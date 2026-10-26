"""Dizin ağacı listeleme tool'u."""

from __future__ import annotations

import os
from pathlib import Path

from spark.tools.registry import ToolDefinition, ToolParameter


# Göz ardı edilecek dizinler
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".next", ".cache", ".spark", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "egg-info", ".tox",
    ".idea", ".vscode", ".vs",
}

# Göz ardı edilecek dosyalar
SKIP_FILES = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
}


def list_dir(path: str = ".", max_depth: int = 3, max_items: int = 100) -> str:
    """Dizin içeriğini ağaç yapısında listele."""
    dir_path = Path(path).resolve()

    if not dir_path.exists():
        return f"Error: Path not found: {path}"

    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"

    lines: list[str] = [f"{dir_path.name}/"]
    item_count = [0]

    _build_tree(dir_path, lines, "", max_depth, 0, max_items, item_count)

    if item_count[0] >= max_items:
        lines.append(f"\n... [truncated at {max_items} items]")

    return "\n".join(lines)


def _build_tree(
    dir_path: Path,
    lines: list[str],
    prefix: str,
    max_depth: int,
    current_depth: int,
    max_items: int,
    item_count: list[int],
) -> None:
    """Recursive ağaç yapıcı."""
    if current_depth >= max_depth or item_count[0] >= max_items:
        return

    try:
        entries = sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        lines.append(f"{prefix}[permission denied]")
        return

    # Filtreleme
    entries = [
        e for e in entries
        if e.name not in SKIP_DIRS and e.name not in SKIP_FILES
        and not e.name.startswith(".")  # Gizli dosyalar (isteğe bağlı)
        or e.name in (".env", ".gitignore", ".spark")  # Önemli gizli dosyalar
    ]

    for i, entry in enumerate(entries):
        if item_count[0] >= max_items:
            return

        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "

        if entry.is_dir():
            child_count = _count_children(entry)
            lines.append(f"{prefix}{connector}{entry.name}/ ({child_count})")
            item_count[0] += 1
            _build_tree(
                entry, lines, prefix + extension,
                max_depth, current_depth + 1, max_items, item_count,
            )
        else:
            size = _format_size(entry.stat().st_size)
            lines.append(f"{prefix}{connector}{entry.name} ({size})")
            item_count[0] += 1


def _count_children(dir_path: Path) -> str:
    """Dizindeki çocuk sayısını say."""
    try:
        count = sum(1 for _ in dir_path.iterdir())
        return f"{count} items"
    except PermissionError:
        return "?"


def _format_size(bytes_size: int) -> str:
    """Dosya boyutunu okunabilir formata çevir."""
    if bytes_size < 1024:
        return f"{bytes_size}B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f}KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f}MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f}GB"


LIST_DIR_TOOL = ToolDefinition(
    name="list_dir",
    description="List directory contents as a tree. Shows files and subdirectories.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="Directory path to list. Defaults to current directory.",
            required=False,
        ),
        ToolParameter(
            name="max_depth",
            type="integer",
            description="Maximum tree depth. Default 3.",
            required=False,
        ),
    ],
    handler=list_dir,
)
