"""Unit tests for contract assertions, scenario harness, and LLM telemetry."""

import pytest
import pandas as pd
from unittest.mock import MagicMock

from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    EvalAssertionError,
)
from ai_ops_eval_harness.assertions import (
    audit_temporal_completeness,
    assert_decoupled_json_contract,
    assert_ultra_concise_disclosure,
    assert_prompt_context_integrity,
)
from ai_ops_eval_harness.scenarios import (
    BlastShield,
    QAScenario,
    ScenarioHarness,
)
from ai_ops_eval_harness.telemetry import track_llm_telemetry


class TestTemporalCompleteness:
    def test_completeness_complete_dataset(self):
        df = pd.DataFrame({"revenue": [100.0, 200.0, 300.0]})
        res = audit_temporal_completeness(df, expected_days=3)
        assert res["status"] == "complete"
        assert res["completeness_pct"] == 100.0

    def test_completeness_partial_dataset(self):
        df = pd.DataFrame({"revenue": [100.0, 0.0, 150.0]})
        res = audit_temporal_completeness(df, expected_days=3)
        assert res["status"] == "partial_starvation"
        assert res["valid_days"] == 2
        assert res["completeness_pct"] == 66.67

    def test_completeness_fatal_starvation_raises(self):
        df = pd.DataFrame({"revenue": [0.0, 0.0, 0.0]})
        with pytest.raises(DataStarvationError, match="0 valid days with positive revenue"):
            audit_temporal_completeness(df, expected_days=3, raise_on_fatal=True)

    def test_completeness_fatal_starvation_silent(self):
        df = pd.DataFrame({"revenue": [0.0, 0.0]})
        res = audit_temporal_completeness(df, expected_days=2, raise_on_fatal=False)
        assert res["status"] == "fatal_starvation"


class TestDecoupledJsonContract:
    def test_valid_json_payload(self):
        payload = {
            "status": "success",
            "text": "Report completed successfully. ![Chart](https://storage.local/chart.png)",
            "chart_path": "/storage/chart.png",
        }
        assert_decoupled_json_contract(payload)

    def test_missing_required_key(self):
        with pytest.raises(EvalAssertionError, match="Missing required key 'text'"):
            assert_decoupled_json_contract({"status": "success"})

    def test_unexpected_status(self):
        with pytest.raises(EvalAssertionError, match="Unexpected status 'unknown_status'"):
            assert_decoupled_json_contract({"status": "unknown_status", "text": "Hello"})

    def test_raw_traceback_leak_rejected(self):
        payload = {
            "status": "error",
            "text": "Failed: Traceback (most recent call last):\n  File 'app.py', line 12",
        }
        with pytest.raises(EvalAssertionError, match="Raw python traceback detected"):
            assert_decoupled_json_contract(payload)

    def test_unparsed_error_xml_tags_rejected(self):
        payload = {
            "status": "error",
            "text": "<ERROR>Connection timeout to database</ERROR>",
        }
        with pytest.raises(EvalAssertionError, match="Unparsed <ERROR> XML tags detected"):
            assert_decoupled_json_contract(payload)

    def test_forbidden_media_tags_rejected(self):
        payload = {
            "status": "success",
            "text": "Here is chart: <media>/path/to/chart.png</media>",
        }
        with pytest.raises(EvalAssertionError, match="Forbidden XML <media> tag detected"):
            assert_decoupled_json_contract(payload)


class TestUltraConciseDisclosure:
    def test_ultra_concise_mode_passes(self):
        text = "Resumen diario:\n* Ventas brutas: $10,000\n* Crecimiento DoD: +5%\n* Ordenes: 120"
        res = assert_ultra_concise_disclosure(text, user_prompt="dame el reporte de ayer")
        assert res["is_expanded_request"] is False
        assert res["bullet_count"] == 3

    def test_ultra_concise_mode_rejects_markdown_table(self):
        text = "Ventas:\n| Dia | Monto |\n| --- | --- |\n| Lun | $500 |"
        with pytest.raises(EvalAssertionError, match="Markdown table generated in default ultra-concise mode"):
            assert_ultra_concise_disclosure(text, user_prompt="reporte normal")

    def test_ultra_concise_mode_rejects_excessive_bullets(self):
        text = "* B1\n* B2\n* B3\n* B4\n* B5"
        with pytest.raises(EvalAssertionError, match="Output contains 5 bullets, exceeding"):
            assert_ultra_concise_disclosure(text, user_prompt="reporte normal", max_bullet_points=4)

    def test_expanded_mode_allows_table_and_bullets(self):
        text = "Desglose completo:\n| Producto | Total |\n| --- | --- |\n* Item 1\n* Item 2\n* Item 3\n* Item 4\n* Item 5"
        res = assert_ultra_concise_disclosure(text, user_prompt="dame el reporte detallado con desglose")
        assert res["is_expanded_request"] is True
        assert res["has_markdown_table"] is True


class TestPromptContextIntegrity:
    def test_prompt_integrity_passes(self):
        ctx = "=== REPORT ===\n<DATA>\ndate,rev\n2026-08-01,100\n</DATA>\nDATO EXACTO UPT: 2.0"
        assert_prompt_context_integrity(
            prompt_context=ctx,
            required_markers=["=== REPORT ===", "<DATA>", "DATO EXACTO UPT: 2.0"],
            forbidden_markers=["<SECRET_KEY>", "UNKNOWN_VARIABLE"],
        )

    def test_prompt_integrity_missing_marker(self):
        ctx = "=== REPORT ==="
        with pytest.raises(EvalAssertionError, match="Missing required marker '<DATA>'"):
            assert_prompt_context_integrity(ctx, required_markers=["<DATA>"])

    def test_prompt_integrity_forbidden_marker(self):
        ctx = "=== REPORT === <SECRET_KEY>"
        with pytest.raises(EvalAssertionError, match="Forbidden marker '<SECRET_KEY>'"):
            assert_prompt_context_integrity(ctx, required_markers=["=== REPORT ==="], forbidden_markers=["<SECRET_KEY>"])


class TestScenarioHarness:
    def test_blast_shield_intercepts_calls(self):
        shield = BlastShield(simulate_success=True)
        with shield:
            ok = shield.record_dispatch("+1234567890", {"message": "Hello"})
            assert ok is True

        assert len(shield.intercepted_calls) == 1
        assert shield.intercepted_calls[0]["destination"] == "+1234567890"

    def test_scenario_harness_suite(self):
        harness = ScenarioHarness(name="ai_ops_test_suite")

        # Scenario 1: passing
        harness.register(
            QAScenario(
                name="valid_report_flow",
                description="Checks successful report generation",
                runner=lambda: {"status": "success", "text": "* Venta: $1000"},
                assertions=[lambda out: assert_decoupled_json_contract(out)],
            )
        )

        # Scenario 2: failing assertion
        harness.register(
            QAScenario(
                name="starvation_simulation",
                description="Checks that starvation raises error",
                runner=lambda: audit_temporal_completeness(pd.DataFrame(), expected_days=5),
            )
        )

        report = harness.run_all()
        assert report["total_scenarios"] == 2
        assert report["passed"] == 1
        assert report["failed"] == 1
        assert report["success_rate_pct"] == 50.0


class TestTelemetryDecorator:
    def test_telemetry_successful_call(self):
        mock_response = MagicMock()
        mock_response.usage_metadata.total_token_count = 150

        @track_llm_telemetry(retries=2)
        def call_llm(model="test_model"):
            return mock_response

        res = call_llm(model="test_model")
        assert res is mock_response

    def test_telemetry_retry_on_429(self):
        attempts = 0

        @track_llm_telemetry(retries=3, base_backoff=0.01)
        def call_flaky_llm():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RuntimeError("429 Too Many Requests")
            mock_res = MagicMock()
            mock_res.usage_metadata.total_token_count = 50
            return mock_res

        res = call_flaky_llm()
        assert attempts == 2
        assert res.usage_metadata.total_token_count == 50

    def test_telemetry_exhaustion_triggers_alert(self):
        alert_payload = None

        def record_alert(payload):
            nonlocal alert_payload
            alert_payload = payload

        @track_llm_telemetry(retries=2, base_backoff=0.01, on_alert=record_alert)
        def call_failing_llm():
            raise ConnectionError("Server unavailable")

        with pytest.raises(ConnectionError):
            call_failing_llm()

        assert alert_payload is not None
        assert alert_payload["event"] == "LLM_TELEMETRY_EXHAUSTION"
        assert alert_payload["attempts"] == 2
