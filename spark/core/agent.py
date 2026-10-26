"""Agent döngüsü — Spark'ın beyni.

4B modeller için optimize edilmiş tool çağrı döngüsü:
- Döngü koruması (aynı tool'u tekrar tekrar çağırma)
- Fallback mekanizması (hatalı JSON parse)
- Token bütçe kontrolü
- İzin yönetimi entegrasyonu
"""

from __future__ import annotations

import json
from typing import Any

from spark.config import SparkConfig
from spark.core.context import ContextManager
from spark.core.history import ChatHistory
from spark.core.permissions import PermissionManager
from spark.core.prompts import get_system_prompt, get_project_context
from spark.llm.client import LMStudioClient
from spark.llm.streaming import StreamAccumulator
from spark.tools.registry import ToolRegistry
from spark.tools.file_read import READ_FILE_TOOL
from spark.tools.file_write import WRITE_FILE_TOOL, set_backup_callback as set_write_backup
from spark.tools.file_edit import EDIT_FILE_TOOL, set_backup_callback as set_edit_backup
from spark.tools.search import SEARCH_CODE_TOOL
from spark.tools.shell import RUN_COMMAND_TOOL
from spark.tools.git import GIT_STATUS_TOOL, GIT_DIFF_TOOL, GIT_COMMIT_TOOL
from spark.tools.tree import LIST_DIR_TOOL
from spark.tools.web import WEB_SEARCH_TOOL
from spark.ui.console import (
    console, print_tool_call, print_tool_result,
    print_permission_request, print_error, print_warning,
)
from spark.ui.spinner import tool_spinner
from spark.ui.markdown import render_markdown


class Agent:
    """Ana agent döngüsü — kullanıcı mesajını alır, tool'ları çalıştırır, yanıt üretir."""

    def __init__(
        self,
        config: SparkConfig,
        llm_client: LMStudioClient,
        project_dir: str,
    ) -> None:
        self.config = config
        self.llm = llm_client
        self.project_dir = project_dir

        # Alt sistemler
        self.history = ChatHistory()
        self.context = ContextManager(
            max_context=llm_client.profile.context_window
        )
        self.permissions = PermissionManager(config.permissions)
        self.tools = ToolRegistry()

        # Tool'ları kaydet
        self._register_tools()

        # Dosya backup callback'lerini ayarla
        set_write_backup(self.history.record_file_backup)
        set_edit_backup(self.history.record_file_backup)

        # Bağlamdaki dosyalar
        self.files_in_context: list[str] = []

        # Döngü koruması
        self._recent_calls: list[tuple[str, str]] = []

        # Sistem prompt'unu ekle
        system_content = get_system_prompt()
        project_ctx = get_project_context(project_dir, self.files_in_context)
        self.history.add_system_message(f"{system_content}\n\n{project_ctx}")

    def _register_tools(self) -> None:
        """Tüm tool'ları registry'ye kaydet."""
        for tool in [
            READ_FILE_TOOL,
            WRITE_FILE_TOOL,
            EDIT_FILE_TOOL,
            SEARCH_CODE_TOOL,
            RUN_COMMAND_TOOL,
            GIT_STATUS_TOOL,
            GIT_DIFF_TOOL,
            GIT_COMMIT_TOOL,
            LIST_DIR_TOOL,
            WEB_SEARCH_TOOL,
        ]:
            self.tools.register(tool)

    def process_message(self, user_message: str) -> str:
        """Kullanıcı mesajını işle ve yanıt üret.

        Returns: Asistan'ın son metin yanıtı
        """
        # Kullanıcı mesajını geçmişe ekle
        self.history.add_user_message(user_message)

        # Token bütçesi kontrol — gerekirse eski mesajları kırp
        self.history.messages = self.context.trim_messages(
            self.history.messages
        )

        # Agent döngüsü
        final_response = ""
        iteration = 0
        max_iterations = self.config.agent.max_iterations

        while iteration < max_iterations:
            iteration += 1

            # LLM'e gönder
            messages = self.history.get_messages_for_api()
            tool_schemas = self.tools.get_all_schemas()

            accumulator = self._call_llm(messages, tool_schemas)

            if accumulator is None:
                final_response = "❌ LLM yanıt vermedi."
                break

            # Tool çağrısı mı?
            if accumulator.is_tool_call and accumulator.tool_calls:
                # Metin yanıtı varsa göster
                if accumulator.content:
                    render_markdown(accumulator.content)

                # Tool call'ları işle
                tool_results = self._execute_tool_calls(accumulator)

                if tool_results is None:
                    # Kullanıcı izin vermedi
                    final_response = "İşlem iptal edildi."
                    self.history.add_assistant_message(content="İşlem iptal edildi.")
                    break

                # Asistan mesajını geçmişe ekle (tool_calls ile)
                assistant_tool_calls = []
                for tc in accumulator.tool_calls:
                    assistant_tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    })

                self.history.add_assistant_message(
                    content=accumulator.content or "",
                    tool_calls=assistant_tool_calls,
                )

                # Tool sonuçlarını geçmişe ekle
                for tc, result in zip(accumulator.tool_calls, tool_results):
                    truncated_result = self.context.truncate_content(
                        result, self.config.agent.max_tool_result_chars
                    )
                    self.history.add_tool_result(tc.id, truncated_result)

                # Döngü koruması kontrolü
                if self._detect_loop(accumulator.tool_calls):
                    print_warning("Döngü algılandı, durduruluyor.")
                    final_response = accumulator.content or "İşlem tamamlandı."
                    break

                # Döngüyü devam ettir (LLM'den yeni yanıt al)
                continue

            else:
                # Düz metin yanıtı
                final_response = accumulator.content
                self.history.add_assistant_message(content=final_response)

                # Token kullanımını güncelle
                if accumulator.usage:
                    self.history.update_token_usage(
                        accumulator.usage.get("total_tokens", 0)
                    )
                break

        if iteration >= max_iterations:
            print_warning(f"Maksimum iterasyon ({max_iterations}) aşıldı.")
            if not final_response:
                final_response = "Maksimum işlem sayısına ulaşıldı."

        return final_response

    def _call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> StreamAccumulator | None:
        """LLM'e streaming istek gönder ve yanıtı biriktir."""
        accumulator = StreamAccumulator()
        text_started = False
        in_think_block = False
        buffer = ""

        try:
            for acc, new_text in self.llm.chat_completion_stream(messages, tools):
                # Yeni metin geldiğinde filtrele ve terminale yazdır
                if new_text and not acc.has_tool_calls:
                    buffer += new_text

                    # <think>...</think> bloklarını filtrele
                    while "<think>" in buffer:
                        in_think_block = True
                        parts = buffer.split("<think>", 1)
                        if parts[0] and not text_started:
                            from spark.ui.console import print_assistant_start
                            print_assistant_start()
                            text_started = True
                        if parts[0]:
                            console.print(parts[0], end="", highlight=False)
                        buffer = parts[1]

                    if in_think_block:
                        if "</think>" in buffer:
                            parts = buffer.split("</think>", 1)
                            buffer = parts[1]
                            in_think_block = False
                        else:
                            # Hala think bloğundayız, biriktirmeye devam et
                            continue

                    if buffer and not in_think_block:
                        if not text_started:
                            from spark.ui.console import print_assistant_start
                            print_assistant_start()
                            text_started = True

                        console.print(buffer, end="", highlight=False)
                        buffer = ""

                accumulator = acc

            # Streaming bitti
            accumulator.finalize()

            # Kalan buffer varsa bas
            if buffer and not in_think_block:
                if not text_started:
                    from spark.ui.console import print_assistant_start
                    print_assistant_start()
                    text_started = True
                console.print(buffer, end="", highlight=False)

            # Temiz içeriği kaydet (think tagleri olmadan)
            clean_content = accumulator.content
            if "<think>" in clean_content and "</think>" in clean_content:
                import re
                clean_content = re.sub(r'<think>.*?</think>', '', clean_content, flags=re.DOTALL).strip()
                accumulator.content = clean_content

            if text_started:
                console.print()  # Satır sonu
                console.print()

            return accumulator

        except Exception as e:
            print_error(f"LLM iletişim hatası: {e}")
            return None

    def _execute_tool_calls(
        self,
        accumulator: StreamAccumulator,
    ) -> list[str] | None:
        """Tool çağrılarını çalıştır. İzin reddedilirse None döndürür."""
        results: list[str] = []

        for tc in accumulator.tool_calls:
            tool_name = tc.name
            args = tc.parse_arguments()

            # Parse hatası kontrolü
            if args.get("_parse_error"):
                print_error(f"Tool argümanları parse edilemedi: {tool_name}")
                results.append(f"Error: Could not parse arguments for {tool_name}. "
                              "Please try simpler arguments.")
                continue

            # İzin kontrolü
            allowed, detail = self.permissions.check_permission(tool_name, args)

            if not allowed:
                if detail.startswith("🚫"):
                    # Engellenmiş komut
                    print_error(detail)
                    results.append(detail)
                    continue

                # Kullanıcıdan onay iste
                args_summary = self._summarize_args(args)
                print_tool_call(tool_name, args_summary)
                response = print_permission_request(
                    f"{tool_name} çalıştırmak istiyor",
                    detail,
                )

                if response in ("e", "evet", "y", "yes"):
                    pass  # Devam et
                elif response in ("her zaman", "always", "h.z", "a"):
                    self.permissions.approve_session(tool_name)
                    if tool_name == "run_command":
                        self.permissions.approve_command(args.get("command", ""))
                else:
                    return None  # İptal
            else:
                # Otomatik onaylanan tool → göster
                args_summary = self._summarize_args(args)
                if self.config.ui.show_tool_calls:
                    print_tool_call(tool_name, args_summary)

            # Tool'u çalıştır
            with tool_spinner(tool_name):
                result = self.tools.execute(tool_name, args)

            # Sonucu göster
            if self.config.ui.show_tool_calls:
                print_tool_result(result)

            results.append(result)

        return results

    def _detect_loop(self, tool_calls) -> bool:
        """Aynı tool çağrısının tekrarlanıp tekrarlanmadığını kontrol et."""
        threshold = self.config.agent.loop_detection_threshold

        for tc in tool_calls:
            call_sig = (tc.name, tc.arguments)
            self._recent_calls.append(call_sig)

        # Son N çağrıda aynı imza varsa döngü
        if len(self._recent_calls) >= threshold:
            recent = self._recent_calls[-threshold:]
            if len(set(recent)) == 1:
                return True

        # Çok fazla çağrı birikmesin
        if len(self._recent_calls) > 50:
            self._recent_calls = self._recent_calls[-20:]

        return False

    def _summarize_args(self, args: dict[str, Any]) -> str:
        """Tool argümanlarını kısa özetle."""
        parts: list[str] = []
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            parts.append(f'{key}="{value}"')

        return ", ".join(parts[:3])

    def add_file_to_context(self, filepath: str) -> str:
        """Dosyayı bağlama ekle."""
        from pathlib import Path

        path = Path(filepath).resolve()
        if not path.exists():
            return f"Dosya bulunamadı: {filepath}"

        rel_path = str(path)
        if rel_path not in self.files_in_context:
            self.files_in_context.append(rel_path)

            # Dosya içeriğini oku ve context'e ekle
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                truncated = self.context.truncate_content(content, 3000)
                self.history.add_system_message(
                    f"[File added to context: {path.name}]\n{truncated}"
                )
            except Exception as e:
                return f"Dosya okunamadı: {e}"

        return f"Eklendi: {path.name} ({len(self.files_in_context)} dosya bağlamda)"

    def drop_file_from_context(self, filepath: str) -> str:
        """Dosyayı bağlamdan çıkar."""
        from pathlib import Path

        path = str(Path(filepath).resolve())
        if path in self.files_in_context:
            self.files_in_context.remove(path)
            return f"Çıkarıldı: {Path(path).name}"
        return f"Dosya bağlamda değil: {filepath}"

    def compact_history(self) -> str:
        """Sohbet geçmişini sıkıştır."""
        from spark.core.prompts import SUMMARY_PROMPT

        # Mevcut geçmişi özetle
        summary_messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": self._format_history_for_summary()},
        ]

        result = self.llm.chat_completion(summary_messages, temperature=0.3)
        summary = result.get("content", "Özet oluşturulamadı.")

        old_count = self.history.message_count
        self.history.compact(summary)

        # Sistem prompt'unu yeniden ekle
        system_content = get_system_prompt(compact=True)
        project_ctx = get_project_context(self.project_dir, self.files_in_context)
        self.history.messages.insert(0, {
            "role": "system",
            "content": f"{system_content}\n\n{project_ctx}",
        })

        return f"Geçmiş sıkıştırıldı: {old_count} mesaj → {self.history.message_count} mesaj"

    def _format_history_for_summary(self) -> str:
        """Geçmişi özet için formatla."""
        parts: list[str] = []
        for msg in self.history.messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if content and role != "system":
                parts.append(f"[{role}] {content[:500]}")
        return "\n".join(parts[-20:])  # Son 20 mesaj

    def undo_last_change(self) -> str:
        """Son dosya değişikliğini geri al."""
        backup = self.history.pop_last_backup()
        if not backup:
            return "Geri alınacak değişiklik yok."

        filepath = backup["path"]
        old_content = backup["content"]

        try:
            from pathlib import Path
            path = Path(filepath)

            if old_content is None:
                # Dosya yeni oluşturulmuştu → sil
                if path.exists():
                    path.unlink()
                return f"Geri alındı: {path.name} silindi (yeni oluşturulmuştu)"
            else:
                # Eski içeriği geri yaz
                path.write_text(old_content, encoding="utf-8")
                return f"Geri alındı: {path.name} eski haline döndürüldü"

        except Exception as e:
            return f"Geri alma hatası: {e}"

    @property
    def tokens_used(self) -> int:
        """Yaklaşık token kullanımını döndür."""
        return self.context.count_messages_tokens(self.history.messages)

    @property
    def context_max(self) -> int:
        """Context window boyutunu döndür."""
        return self.llm.profile.context_window
