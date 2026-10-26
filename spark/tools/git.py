"""Git işlemleri tool'u."""

from __future__ import annotations

import subprocess
from pathlib import Path

from spark.tools.registry import ToolDefinition, ToolParameter


def _run_git(args: list[str], cwd: str = "") -> tuple[bool, str]:
    """Git komutu çalıştır. (başarılı, çıktı) döndürür."""
    try:
        cmd = ["git"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd or None,
            encoding="utf-8",
            errors="replace",
        )

        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            return False, error or f"Git command failed (exit {result.returncode})"

        return True, output

    except FileNotFoundError:
        return False, "Error: git is not installed or not in PATH"
    except subprocess.TimeoutExpired:
        return False, "Error: git command timed out"
    except Exception as e:
        return False, f"Error: {e}"


def git_status(path: str = ".") -> str:
    """Git durumunu göster."""
    success, output = _run_git(["status", "--short", "--branch"], cwd=path)
    if not success:
        return f"Git error: {output}"

    if not output:
        return "Clean working tree (no changes)."

    return output


def git_diff(path: str = ".", staged: bool = False) -> str:
    """Git diff göster."""
    args = ["diff", "--stat"]
    if staged:
        args.append("--staged")

    success, output = _run_git(args, cwd=path)
    if not success:
        return f"Git error: {output}"

    if not output:
        return "No changes to show."

    # Detaylı diff de ekle (kısaltılmış)
    detail_args = ["diff"]
    if staged:
        detail_args.append("--staged")

    _, detail = _run_git(detail_args, cwd=path)
    if detail:
        lines = detail.splitlines()
        if len(lines) > 100:
            detail = "\n".join(lines[:100]) + f"\n\n... [{len(lines) - 100} more lines]"

    return f"{output}\n\n{detail}" if detail else output


def git_commit(message: str, path: str = ".") -> str:
    """Git commit yap."""
    # Önce stage
    _run_git(["add", "-A"], cwd=path)

    # Commit
    success, output = _run_git(["commit", "-m", message], cwd=path)
    if not success:
        return f"Commit failed: {output}"

    return f"Committed: {output}"


# Tool tanımları
GIT_STATUS_TOOL = ToolDefinition(
    name="git_status",
    description="Show git status of the repository.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="Repository path. Defaults to current directory.",
            required=False,
        ),
    ],
    handler=git_status,
)

GIT_DIFF_TOOL = ToolDefinition(
    name="git_diff",
    description="Show git diff of changes.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="Repository path. Defaults to current directory.",
            required=False,
        ),
        ToolParameter(
            name="staged",
            type="boolean",
            description="Show staged changes only. Default false.",
            required=False,
        ),
    ],
    handler=git_diff,
)

GIT_COMMIT_TOOL = ToolDefinition(
    name="git_commit",
    description="Stage all changes and create a git commit.",
    parameters=[
        ToolParameter(
            name="message",
            type="string",
            description="Commit message",
            required=True,
        ),
        ToolParameter(
            name="path",
            type="string",
            description="Repository path. Defaults to current directory.",
            required=False,
        ),
    ],
    handler=git_commit,
)
