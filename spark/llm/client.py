"""LM Studio OpenAI-uyumlu client."""

from __future__ import annotations

from typing import Any, Generator

from openai import OpenAI, APIConnectionError, APITimeoutError

from spark.config import LLMConfig
from spark.llm.models import ModelProfile, get_model_profile
from spark.llm.streaming import StreamAccumulator


class LMStudioClient:
    """LM Studio ile OpenAI-uyumlu API üzerinden iletişim."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
        )
        self._active_model: str | None = None
        self._profile: ModelProfile | None = None

    @property
    def model_name(self) -> str:
        """Aktif model adını döndür."""
        if self._active_model:
            return self._active_model
        if self.config.model != "auto":
            return self.config.model
        return self._detect_model()

    @property
    def profile(self) -> ModelProfile:
        """Aktif modelin profilini döndür."""
        if self._profile is None:
            self._profile = get_model_profile(self.model_name)
        return self._profile

    def _detect_model(self) -> str:
        """LM Studio'dan yüklü modeli otomatik algıla (kodlama modellerine öncelik ver)."""
        try:
            models = self.client.models.list()
            if models.data:
                # Embedding modellerini filtrele
                chat_models = [
                    m.id for m in models.data
                    if "embed" not in m.id.lower()
                ]

                # Tercih sırası: qwen > gemma > phi > deepseek > coder > diğerleri
                priority_keywords = ["qwen", "gemma", "phi", "deepseek", "coder"]
                chosen_model = None

                for kw in priority_keywords:
                    for m_id in chat_models:
                        if kw in m_id.lower():
                            chosen_model = m_id
                            break
                    if chosen_model:
                        break

                if not chosen_model and chat_models:
                    chosen_model = chat_models[0]
                elif not chosen_model and models.data:
                    chosen_model = models.data[0].id

                if chosen_model:
                    self._active_model = chosen_model
                    self._profile = get_model_profile(chosen_model)
                    return chosen_model
        except Exception:
            pass
        return "unknown"

    def set_model(self, model_name: str) -> None:
        """Aktif modeli değiştir."""
        self._active_model = model_name
        self._profile = get_model_profile(model_name)

    def list_available_models(self) -> list[str]:
        """LM Studio'daki mevcut modelleri listele."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

    def chat_completion_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[tuple[StreamAccumulator, str | None], None, StreamAccumulator]:
        """Streaming chat completion isteği gönder.

        Yields: (StreamAccumulator, new_text_chunk)
        Returns: Tamamlanmış StreamAccumulator
        """
        profile = self.profile
        params: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature or profile.temperature,
            "max_tokens": max_tokens or profile.recommended_max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if tools and profile.supports_tool_calling:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        accumulator = StreamAccumulator()

        try:
            stream = self.client.chat.completions.create(**params)
            for chunk in stream:
                new_text = accumulator.process_chunk(chunk)
                if new_text is not None or accumulator.has_tool_calls:
                    yield accumulator, new_text

            accumulator.finalize()

        except APIConnectionError:
            accumulator.content = (
                "❌ LM Studio'ya bağlanılamadı. "
                f"Sunucunun {self.config.base_url} adresinde çalıştığından emin olun.\n"
                "LM Studio → Developer sekmesinden sunucuyu başlatın."
            )
            yield accumulator, accumulator.content
        except APITimeoutError:
            accumulator.content = (
                "⏱️ İstek zaman aşımına uğradı. "
                "Model yanıt vermiyor olabilir. Daha kısa bir istek deneyin."
            )
            yield accumulator, accumulator.content
        except Exception as e:
            accumulator.content = f"❌ LLM hatası: {type(e).__name__}: {e}"
            yield accumulator, accumulator.content

        return accumulator

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Non-streaming chat completion (özet/compact için kullanılır)."""
        profile = self.profile
        params: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature or profile.temperature,
            "max_tokens": max_tokens or profile.recommended_max_tokens,
        }

        if tools and profile.supports_tool_calling:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**params)
            choice = response.choices[0]

            result: dict[str, Any] = {
                "content": choice.message.content or "",
                "tool_calls": [],
                "finish_reason": choice.finish_reason,
                "usage": {},
            }

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    result["tool_calls"].append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    })

            if response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return result

        except APIConnectionError:
            return {
                "content": f"❌ LM Studio'ya bağlanılamadı ({self.config.base_url}).",
                "tool_calls": [],
                "finish_reason": "error",
                "usage": {},
            }
        except Exception as e:
            return {
                "content": f"❌ LLM hatası: {e}",
                "tool_calls": [],
                "finish_reason": "error",
                "usage": {},
            }

    def test_connection(self) -> tuple[bool, str]:
        """Bağlantıyı test et. (başarılı_mı, mesaj) döndürür."""
        try:
            models = self.client.models.list()
            if models.data:
                model_names = [m.id for m in models.data]
                return True, f"Bağlantı başarılı. Modeller: {', '.join(model_names)}"
            return True, "Bağlantı başarılı ama yüklü model yok."
        except APIConnectionError:
            return False, (
                f"LM Studio'ya bağlanılamadı ({self.config.base_url}). "
                "Sunucu çalışıyor mu?"
            )
        except Exception as e:
            return False, f"Bağlantı hatası: {e}"
