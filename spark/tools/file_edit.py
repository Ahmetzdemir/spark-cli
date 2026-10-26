"""Dosya düzenleme tool'u — search-replace yöntemiyle."""

from __future__ import annotations

from pathlib import Path

from spark.tools.registry import ToolDefinition, ToolParameter


_backup_callback = None


def set_backup_callback(callback) -> None:
    """Dosya yedekleme callback'ini ayarla."""
    global _backup_callback
    _backup_callback = callback


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Dosyadaki metni bul ve değiştir (search-replace).

    4B modeller için en güvenilir düzenleme yöntemi:
    tam metin eşleşmesi arar ve değiştirir.
    """
    try:
        filepath = Path(path).resolve()

        if not filepath.exists():
            return f"Error: File not found: {path}"

        content = filepath.read_text(encoding="utf-8")

        # Metin arama
        if old_text not in content:
            # Boşluk/tab farklılıkları ile tekrar dene
            normalized_content = _normalize_whitespace(content)
            normalized_old = _normalize_whitespace(old_text)

            if normalized_old in normalized_content:
                # Orijinal içerikte bul
                idx = normalized_content.index(normalized_old)
                # Orijinal satırlarda karşılık gelen bölümü bul
                lines = content.splitlines(keepends=True)
                char_count = 0
                start_line = 0
                end_line = 0
                for i, line in enumerate(lines):
                    if char_count <= idx < char_count + len(line):
                        start_line = i
                    if char_count + len(line) >= idx + len(normalized_old):
                        end_line = i + 1
                        break
                    char_count += len(line)

                # Çevredeki satırları göster
                context_lines = content.splitlines()
                nearby = context_lines[max(0, start_line-2):min(len(context_lines), end_line+2)]
                return (
                    f"Error: Exact text not found but similar text exists near lines "
                    f"{start_line+1}-{end_line}. Here's the area:\n"
                    + "\n".join(f"  {i+start_line-1}: {l}" for i, l in enumerate(nearby))
                    + "\nPlease use the exact text from the file."
                )
            else:
                return (
                    f"Error: Text not found in {filepath.name}. "
                    f"Read the file first to see exact content."
                )

        # Birden fazla eşleşme kontrolü
        count = content.count(old_text)
        if count > 1:
            return (
                f"Warning: Found {count} occurrences of the search text. "
                f"Please provide more context to make the match unique. "
                f"Include surrounding lines in old_text."
            )

        # Yedek al
        if _backup_callback:
            _backup_callback(str(filepath), content)

        # Değiştir
        new_content = content.replace(old_text, new_text, 1)
        filepath.write_text(new_content, encoding="utf-8")

        # Değişiklik özeti
        old_lines = old_text.count("\n") + 1
        new_lines = new_text.count("\n") + 1
        return (
            f"Edited {filepath.name}: replaced {old_lines} lines with {new_lines} lines. "
            f"({_count_diff(old_text, new_text)})"
        )

    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error editing file: {e}"


def _normalize_whitespace(text: str) -> str:
    """Boşluk/tab farklılıklarını normalize et."""
    import re
    return re.sub(r'[ \t]+', ' ', text).strip()


def _count_diff(old: str, new: str) -> str:
    """Eklenen/silinen satır sayısını hesapla."""
    old_lines = set(old.splitlines())
    new_lines = set(new.splitlines())

    added = len(new_lines - old_lines)
    removed = len(old_lines - new_lines)

    parts = []
    if added:
        parts.append(f"+{added}")
    if removed:
        parts.append(f"-{removed}")

    return ", ".join(parts) if parts else "no line count change"


EDIT_FILE_TOOL = ToolDefinition(
    name="edit_file",
    description="Edit a file by finding and replacing exact text. Read the file first to see exact content.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="File path to edit",
            required=True,
        ),
        ToolParameter(
            name="old_text",
            type="string",
            description="Exact text to find and replace",
            required=True,
        ),
        ToolParameter(
            name="new_text",
            type="string",
            description="New text to replace with",
            required=True,
        ),
    ],
    handler=edit_file,
)
