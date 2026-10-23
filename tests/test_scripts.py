"""Unit tests verifying bash operational scripts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestShellScripts:
    def test_check_blacklist_clean(self, tmp_path: pytest.TempPathFactory) -> None:
        clean_dir = tmp_path / "clean_dir"
        clean_dir.mkdir()
        (clean_dir / "clean_file.py").write_text("x = 42\nprint('all clean')\n")

        res = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "check_blacklist.sh"), str(clean_dir)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
        assert "BLACK_LIST_CLEAN" in res.stdout

    def test_check_blacklist_catches_sensitive_string(self, tmp_path: pytest.TempPathFactory) -> None:
        dirty_dir = tmp_path / "dirty_dir"
        dirty_dir.mkdir()
        forbidden_key = "".join(["OPEN", "CLAW", "_TOKEN"])
        (dirty_dir / "dirty_file.py").write_text(f"API_TOKEN = '{forbidden_key}_XYZ'\n")

        res = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "check_blacklist.sh"), str(dirty_dir)],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 1
        assert "SECURITY VIOLATION: Blacklisted strings detected!" in res.stdout

    def test_audit_image_script_executable(self) -> None:
        script = SCRIPTS_DIR / "audit_image.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_audit_image_syntax_check(self) -> None:
        res = subprocess.run(
            ["bash", "-n", str(SCRIPTS_DIR / "audit_image.sh")],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0
