"""Context ve token bütçe yönetimi.

4B modellerin sınırlı context window'u için agresif bütçe yönetimi.
"""

from __future__ import annotations

from typing import Any

import tiktoken


class ContextManager:
    """Token bütçesini ve context window'u yöneten sınıf."""

    def __init__(self, max_context: int = 8192) -> None:
        self.max_context = max_context
        self._encoder: tiktoken.Encoding | None = None

        # Token bütçesi ayrımı
        self.budget = ContextBudget(
            system_prompt=800,
            tool_definitions=1200,
            project_context=1000,
            response_reserve=2000,
            max_total=max_context,
        )

    @property
    def encoder(self) -> tiktoken.Encoding:
        """Token encoder'ı lazy yükle."""
        if self._encoder is None:
            try:
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # Fallback: basit kelime sayısı tahmini
                self._encoder = _FallbackEncoder()  # type: ignore
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """Metindeki token sayısını hesapla."""
        if not text:
            return 0
        try:
            return len(self.encoder.encode(text))
        except Exception:
            # Fallback: ortalama 4 karakter/token
            return len(text) // 4

    def count_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Mesaj listesindeki toplam token sayısını hesapla."""
        total = 0
        for msg in messages:
            # Her mesaj ~4 token overhead
            total += 4
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count_tokens(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        total += self.count_tokens(str(part.get("text", "")))

            # Tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    total += self.count_tokens(tc.get("function", {}).get("name", ""))
                    total += self.count_tokens(tc.get("function", {}).get("arguments", ""))

        return total

    @property
    def available_for_history(self) -> int:
        """Sohbet geçmişi için kullanılabilir token sayısı."""
        return (
            self.max_context
            - self.budget.system_prompt
            - self.budget.tool_definitions
            - self.budget.project_context
            - self.budget.response_reserve
        )

    def trim_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Mesajları token bütçesine sığacak şekilde kırp.

        İlk mesajı (sistem prompt) ve son mesajı (kullanıcı) korur.
        Ortadaki eski mesajları siler.
        """
        budget = self.available_for_history
        if budget <= 0:
            # Sadece son mesajı döndür
            return messages[-1:] if messages else []

        total = self.count_messages_tokens(messages)
        if total <= budget:
            return messages

        # Son mesajı (en güncel) koru
        trimmed = list(messages)
        while len(trimmed) > 2 and self.count_messages_tokens(trimmed) > budget:
            # En eski mesajı sil (indeks 1, 0 sistem prompt olabilir)
            trimmed.pop(1)

        return trimmed

    def truncate_content(self, content: str, max_tokens: int | None = None) -> str:
        """İçeriği belirli token sayısına kırp."""
        limit = max_tokens or 2000
        tokens = self.count_tokens(content)

        if tokens <= limit:
            return content

        # Karakter bazında kırp (yaklaşık)
        char_limit = limit * 4
        if len(content) > char_limit:
            return content[:char_limit] + f"\n\n... [{tokens - limit} token kırpıldı]"

        return content

    def update_max_context(self, max_context: int) -> None:
        """Maksimum context boyutunu güncelle."""
        self.max_context = max_context
        self.budget.max_total = max_context


class ContextBudget:
    """Token bütçesi dağılımı."""

    def __init__(
        self,
        system_prompt: int = 800,
        tool_definitions: int = 1200,
        project_context: int = 1000,
        response_reserve: int = 2000,
        max_total: int = 8192,
    ) -> None:
        self.system_prompt = system_prompt
        self.tool_definitions = tool_definitions
        self.project_context = project_context
        self.response_reserve = response_reserve
        self.max_total = max_total

    @property
    def allocated(self) -> int:
        return (
            self.system_prompt
            + self.tool_definitions
            + self.project_context
            + self.response_reserve
        )

    @property
    def available(self) -> int:
        return max(0, self.max_total - self.allocated)


class _FallbackEncoder:
    """tiktoken yüklenemezse kullanılan basit encoder."""

    def encode(self, text: str) -> list[int]:
        """Basit tahmin: ortalama 4 karakter/token."""
        return list(range(len(text) // 4))
