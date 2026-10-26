"""Diff görüntüleme bileşeni."""

from __future__ import annotations

import difflib

from rich.text import Text

from spark.ui.console import console


def show_diff(old_content: str, new_content: str, filename: str = "", max_lines: int = 50) -> None:
    """İki metin arasındaki diff'i renkli göster."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}" if filename else "eski",
        tofile=f"b/{filename}" if filename else "yeni",
        lineterm="",
    ))

    if not diff:
        console.print(Text("  Değişiklik yok.", style="spark.text_dim"))
        return

    console.print()
    shown = 0
    for line in diff:
        if shown >= max_lines:
            remaining = len(diff) - shown
            console.print(Text(
                f"  ... ({remaining} satır daha)",
                style="spark.text_dim",
            ))
            break

        line_stripped = line.rstrip("\n")

        if line.startswith("+++") or line.startswith("---"):
            console.print(Text(f"  {line_stripped}", style="spark.diff_header"))
        elif line.startswith("@@"):
            console.print(Text(f"  {line_stripped}", style="spark.info"))
        elif line.startswith("+"):
            console.print(Text(f"  {line_stripped}", style="spark.diff_add"))
        elif line.startswith("-"):
            console.print(Text(f"  {line_stripped}", style="spark.diff_remove"))
        else:
            console.print(Text(f"  {line_stripped}", style="spark.text_dim"))

        shown += 1

    console.print()


def show_file_changes_summary(changes: list[dict]) -> None:
    """Dosya değişikliklerinin özetini göster.

    changes: [{"file": str, "action": "created"|"modified"|"deleted", "lines_added": int, "lines_removed": int}]
    """
    if not changes:
        return

    console.print()
    for change in changes:
        action = change.get("action", "modified")
        filename = change.get("file", "?")
        added = change.get("lines_added", 0)
        removed = change.get("lines_removed", 0)

        if action == "created":
            icon = "✚"
            style = "spark.success"
        elif action == "deleted":
            icon = "✖"
            style = "spark.error"
        else:
            icon = "●"
            style = "spark.warning"

        line = Text()
        line.append(f"  {icon} ", style=style)
        line.append(filename, style="bold " + style)

        if added or removed:
            line.append("  ", style="")
            if added:
                line.append(f"+{added}", style="spark.diff_add")
            if added and removed:
                line.append(" ", style="")
            if removed:
                line.append(f"-{removed}", style="spark.diff_remove")

        console.print(line)

    console.print()
