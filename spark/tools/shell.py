"""Shell komut çalıştırma tool'u — güvenlik kontrolleri ile."""

from __future__ import annotations

import subprocess
import os
import sys

from spark.tools.registry import ToolDefinition, ToolParameter


# Maksimum komut çıktısı (karakter)
MAX_OUTPUT_CHARS = 10000
# Komut zaman aşımı (saniye)
DEFAULT_TIMEOUT = 60


def run_command(command: str, cwd: str = "") -> str:
    """Shell komutu çalıştır."""
    working_dir = cwd if cwd else os.getcwd()

    try:
        # Windows'ta shell=True, Unix'te uygun shell
        is_windows = sys.platform == "win32"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT,
            cwd=working_dir,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        output_parts: list[str] = []

        if result.stdout:
            stdout = result.stdout.strip()
            if len(stdout) > MAX_OUTPUT_CHARS:
                stdout = stdout[:MAX_OUTPUT_CHARS] + f"\n\n... [output truncated, {len(result.stdout)} total chars]"
            output_parts.append(stdout)

        if result.stderr:
            stderr = result.stderr.strip()
            if len(stderr) > MAX_OUTPUT_CHARS:
                stderr = stderr[:MAX_OUTPUT_CHARS] + "\n... [stderr truncated]"
            if stderr:
                output_parts.append(f"[stderr]\n{stderr}")

        if result.returncode != 0:
            output_parts.insert(0, f"[exit code: {result.returncode}]")

        if not output_parts:
            if result.returncode == 0:
                return "Command completed successfully (no output)."
            else:
                return f"Command failed with exit code {result.returncode} (no output)."

        return "\n".join(output_parts)

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {DEFAULT_TIMEOUT}s: {command}"
    except FileNotFoundError:
        return f"Error: Command not found. Make sure it's installed and in PATH."
    except PermissionError:
        return f"Error: Permission denied to execute: {command}"
    except Exception as e:
        return f"Error running command: {type(e).__name__}: {e}"


RUN_COMMAND_TOOL = ToolDefinition(
    name="run_command",
    description="Run a shell command and return its output. Use with caution.",
    parameters=[
        ToolParameter(
            name="command",
            type="string",
            description="Shell command to execute",
            required=True,
        ),
        ToolParameter(
            name="cwd",
            type="string",
            description="Working directory. Defaults to current directory.",
            required=False,
        ),
    ],
    handler=run_command,
)
