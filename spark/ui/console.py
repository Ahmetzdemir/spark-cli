"""Rich console — Claude Code Birebir Görsel ve Çıktı Arayüzü."""

from __future__ import annotations

import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

from spark import __version__
from spark.ui.themes import get_spark_theme, ICONS


# Global console instance
console = Console(theme=get_spark_theme(), highlight=False)
error_console = Console(theme=get_spark_theme(), stderr=True, highlight=False)


def print_banner(project_dir: str | None = None, model_name: str | None = None) -> None:
    """Claude Code birebir açılış paneli."""
    cwd_name = Path(project_dir or os.getcwd()).name
    active_model = model_name or "Local Model"

    header = Text()
    header.append("  ⚡ Claude Code", style="bold #D97706")
    header.append(f" (v{__version__})", style="dim")
    header.append(" · Local Edition\n", style="dim")

    info = Text()
    info.append("  Model: ", style="dim")
    info.append(f"{active_model} ", style="bold #F8FAFC")
    info.append("· CWD: ", style="dim")
    info.append(f"{cwd_name}\n", style="bold #F8FAFC")
    info.append("  Komutlar için ", style="dim")
    info.append("/help", style="bold #D97706")
    info.append(" · Token kullanımı için ", style="dim")
    info.append("/cost", style="bold #38BDF8")

    console.print()
    console.print(Panel(
        Text.assemble(header, info),
        border_style="#475569",
        box=box.ROUNDED,
        padding=(1, 1),
    ))
    console.print()


def print_user_prompt(text: str) -> None:
    """Kullanıcı mesajı (Claude Code stili)."""
    console.print(
        Text.assemble(
            ("❯ ", "bold #D97706"),
            (text, "bold #F8FAFC"),
        )
    )
    console.print()


def print_assistant_start() -> None:
    """Claude Code yanıt başlangıcı."""
    console.print(
        Text.assemble(
            ("⚡ ", "bold #D97706"),
            ("claude › ", "bold #D97706"),
        ),
        end="",
    )


def print_tool_call(tool_name: str, args_summary: str) -> None:
    """Claude Code birebir araç çağrı formatı: ● ToolName(args)."""
    claude_tool_name = _get_claude_tool_name(tool_name)

    title = Text()
    title.append(f"  ● ", style="bold #D97706")
    title.append(f"{claude_tool_name}", style="bold #38BDF8")
    if args_summary:
        title.append(f"({args_summary})", style="dim #94A3B8")
    else:
        title.append("()", style="dim #94A3B8")

    console.print(title)


def print_tool_result(result: str, max_lines: int = 15) -> None:
    """Claude Code stili araç çıktı özeti: ↳ Çıktı."""
    lines = result.strip().split("\n")
    if not lines or (len(lines) == 1 and not lines[0]):
        console.print(Text("    ↳ Tamamlandı", style="dim #94A3B8"))
        console.print()
        return

    # İlk satırı ana özet olarak ver
    first_line = lines[0].strip()
    if len(lines) == 1:
        console.print(Text(f"    ↳ {first_line}", style="dim #94A3B8"))
    else:
        console.print(Text(f"    ↳ {first_line}", style="dim #94A3B8"))
        display_lines = lines[1:max_lines]
        for line in display_lines:
            console.print(Text(f"      {line}", style="#94A3B8"))
        if len(lines) > max_lines:
            console.print(Text(f"      ... [{len(lines) - max_lines} satır daha]", style="dim"))

    console.print()


def print_permission_request(action: str, detail: str) -> str:
    """Claude Code stili izin onay kartı."""
    panel_content = Text()
    panel_content.append(f"{action}\n", style="bold spark.warning")
    panel_content.append(f"{detail}\n\n", style="spark.text_dim")
    panel_content.append("Onaylıyor musunuz? [e: Evet / h: Hayır / her zaman: Bu oturumda hep izin ver]", style="bold #D97706")

    console.print(
        Panel(
            panel_content,
            title="▲ İzin İsteği",
            title_align="left",
            border_style="#D97706",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    response = console.input(Text("  Onay [e/h/her zaman] ❯ ", style="bold #D97706"))
    return response.strip().lower()


def print_error(message: str) -> None:
    """Hata mesajı."""
    error_console.print(
        Text.assemble(
            ("  ✗ ", "bold #EF4444"),
            (message, "#EF4444"),
        )
    )


def print_warning(message: str) -> None:
    """Uyarı mesajı."""
    console.print(
        Text.assemble(
            ("  ▲ ", "bold #F59E0B"),
            (message, "#F59E0B"),
        )
    )


def print_success(message: str) -> None:
    """Başarı mesajı."""
    console.print(
        Text.assemble(
            ("  ✓ ", "bold #10B981"),
            (message, "#10B981"),
        )
    )


def print_info(message: str) -> None:
    """Bilgi mesajı."""
    console.print(
        Text.assemble(
            ("  ℹ ", "bold #38BDF8"),
            (message, "dim #94A3B8"),
        )
    )


def print_session_status(
    model: str,
    tokens_used: int,
    context_max: int,
    files_in_context: list[str],
    messages_count: int,
) -> None:
    """Claude Code /status paneli."""
    table = Table(
        title="⚡ Claude Code Oturum Durumu",
        box=box.ROUNDED,
        border_style="#475569",
        title_style="bold #D97706",
        show_header=False,
        padding=(0, 2),
    )
    table.add_column("Özellik", style="dim #94A3B8")
    table.add_column("Değer", style="#F8FAFC")

    table.add_row("Aktif Model", model)
    table.add_row("Token Kullanımı", f"{tokens_used:,} / {context_max:,}")
    table.add_row("Mesaj Sayısı", str(messages_count))
    table.add_row("Bağlamdaki Dosyalar", str(len(files_in_context)))
    if files_in_context:
        for f in files_in_context[:8]:
            table.add_row("", f"  📄 {Path(f).name}")

    console.print()
    console.print(table)
    console.print()


def _get_claude_tool_name(tool_name: str) -> str:
    """Tool adlarını Claude Code formatına çevirir."""
    mapping = {
        "read_file": "Read",
        "write_file": "Write",
        "edit_file": "Edit",
        "search_code": "Grep",
        "list_dir": "LS",
        "run_command": "Bash",
        "git_status": "GitStatus",
        "git_diff": "GitDiff",
        "git_commit": "GitCommit",
        "web_search": "WebSearch",
    }
    return mapping.get(tool_name, tool_name.title())
