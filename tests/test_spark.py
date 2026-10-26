"""Spark CLI Unit Testleri."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest

from spark.tools.file_read import read_file
from spark.tools.file_write import write_file
from spark.tools.file_edit import edit_file
from spark.tools.search import search_code
from spark.tools.tree import list_dir
from spark.tools.shell import run_command
from spark.core.context import ContextManager
from spark.core.permissions import PermissionManager, PermissionLevel
from spark.config import PermissionsConfig
from spark.llm.models import get_model_profile, MODEL_PROFILES


def test_file_read_and_write():
    """Dosya yazma ve okuma testi."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        content = "Satır 1\nSatır 2\nSatır 3\nSatır 4\nSatır 5"

        # Yaz
        res_write = write_file(str(test_file), content)
        assert "Created" in res_write or "lines" in res_write
        assert test_file.exists()

        # Tam oku
        res_read = read_file(str(test_file))
        assert "Satır 1" in res_read
        assert "Satır 5" in res_read

        # Aralık oku
        res_range = read_file(str(test_file), start_line=2, end_line=4)
        assert "Satır 2" in res_range
        assert "Satır 4" in res_range
        assert "Satır 1" not in res_range


def test_file_edit_search_replace():
    """Dosya düzenleme (search-replace) testi."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "code.py"
        content = "def hello():\n    print('eski')\n"
        test_file.write_text(content, encoding="utf-8")

        # Değiştir
        res_edit = edit_file(str(test_file), "print('eski')", "print('yeni')")
        assert "Edited" in res_edit

        new_content = test_file.read_text(encoding="utf-8")
        assert "print('yeni')" in new_content
        assert "print('eski')" not in new_content


def test_search_code():
    """Kod arama testi."""
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "app.py"
        f1.write_text("def find_me_func():\n    pass\n", encoding="utf-8")

        res = search_code("find_me_func", path=tmpdir)
        assert "find_me_func" in res
        assert "app.py" in res


def test_list_dir():
    """Dizin ağacı listeleme testi."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "folder").mkdir()
        (Path(tmpdir) / "folder" / "sub.py").write_text("print()", encoding="utf-8")
        (Path(tmpdir) / "main.py").write_text("print()", encoding="utf-8")

        res = list_dir(tmpdir)
        assert "main.py" in res
        assert "folder/" in res


def test_run_command():
    """Shell komutu çalıştırma testi."""
    res = run_command("python -c \"print('SPARK_OK')\"")
    assert "SPARK_OK" in res


def test_context_manager_trimming():
    """Context ve token kırpma testi."""
    cm = ContextManager(max_context=1000)
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Msg 1 " * 50},
        {"role": "assistant", "content": "Resp 1 " * 50},
        {"role": "user", "content": "Msg 2 " * 50},
        {"role": "assistant", "content": "Resp 2 " * 50},
        {"role": "user", "content": "Latest message"},
    ]

    trimmed = cm.trim_messages(messages)
    assert len(trimmed) <= len(messages)
    # Son mesajın korunduğundan emin ol
    assert trimmed[-1]["content"] == "Latest message"


def test_permission_manager():
    """İzin sistemi testi."""
    # Manuel onay modu
    cfg_manual = PermissionsConfig(
        auto_approve_read=True,
        auto_approve_write=False,
        auto_approve_execute=False,
        auto_approve_all=False,
        blocked_commands=["rm -rf /", "format"],
        whitelisted_commands=["npm test"],
    )
    pm = PermissionManager(cfg_manual)

    # Okuma tool'u -> otomatik onay
    allowed, _ = pm.check_permission("read_file", {"path": "test.py"})
    assert allowed is True

    # Yazma tool'u -> onay gerektirir
    allowed, msg = pm.check_permission("write_file", {"path": "test.py"})
    assert allowed is False
    assert "test.py" in msg

    # Engelli komut -> ret
    allowed, msg = pm.check_permission("run_command", {"command": "rm -rf /"})
    assert allowed is False
    assert "engellenmiştir" in msg

    # Beyaz liste komut -> onay
    allowed, _ = pm.check_permission("run_command", {"command": "npm test"})
    assert allowed is True

    # Otomatik onay modu
    cfg_auto = PermissionsConfig(
        auto_approve_all=True,
        blocked_commands=["rm -rf /"],
    )
    pm_auto = PermissionManager(cfg_auto)
    allowed, _ = pm_auto.check_permission("write_file", {"path": "test.py"})
    assert allowed is True
    allowed, _ = pm_auto.check_permission("run_command", {"command": "pytest"})
    assert allowed is True
    allowed, msg = pm_auto.check_permission("run_command", {"command": "rm -rf /"})
    assert allowed is False


def test_model_profiles():
    """Model profil eşleme testi."""
    p1 = get_model_profile("qwen3-4b-instruct")
    assert "Qwen" in p1.display_name
    assert p1.context_window >= 16384

    p2 = get_model_profile("phi-4-mini")
    assert "Phi" in p2.display_name

    p3 = get_model_profile("google/gemma-4-e4b")
    assert "Gemma" in p3.display_name
