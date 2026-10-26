"""Markdown render bileşeni."""

from __future__ import annotations

from rich.markdown import Markdown

from spark.ui.console import console


def render_markdown(text: str) -> None:
    """Markdown metnini terminalde render et."""
    if not text.strip():
        return

    md = Markdown(
        text,
        code_theme="monokai",
        inline_code_lexer="python",
    )
    console.print(md, width=min(console.width - 4, 100))


def render_code_block(code: str, language: str = "python", title: str | None = None) -> None:
    """Kod bloğunu syntax highlighting ile göster."""
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich import box

    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=True,
    )

    if title:
        console.print(Panel(
            syntax,
            title=title,
            border_style="spark.border",
            box=box.ROUNDED,
            padding=(0, 1),
        ))
    else:
        console.print(syntax)
