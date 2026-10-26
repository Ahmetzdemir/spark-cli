"""Dosya okuma tool'u."""

from __future__ import annotations

from pathlib import Path

from spark.tools.registry import ToolDefinition, ToolParameter


def read_file(path: str, start_line: int = 0, end_line: int = 0) -> str:
    """Dosya oku. start_line/end_line verilirse sadece o aralığı oku."""
    try:
        filepath = Path(path).resolve()

        if not filepath.exists():
            return f"Error: File not found: {path}"

        if not filepath.is_file():
            return f"Error: Not a file: {path}"

        # Büyük dosya kontrolü (1MB üzeri)
        file_size = filepath.stat().st_size
        if file_size > 1_000_000:
            return (
                f"Warning: File is very large ({file_size:,} bytes). "
                f"Use start_line and end_line to read a specific range."
            )

        content = filepath.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        # Satır aralığı belirtilmişse
        if start_line > 0 or end_line > 0:
            start = max(0, start_line - 1)  # 1-indexed → 0-indexed
            end = end_line if end_line > 0 else len(lines)
            selected = lines[start:end]

            header = f"[{filepath.name} lines {start_line}-{end or len(lines)} of {len(lines)}]\n"
            return header + "\n".join(
                f"{i + start + 1:4d} │ {line}"
                for i, line in enumerate(selected)
            )

        # Tüm dosya (maksimum 200 satır göster)
        max_lines = 200
        if len(lines) > max_lines:
            header = f"[{filepath.name} — {len(lines)} lines, showing first {max_lines}]\n"
            truncated = lines[:max_lines]
            return header + "\n".join(
                f"{i + 1:4d} │ {line}"
                for i, line in enumerate(truncated)
            ) + f"\n\n... [{len(lines) - max_lines} more lines]"

        return f"[{filepath.name} — {len(lines)} lines]\n" + "\n".join(
            f"{i + 1:4d} │ {line}"
            for i, line in enumerate(lines)
        )

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except UnicodeDecodeError:
        return f"Error: Cannot read binary file: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


# Tool tanımı
READ_FILE_TOOL = ToolDefinition(
    name="read_file",
    description="Read a file's contents. Use start_line and end_line to read a specific range.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="File path to read",
            required=True,
        ),
        ToolParameter(
            name="start_line",
            type="integer",
            description="Start line number (1-indexed). 0 means from beginning.",
            required=False,
        ),
        ToolParameter(
            name="end_line",
            type="integer",
            description="End line number (1-indexed, inclusive). 0 means to end.",
            required=False,
        ),
    ],
    handler=read_file,
)
