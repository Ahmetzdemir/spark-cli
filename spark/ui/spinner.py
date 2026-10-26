"""Yükleme animasyonları ve spinner."""

from __future__ import annotations

import contextlib
from typing import Generator

from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from spark.ui.console import console
from spark.ui.themes import ICONS


@contextlib.contextmanager
def thinking_spinner(message: str = "Düşünüyor...") -> Generator[Live, None, None]:
    """Düşünme/yükleme spinner'ı."""
    spinner = Spinner(
        "dots",
        text=Text.assemble(
            (f"  {ICONS['thinking']} ", "spark.accent"),
            (message, "spark.text_dim"),
        ),
        style="spark.accent",
    )
    with Live(spinner, console=console, refresh_per_second=10, transient=True) as live:
        yield live


@contextlib.contextmanager
def tool_spinner(tool_name: str) -> Generator[Live, None, None]:
    """Tool çalışma spinner'ı."""
    spinner = Spinner(
        "dots2",
        text=Text.assemble(
            ("  │ ", "spark.border"),
            (f"Çalıştırılıyor: ", "spark.text_dim"),
            (tool_name, "spark.tool_name"),
        ),
        style="spark.accent",
    )
    with Live(spinner, console=console, refresh_per_second=10, transient=True) as live:
        yield live
