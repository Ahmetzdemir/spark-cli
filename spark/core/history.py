"""Sohbet geçmişi yönetimi."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from spark.config import CONFIG_DIR_NAME, HISTORY_DIR_NAME


class ChatHistory:
    """Sohbet geçmişi yönetimi.

    - Mesajları bellekte tutar
    - Dosya değişikliklerini izler (undo için)
    - Geçmişi diske kaydedebilir
    """

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self._file_backups: list[dict[str, Any]] = []  # undo için
        self._total_tokens_used: int = 0

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens_used

    def add_system_message(self, content: str) -> None:
        """Sistem mesajı ekle."""
        self.messages.append({
            "role": "system",
            "content": content,
        })

    def add_user_message(self, content: str) -> None:
        """Kullanıcı mesajı ekle."""
        self.messages.append({
            "role": "user",
            "content": content,
        })

    def add_assistant_message(
        self,
        content: str = "",
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        """Asistan mesajı ekle."""
        msg: dict[str, Any] = {"role": "assistant"}

        if content:
            msg["content"] = content
        else:
            msg["content"] = None

        if tool_calls:
            msg["tool_calls"] = tool_calls

        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """Tool sonucu ekle."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    def record_file_backup(self, path: str, content: str | None) -> None:
        """Dosya değişikliği öncesi yedek kaydet (undo için).

        content=None → dosya yoktu (yeni oluşturuldu).
        """
        self._file_backups.append({
            "path": path,
            "content": content,
            "timestamp": time.time(),
        })

    def get_last_backup(self) -> dict[str, Any] | None:
        """Son dosya yedeğini döndür."""
        if self._file_backups:
            return self._file_backups[-1]
        return None

    def pop_last_backup(self) -> dict[str, Any] | None:
        """Son dosya yedeğini çıkar ve döndür (undo)."""
        if self._file_backups:
            return self._file_backups.pop()
        return None

    def get_all_backups(self) -> list[dict[str, Any]]:
        """Tüm dosya yedeklerini döndür."""
        return list(self._file_backups)

    def clear(self) -> None:
        """Geçmişi temizle (yedekler korunur)."""
        self.messages.clear()
        self._total_tokens_used = 0

    def compact(self, summary: str) -> None:
        """Geçmişi bir özete sıkıştır."""
        self.messages = [
            {
                "role": "system",
                "content": f"[Önceki sohbet özeti]\n{summary}",
            }
        ]

    def update_token_usage(self, tokens: int) -> None:
        """Toplam token kullanımını güncelle."""
        self._total_tokens_used += tokens

    def get_messages_for_api(self) -> list[dict[str, Any]]:
        """API'ye gönderilecek mesajları döndür."""
        return list(self.messages)

    def save_to_disk(self, project_dir: Path) -> None:
        """Geçmişi diske kaydet."""
        history_dir = project_dir / CONFIG_DIR_NAME / HISTORY_DIR_NAME
        history_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        filename = f"session_{timestamp}.jsonl"

        with open(history_dir / filename, "w", encoding="utf-8") as f:
            for msg in self.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    def load_from_disk(self, filepath: Path) -> None:
        """Geçmişi diskten yükle."""
        if not filepath.exists():
            return

        self.messages.clear()
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    def get_modified_files(self) -> list[str]:
        """Bu oturumda değiştirilen dosyaların listesini döndür."""
        return list({b["path"] for b in self._file_backups})
