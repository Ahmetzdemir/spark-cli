"""Prompt Toolkit için interaktif Slash Komutu ve Dosya Yolu Tamamlayıcı (Completer)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from spark.commands.registry import CommandRegistry


class SparkCompleter(Completer):
    """Slash komutları ve dosya yolları için akıllı popup tamamlayıcı."""

    def __init__(self, command_registry: CommandRegistry, project_dir: str) -> None:
        self.command_registry = command_registry
        self.project_dir = project_dir

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor(WORD=True)

        # 1. Slash komutları tamamlama
        if text_before_cursor.startswith("/") and " " not in text_before_cursor:
            query = text_before_cursor[1:].lower()
            seen_names = set()

            for cmd in self.command_registry._commands.values():
                if cmd.name not in seen_names and cmd.name.startswith(query):
                    seen_names.add(cmd.name)
                    yield Completion(
                        f"/{cmd.name}",
                        start_position=-len(text_before_cursor),
                        display=f"/{cmd.name:<10}",
                        display_meta=cmd.description,
                    )

            # Alias'ları da ekle
            for alias, target in self.command_registry._aliases.items():
                if alias not in seen_names and alias.startswith(query):
                    seen_names.add(alias)
                    cmd = self.command_registry._commands.get(target)
                    desc = f"({target}) {cmd.description}" if cmd else ""
                    yield Completion(
                        f"/{alias}",
                        start_position=-len(text_before_cursor),
                        display=f"/{alias:<10}",
                        display_meta=desc,
                    )
            return

        # 2. Dosya yolu tamamlama (/add, /drop veya genel dosya referansı sonrası)
        if any(text_before_cursor.startswith(prefix) for prefix in ["/add ", "/drop ", "@"]):
            prefix_len = 5 if text_before_cursor.startswith(("/add ", "/drop ")) else 1
            path_query = text_before_cursor[prefix_len:].strip()

            base_dir = self.project_dir
            search_prefix = path_query

            if "/" in path_query or "\\" in path_query:
                parts = path_query.replace("\\", "/").rsplit("/", 1)
                sub_dir = os.path.join(self.project_dir, parts[0])
                if os.path.isdir(sub_dir):
                    base_dir = sub_dir
                    search_prefix = parts[1]

            if os.path.isdir(base_dir):
                try:
                    for entry in sorted(os.listdir(base_dir)):
                        if entry.startswith(".") and not search_prefix.startswith("."):
                            continue
                        if entry.lower().startswith(search_prefix.lower()):
                            full_path = os.path.join(base_dir, entry)
                            is_dir = os.path.isdir(full_path)
                            display_text = f"{entry}/" if is_dir else entry
                            meta = "📁 Dizin" if is_dir else "📄 Dosya"

                            yield Completion(
                                display_text,
                                start_position=-len(search_prefix),
                                display=display_text,
                                display_meta=meta,
                            )
                except PermissionError:
                    pass
