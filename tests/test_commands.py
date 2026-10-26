"""Slash komutları testleri — Claude Code Komut Paketi."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from spark.commands.registry import build_command_registry
from spark.core.agent import Agent
from spark.config import SparkConfig
from spark.llm.client import LMStudioClient


def test_command_registry_build():
    """Slash komut registry oluşturma ve alias testi."""
    reg = build_command_registry()
    names = reg.get_command_names()
    assert "/cost" in names
    assert "/doctor" in names
    assert "/init" in names
    assert "/review" in names
    assert "/add" in names
    assert "/drop" in names
    assert "/files" in names
    assert "/commit" in names
    assert "/diff" in names
    assert "/undo" in names
    assert "/compact" in names
    assert "/clear" in names
    assert "/model" in names
    assert "/help" in names
    assert "/exit" in names
    assert "/config" in names


def test_slash_command_execution():
    """Temel komut çalıştırma testi."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "sample.py"
        test_file.write_text("print('hello')", encoding="utf-8")

        config = SparkConfig()
        llm = LMStudioClient(config.llm)
        agent = Agent(config=config, llm_client=llm, project_dir=tmpdir)
        reg = build_command_registry()

        # /cost komutu
        is_cmd, res = reg.parse_and_execute("/cost", agent)
        assert is_cmd is True
        assert "Token" in res

        # /init komutu (CLAUDE.md oluşturur)
        is_cmd, res = reg.parse_and_execute("/init", agent)
        assert is_cmd is True
        assert (Path(tmpdir) / "CLAUDE.md").exists()

        # /doctor komutu
        is_cmd, res = reg.parse_and_execute("/doctor", agent)
        assert is_cmd is True
        assert "Doctor" in res

        # /add komutu
        is_cmd, res = reg.parse_and_execute(f"/add {test_file}", agent)
        assert is_cmd is True
        assert "Eklendi" in res
        assert str(test_file) in agent.files_in_context

        # /files komutu
        is_cmd, res = reg.parse_and_execute("/files", agent)
        assert is_cmd is True
        assert "sample.py" in res

        # /drop komutu
        is_cmd, res = reg.parse_and_execute(f"/drop {test_file}", agent)
        assert is_cmd is True
        assert "Çıkarıldı" in res

        # /config komutu
        is_cmd, res = reg.parse_and_execute("/config", agent)
        assert is_cmd is True
        assert "Claude Code" in res or "Spark" in res

        # /clear komutu
        is_cmd, res = reg.parse_and_execute("/clear", agent)
        assert is_cmd is True
        assert "temizlendi" in res
