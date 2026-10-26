"""Slash komut registry'si — Claude Code Birebir Komut Seti."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from spark.core.agent import Agent


@dataclass
class SlashCommand:
    """Bir slash komutu tanımı."""
    name: str
    description: str
    usage: str
    handler: Callable[["Agent", list[str]], str]
    aliases: list[str] | None = None


class CommandRegistry:
    """Slash komut kayıt ve çalıştırma sistemi."""

    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: SlashCommand) -> None:
        """Komut kaydet."""
        self._commands[command.name] = command
        if command.aliases:
            for alias in command.aliases:
                self._aliases[alias] = command.name

    def parse_and_execute(self, input_text: str, agent: "Agent") -> tuple[bool, str]:
        """Slash komutunu parse et ve çalıştır.

        Returns:
            (is_command, result_message)
        """
        if not input_text.startswith("/"):
            return False, ""

        parts = input_text[1:].strip().split(maxsplit=1)
        if not parts:
            return False, ""

        cmd_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        # Alias kontrolü
        if cmd_name in self._aliases:
            cmd_name = self._aliases[cmd_name]

        # Komut bul
        command = self._commands.get(cmd_name)
        if command is None:
            return True, f"Bilinmeyen komut: /{cmd_name}. Komut listesi için /help yazın."

        # Özel help durumu
        if cmd_name == "help":
            return True, self.get_help_text()

        # Çalıştır
        try:
            result = command.handler(agent, args)
            return True, result
        except Exception as e:
            return True, f"Komut hatası: {e}"

    def get_help_text(self) -> str:
        """Claude Code stili komut yardım tablosu."""
        lines = [
            "⚡ Claude Code Komut Listesi\n",
            "  Komut         Açıklama",
            "  ────────────  ──────────────────────────────────────────",
        ]
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            aliases_text = f" (kısayol: {', '.join('/' + a for a in cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"  /{cmd.name:<12} {cmd.description}{aliases_text}")

        lines.append("\n  İpucu: Dosyalara doğrudan başvurmak için /add veya @dosya kullanabilirsiniz.")
        return "\n".join(lines)

    def get_command_names(self) -> list[str]:
        """Tüm komut adlarını döndür."""
        names = ["/" + name for name in self._commands.keys()]
        names.extend("/" + alias for alias in self._aliases.keys())
        return sorted(names)


def build_command_registry() -> CommandRegistry:
    """Tüm Claude Code komutlarını kaydeden registry oluştur."""
    registry = CommandRegistry()

    # ===== Claude Code Temel Komutları =====
    registry.register(SlashCommand(
        name="cost",
        description="Oturum token kullanımını ve maliyeti göster",
        usage="/cost",
        handler=_cmd_cost,
    ))

    registry.register(SlashCommand(
        name="init",
        description="Projeye CLAUDE.md kılavuz dosyasını oluştur",
        usage="/init",
        handler=_cmd_init,
    ))

    registry.register(SlashCommand(
        name="doctor",
        description="Sistem, LLM bağlantısı ve araç sağlığını denetle",
        usage="/doctor",
        handler=_cmd_doctor,
    ))

    registry.register(SlashCommand(
        name="review",
        description="Mevcut git değişikliklerini AI ile incele",
        usage="/review",
        handler=_cmd_review,
    ))

    registry.register(SlashCommand(
        name="clear",
        description="Sohbet geçmişini ve bağlamı sıfırla",
        usage="/clear",
        handler=_cmd_clear,
        aliases=["reset"],
    ))

    registry.register(SlashCommand(
        name="compact",
        description="Geçmişi özetleyerek bağlamı sıkıştır",
        usage="/compact",
        handler=_cmd_compact,
    ))

    # ===== Dosya & Kod Komutları =====
    registry.register(SlashCommand(
        name="add",
        description="Dosyayı bağlama ekle",
        usage="/add <dosya_yolu>",
        handler=_cmd_add,
    ))

    registry.register(SlashCommand(
        name="drop",
        description="Dosyayı bağlamdan çıkar",
        usage="/drop <dosya_yolu>",
        handler=_cmd_drop,
    ))

    registry.register(SlashCommand(
        name="files",
        description="Bağlamdaki aktif dosyaları listele",
        usage="/files",
        handler=_cmd_files,
    ))

    registry.register(SlashCommand(
        name="undo",
        description="Son dosya değişikliğini geri al",
        usage="/undo",
        handler=_cmd_undo,
    ))

    # ===== Git Komutları =====
    registry.register(SlashCommand(
        name="commit",
        description="AI tarafından üretilen mesajla git commit yap",
        usage="/commit [mesaj]",
        handler=_cmd_commit,
    ))

    registry.register(SlashCommand(
        name="diff",
        description="Mevcut git diff çıktısını göster",
        usage="/diff",
        handler=_cmd_diff,
    ))

    # ===== Durum & Model Komutları =====
    registry.register(SlashCommand(
        name="status",
        description="Oturum durumunu ve context doluluğunu göster",
        usage="/status",
        handler=_cmd_status,
    ))

    registry.register(SlashCommand(
        name="model",
        description="Aktif modeli göster veya değiştir",
        usage="/model [model_adı]",
        handler=_cmd_model,
        aliases=["models"],
    ))

    registry.register(SlashCommand(
        name="config",
        description="Mevcut ayarları listele",
        usage="/config",
        handler=_cmd_config,
    ))

    # ===== Yardım & Çıkış =====
    registry.register(SlashCommand(
        name="help",
        description="Komut yardım listesini göster",
        usage="/help",
        handler=_cmd_help,
        aliases=["?", "h"],
    ))

    registry.register(SlashCommand(
        name="exit",
        description="Claude Code / Spark oturumundan çık",
        usage="/exit",
        handler=_cmd_exit,
        aliases=["quit", "q"],
    ))

    return registry


# ===== Komut Handler'ları =====

def _cmd_cost(agent: "Agent", args: list[str]) -> str:
    """Claude Code /cost komutu."""
    tokens = agent.tokens_used
    ctx_max = agent.context_max
    percentage = (tokens / ctx_max * 100) if ctx_max > 0 else 0

    return f"""╭─── 📊 Claude Code Token & Maliyet Özeti ──────────────────────╮
│  Kullanılan Token:    {tokens:,} / {ctx_max:,} (%{percentage:.1f})
│  Tahmini Maliyet:     $0.0000 (Yerel LM Studio Modeli)
│  Mesaj Sayısı:        {agent.history.message_count}
│  Aktif Model:         {agent.llm.model_name}
╰────────────────────────────────────────────────────────────────╯"""


def _cmd_init(agent: "Agent", args: list[str]) -> str:
    """Claude Code /init komutu — CLAUDE.md dosyası oluşturur."""
    claude_md_path = os.path.join(agent.project_dir, "CLAUDE.md")
    if os.path.exists(claude_md_path):
        return f"CLAUDE.md zaten mevcut: {claude_md_path}"

    project_name = Path(agent.project_dir).name
    template = f"""# {project_name} — Project Guide

## Build & Test Commands
- Run tests: `pytest` or `npm test`
- Build: `python setup.py build` or `npm run build`
- Lint: `flake8` or `eslint`

## Code Style & Architecture Guidelines
- Language: Python / JavaScript
- Follow clean architecture and modular functions.
- Always include automated tests for new features.
"""
    try:
        with open(claude_md_path, "w", encoding="utf-8") as f:
            f.write(template)
        agent.add_file_to_context("CLAUDE.md")
        return f"✓ CLAUDE.md oluşturuldu ve bağlama eklendi: {claude_md_path}"
    except Exception as e:
        return f"CLAUDE.md oluşturulamadı: {e}"


def _cmd_doctor(agent: "Agent", args: list[str]) -> str:
    """Claude Code /doctor komutu — Sistem ve bağlantı sağlığını denetler."""
    is_connected, msg = agent.llm.test_connection()
    conn_status = "✓ Bağlı (localhost:1234)" if is_connected else "✗ Bağlantı Yok"

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    git_status = "✓ Aktif" if os.path.exists(os.path.join(agent.project_dir, ".git")) else "○ Git yok"
    claude_md = "✓ Mevcut" if os.path.exists(os.path.join(agent.project_dir, "CLAUDE.md")) else "○ Yok (/init ile oluşturun)"

    return f"""╭─── 🩺 Claude Code Doctor — Sistem Sağlığı ───────────────────╮
│  LM Studio Sunucu:    {conn_status}
│  Aktif Model:         {agent.llm.model_name}
│  Context Limiti:      {agent.context_max:,} tokens
│  Python Sürümü:       {py_ver}
│  Git Entegrasyonu:    {git_status}
│  CLAUDE.md Bellek:    {claude_md}
│  Otonom İzinler:      ✓ Tüm araçlar otomatik onaylı
╰────────────────────────────────────────────────────────────────╯"""


def _cmd_review(agent: "Agent", args: list[str]) -> str:
    """Claude Code /review komutu — Değişiklikleri AI ile denetler."""
    from spark.tools.git import git_diff
    diff = git_diff(agent.project_dir)
    if "No changes" in diff or not diff.strip():
        return "İncelenecek git değişikliği bulunamadı (çalışma ağacı temiz)."

    prompt = f"Aşağıdaki git diff değişikliklerini incele, kod kalitesi, güvenlik ve olası hatalar açısından kısa ve net bir code review yap:\n\n{diff[:3000]}"
    return agent.process_message(prompt)


def _cmd_add(agent: "Agent", args: list[str]) -> str:
    if not args:
        return "Kullanım: /add <dosya_yolu>"
    return agent.add_file_to_context(args[0])


def _cmd_drop(agent: "Agent", args: list[str]) -> str:
    if not args:
        return "Kullanım: /drop <dosya_yolu>"
    return agent.drop_file_from_context(args[0])


def _cmd_files(agent: "Agent", args: list[str]) -> str:
    if not agent.files_in_context:
        return "Bağlamda dosya yok. /add ile ekleyebilirsiniz."

    lines = ["Bağlamdaki dosyalar:"]
    for f in agent.files_in_context:
        lines.append(f"  📄 {Path(f).name} ({f})")
    return "\n".join(lines)


def _cmd_commit(agent: "Agent", args: list[str]) -> str:
    if args:
        message = " ".join(args)
    else:
        from spark.tools.git import git_diff
        diff = git_diff(agent.project_dir)
        if "No changes" in diff:
            return "Commit edilecek değişiklik yok."

        result = agent.llm.chat_completion([
            {"role": "system", "content": "Write a brief git commit message for these changes. One line, max 72 chars."},
            {"role": "user", "content": f"Changes:\n{diff[:2000]}"},
        ], temperature=0.3)
        message = result.get("content", "update").strip().strip('"')

    from spark.tools.git import git_commit
    return git_commit(message, agent.project_dir)


def _cmd_diff(agent: "Agent", args: list[str]) -> str:
    from spark.tools.git import git_diff
    return git_diff(agent.project_dir)


def _cmd_clear(agent: "Agent", args: list[str]) -> str:
    from spark.core.prompts import get_system_prompt, get_project_context
    agent.history.clear()
    system_content = get_system_prompt()
    project_ctx = get_project_context(agent.project_dir, agent.files_in_context)
    agent.history.add_system_message(f"{system_content}\n\n{project_ctx}")
    return "✓ Sohbet geçmişi ve bağlam temizlendi."


def _cmd_compact(agent: "Agent", args: list[str]) -> str:
    return agent.compact_history()


def _cmd_undo(agent: "Agent", args: list[str]) -> str:
    return agent.undo_last_change()


def _cmd_status(agent: "Agent", args: list[str]) -> str:
    from spark.ui.console import print_session_status
    print_session_status(
        model=agent.llm.model_name,
        tokens_used=agent.tokens_used,
        context_max=agent.context_max,
        files_in_context=agent.files_in_context,
        messages_count=agent.history.message_count,
    )
    return ""


def _cmd_model(agent: "Agent", args: list[str]) -> str:
    if not args:
        current = agent.llm.model_name
        available = agent.llm.list_available_models()
        lines = [f"Aktif model: {current}"]
        if available:
            lines.append("\nLM Studio'daki modeller:")
            for m in available:
                marker = " ←" if m == current else ""
                lines.append(f"  • {m}{marker}")
        lines.append("\nDeğiştirmek için: /model <model_adı>")
        return "\n".join(lines)

    new_model = args[0]
    agent.llm.set_model(new_model)
    agent.context.update_max_context(agent.llm.profile.context_window)
    return f"Model değiştirildi: {new_model} (context: {agent.llm.profile.context_window:,} token)"


def _cmd_help(agent: "Agent", args: list[str]) -> str:
    return ""


def _cmd_exit(agent: "Agent", args: list[str]) -> str:
    raise SystemExit(0)


def _cmd_config(agent: "Agent", args: list[str]) -> str:
    config = agent.config
    return f"""⚡ Claude Code / Spark Yapılandırması

LLM:
  URL:          {config.llm.base_url}
  Model:        {config.llm.model}
  Temperature:  {config.llm.temperature}
  Max Tokens:   {config.llm.max_tokens}

İzinler:
  Yazma onayı:  {"Otomatik" if config.permissions.auto_approve_write else "Manuel"}
  Beyaz liste:  {len(config.permissions.whitelisted_commands)} komut

Agent:
  Max iterasyon: {config.agent.max_iterations}
  Döngü eşiği:   {config.agent.loop_detection_threshold}"""
