"""Spark REPL — Claude Code Stili Zengin ve İnteraktif Arayüz."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings

from spark.config import SparkConfig, CONFIG_DIR_NAME
from spark.core.agent import Agent
from spark.llm.client import LMStudioClient
from spark.commands.registry import build_command_registry, CommandRegistry
from spark.ui.completer import SparkCompleter
from spark.ui.console import (
    console,
    print_banner,
    print_user_prompt,
    print_error,
    print_success,
    print_info,
    print_warning,
)


class SparkApp:
    """Spark CLI ana uygulaması — Claude Code Stili Minimalist ve Güçlü REPL."""

    def __init__(
        self,
        config: SparkConfig,
        project_dir: str | None = None,
        model_override: str | None = None,
    ) -> None:
        self.config = config
        self.project_dir = project_dir or os.getcwd()

        # LLM client
        if model_override:
            config.llm.model = model_override

        self.llm_client = LMStudioClient(config.llm)

        # Agent
        self.agent = Agent(
            config=config,
            llm_client=self.llm_client,
            project_dir=self.project_dir,
        )

        # Komut sistemi
        self.commands: CommandRegistry = build_command_registry()
        self._session: PromptSession | None = None

    def _get_bottom_toolbar(self) -> HTML:
        """Canlı alt durum çubuğu (Bottom Toolbar)."""
        tokens = self.agent.tokens_used
        ctx = self.agent.context_max
        model = self.llm_client.profile.display_name
        cwd = Path(self.project_dir).name

        token_style = "ansigreen" if tokens / max(ctx, 1) < 0.6 else "ansiyellow" if tokens / max(ctx, 1) < 0.85 else "ansired"

        return HTML(
            f" ⚡ <b>Spark</b> │ <b>{model}</b> │ 📁 <b>{cwd}</b> │ "
            f"<{token_style}><b>{tokens:,}/{ctx:,}</b> token</{token_style}> │ "
            f"<i>/help</i> │ <i>Alt+Enter</i>: Çoklu Satır "
        )

    def _get_session(self) -> PromptSession | None:
        """Prompt session'ı zengin tamamlama ve kısayollarla yapılandır."""
        if self._session is not None:
            return self._session

        try:
            history_dir = Path.home() / CONFIG_DIR_NAME
            history_dir.mkdir(exist_ok=True)

            # Çok satırlı giriş için kısayollar
            kb = KeyBindings()

            @kb.add("escape", "enter")
            @kb.add("c-j")  # Ctrl+J veya Alt+Enter yeni satır ekler
            def _insert_newline(event):
                event.current_buffer.insert_text("\n")

            # İnteraktif tamamlayıcı
            completer = SparkCompleter(self.commands, self.project_dir)

            self._session = PromptSession(
                history=FileHistory(str(history_dir / "prompt_history")),
                auto_suggest=AutoSuggestFromHistory(),
                completer=completer,
                complete_while_typing=True,
                bottom_toolbar=self._get_bottom_toolbar,
                key_bindings=kb,
                multiline=False,
                enable_history_search=True,
            )
            return self._session
        except Exception:
            # Fallback: win32 konsol buffer'ı olmayan ortamlar için
            return None

    def run(self, one_shot: str | None = None) -> None:
        """Ana döngüyü başlat."""
        print_banner(self.project_dir, self.llm_client.model_name)
        self._test_connection()

        # Tek seferlik komut
        if one_shot:
            self._process_input(one_shot, is_repl=False)
            return

        # REPL döngüsü
        self._repl_loop()

    def _test_connection(self) -> bool:
        """LM Studio bağlantısını test et."""
        success, message = self.llm_client.test_connection()
        if not success:
            print_error(message)
            print_warning("LM Studio sunucusuna bağlanılamadı.")
            print_info("Lütfen LM Studio'yu açıp Developer sekmesinden sunucuyu başlatın (localhost:1234).")
            console.print()
            return False
        return True

    def _repl_loop(self) -> None:
        """Etkileşimli Claude Code stili REPL döngüsü."""
        session = self._get_session()

        while True:
            try:
                if session:
                    user_input = session.prompt(
                        HTML("<ansiyellow><b>❯ </b></ansiyellow>"),
                    ).strip()
                else:
                    console.print("[bold #D97706]❯ [/]", end="")
                    user_input = input().strip()

                if not user_input:
                    continue

                self._process_input(user_input, is_repl=True)

            except KeyboardInterrupt:
                console.print("\n")
                print_info("Çıkmak için /exit veya Ctrl+D yazın.")
                continue

            except EOFError:
                self._graceful_exit()
                break

            except SystemExit:
                self._graceful_exit()
                break

            except Exception as e:
                print_error(f"Hata: {type(e).__name__}: {e}")

    def _process_input(self, user_input: str, is_repl: bool = False) -> None:
        """Kullanıcı girdisini işle (slash komutu veya normal mesaj)."""

        # Slash komutu kontrolü
        if user_input.startswith("/"):
            is_cmd, result = self.commands.parse_and_execute(
                user_input, self.agent
            )
            if is_cmd:
                if user_input.strip().startswith("/help") or user_input.strip() in ("/?", "/h"):
                    result = self.commands.get_help_text()

                if result:
                    console.print(f"  {result}")
                    console.print()
                return

        # Normal mesaj (tek seferlik modda kullanıcı prompt'unu yazdır)
        if not is_repl:
            print_user_prompt(user_input)

        try:
            self.agent.process_message(user_input)

            # Token kullanım uyarısı
            if self.config.ui.show_token_usage:
                tokens = self.agent.tokens_used
                context_max = self.agent.context_max
                ratio = tokens / max(context_max, 1)

                if ratio > 0.85:
                    print_warning(
                        f"Token kapasitesi dolmak üzere: {tokens:,}/{context_max:,} "
                        f"({ratio:.0%}). /compact ile geçmişi sıkıştırabilirsiniz."
                    )

        except Exception as e:
            print_error(f"Agent hatası: {type(e).__name__}: {e}")

    def _graceful_exit(self) -> None:
        """Düzgün çıkış."""
        console.print()

        modified = self.agent.history.get_modified_files()
        if modified:
            print_info(f"Bu oturumda {len(modified)} dosya değiştirildi:")
            for f in modified:
                console.print(f"    📄 {Path(f).name}")

        print_success("Görüşmek üzere! ⚡")
        console.print()
