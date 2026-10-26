"""Kod arama tool'u — ripgrep ile hızlı arama, Python fallback."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from spark.tools.registry import ToolDefinition, ToolParameter


def search_code(pattern: str, path: str = ".", max_results: int = 30) -> str:
    """Kod tabanında metin/regex arama yap."""
    search_path = Path(path).resolve()

    if not search_path.exists():
        return f"Error: Path not found: {path}"

    # ripgrep varsa kullan (çok daha hızlı)
    if _has_ripgrep():
        return _search_with_ripgrep(pattern, str(search_path), max_results)

    # Fallback: Python ile arama
    return _search_with_python(pattern, search_path, max_results)


def _has_ripgrep() -> bool:
    """ripgrep (rg) yüklü mü kontrol et."""
    try:
        subprocess.run(
            ["rg", "--version"],
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _search_with_ripgrep(pattern: str, path: str, max_results: int) -> str:
    """ripgrep ile arama."""
    try:
        cmd = [
            "rg",
            "--no-heading",
            "--line-number",
            "--color=never",
            "--max-count", str(max_results),
            "--max-filesize", "1M",
            "--type-add", "code:*.{py,js,ts,jsx,tsx,java,c,cpp,h,go,rs,rb,php,cs,swift,kt}",
            pattern,
            path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            if len(lines) > max_results:
                lines = lines[:max_results]
                return "\n".join(lines) + f"\n\n... [{len(lines)} results shown, more available]"
            return "\n".join(lines)
        elif result.returncode == 1:
            return f"No matches found for: {pattern}"
        else:
            return f"Search error: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return "Error: Search timed out (>30s)"
    except Exception as e:
        return f"Error: {e}"


def _search_with_python(pattern: str, path: Path, max_results: int) -> str:
    """Python ile dosya arama (ripgrep fallback)."""
    results: list[str] = []

    # Aranacak dosya uzantıları
    extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
        ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".kt", ".md",
        ".json", ".yaml", ".yml", ".toml", ".txt", ".html", ".css",
    }

    # Göz ardı edilecek dizinler
    skip_dirs = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".next", ".cache", ".spark",
    }

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        # Regex değilse literal arama yap
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    try:
        for root, dirs, files in os.walk(path):
            # Skip dirs
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for filename in files:
                if len(results) >= max_results:
                    break

                ext = Path(filename).suffix.lower()
                if ext not in extensions:
                    continue

                filepath = Path(root) / filename
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            rel_path = filepath.relative_to(path)
                            results.append(f"{rel_path}:{i}: {line.strip()}")
                            if len(results) >= max_results:
                                break
                except (PermissionError, OSError):
                    continue

            if len(results) >= max_results:
                break

    except Exception as e:
        return f"Error during search: {e}"

    if not results:
        return f"No matches found for: {pattern}"

    output = "\n".join(results)
    if len(results) >= max_results:
        output += f"\n\n... [showing first {max_results} results]"

    return output


SEARCH_CODE_TOOL = ToolDefinition(
    name="search_code",
    description="Search for text or regex pattern in code files. Uses ripgrep if available.",
    parameters=[
        ToolParameter(
            name="pattern",
            type="string",
            description="Search pattern (text or regex)",
            required=True,
        ),
        ToolParameter(
            name="path",
            type="string",
            description="Directory or file to search in. Defaults to current directory.",
            required=False,
        ),
    ],
    handler=search_code,
)
