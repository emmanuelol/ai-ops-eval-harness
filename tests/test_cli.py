"""Unit tests for ai-ops-eval CLI commands."""

from __future__ import annotations

import json
import pytest

from ai_ops_eval_harness.cli import main


class TestCLI:
    def test_cli_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "usage: ai-ops-eval" in captured.out

    def test_cli_no_args_shows_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main([])
        assert code == 0
        captured = capsys.readouterr()
        assert "usage: ai-ops-eval" in captured.out

    def test_cli_eval_default(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["eval"])
        assert code == 0
        captured = capsys.readouterr()
        assert "Evaluation Harness" in captured.out
        assert "Passed          : 1" in captured.out

    def test_cli_eval_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["eval", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_scenarios"] == 1
        assert data["passed"] == 1
        assert data["failed"] == 0

    def test_cli_reconcile_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main([
            "reconcile",
            "--primary-gross", "1000",
            "--secondary-gross", "500",
            "--secondary-net", "400",
            "--secondary-tax", "50",
            "--secondary-fee", "50",
        ])
        assert code == 0
        captured = capsys.readouterr()
        assert "Reconciliation Succeeded" in captured.out
        assert "Consolidated Gross: 1500.00" in captured.out

    def test_cli_reconcile_anomaly_fails(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main([
            "reconcile",
            "--primary-gross", "1000",
            "--secondary-gross", "500",
            "--secondary-net", "480",  # Anomaly: 500 - 50 - 50 = 400 != 480
            "--secondary-tax", "50",
            "--secondary-fee", "50",
        ])
        assert code == 2
        captured = capsys.readouterr()
        assert "FINANCIAL ANOMALY ERROR" in captured.err

    def test_cli_starvation_check_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["starvation-check", "--initial", "100", "--final", "99"])
        assert code == 0
        captured = capsys.readouterr()
        assert "STARVATION CHECK PASSED" in captured.out

    def test_cli_starvation_check_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["starvation-check", "--initial", "100", "--final", "0"])
        assert code == 2
        captured = capsys.readouterr()
        assert "DATA STARVATION ERROR" in captured.err
