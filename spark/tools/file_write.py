"""Dosya yazma tool'u."""

from __future__ import annotations

from pathlib import Path

from spark.tools.registry import ToolDefinition, ToolParameter


# Bu modül-seviyesi referans, agent tarafından set edilir
_backup_callback = None


def set_backup_callback(callback) -> None:
    """Dosya yedekleme callback'ini ayarla."""
    global _backup_callback
    _backup_callback = callback


def write_file(path: str, content: str) -> str:
    """Yeni dosya oluştur veya mevcut dosyanın tamamını üzerine yaz."""
    try:
        filepath = Path(path).resolve()

        # Yedek al (undo için)
        old_content = None
        if filepath.exists():
            try:
                old_content = filepath.read_text(encoding="utf-8")
            except Exception:
                pass

        if _backup_callback:
            _backup_callback(str(filepath), old_content)

        # Dizin yoksa oluştur
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Yaz
        filepath.write_text(content, encoding="utf-8")

        lines = content.count("\n") + 1
        if old_content is None:
            return f"Created new file: {filepath} ({lines} lines)"
        else:
            return f"Overwrote file: {filepath} ({lines} lines)"

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error writing file: {e}"


WRITE_FILE_TOOL = ToolDefinition(
    name="write_file",
    description="Create a new file or overwrite an existing file with the given content.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="File path to write",
            required=True,
        ),
        ToolParameter(
            name="content",
            type="string",
            description="Full file content to write",
            required=True,
        ),
    ],
    handler=write_file,
)
