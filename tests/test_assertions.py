"""Unit tests and property-based tests for evaluation assertions."""

from __future__ import annotations

from hypothesis import given, strategies as st
import pandas as pd
import pytest

from ai_ops_eval_harness.assertions import (
    assert_decoupled_json_contract,
    assert_prompt_context_integrity,
    assert_ultra_concise_disclosure,
    audit_temporal_completeness,
)
from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    EvalAssertionError,
)


class TestTemporalCompleteness:
    def test_completeness_complete_dataset(self, sample_timeseries_df: pd.DataFrame) -> None:
        res = audit_temporal_completeness(sample_timeseries_df, expected_days=3)
        assert res["status"] == "complete"
        assert res["completeness_pct"] == 100.0

    def test_completeness_partial_dataset(self) -> None:
        df = pd.DataFrame({"revenue": [100.0, 0.0, 150.0]})
        res = audit_temporal_completeness(df, expected_days=3)
        assert res["status"] == "partial_starvation"
        assert res["valid_days"] == 2
        assert res["completeness_pct"] == 66.67

    def test_completeness_fatal_starvation_raises(self) -> None:
        df = pd.DataFrame({"revenue": [0.0, 0.0, 0.0]})
        with pytest.raises(DataStarvationError, match="0 valid days with positive revenue"):
            audit_temporal_completeness(df, expected_days=3, raise_on_fatal=True)

    def test_completeness_fatal_starvation_silent(self) -> None:
        df = pd.DataFrame({"revenue": [0.0, 0.0]})
        res = audit_temporal_completeness(df, expected_days=2, raise_on_fatal=False)
        assert res["status"] == "fatal_starvation"


class TestDecoupledJsonContract:
    def test_valid_json_payload(self, valid_json_contract_payload: dict[str, str]) -> None:
        assert_decoupled_json_contract(valid_json_contract_payload)

    def test_missing_required_key(self) -> None:
        with pytest.raises(EvalAssertionError, match="Missing required key 'text'"):
            assert_decoupled_json_contract({"status": "success"})

    def test_unexpected_status(self) -> None:
        with pytest.raises(EvalAssertionError, match="Unexpected status 'unknown_status'"):
            assert_decoupled_json_contract({"status": "unknown_status", "text": "Hello"})

    def test_raw_traceback_leak_rejected(self) -> None:
        payload = {
            "status": "error",
            "text": "Failed: Traceback (most recent call last):\n  File 'app.py', line 12",
        }
        with pytest.raises(EvalAssertionError, match="Raw python traceback detected"):
            assert_decoupled_json_contract(payload)

    def test_unparsed_error_xml_tags_rejected(self) -> None:
        payload = {
            "status": "error",
            "text": "<ERROR>Connection timeout to database</ERROR>",
        }
        with pytest.raises(EvalAssertionError, match="Unparsed <ERROR> XML tags detected"):
            assert_decoupled_json_contract(payload)

    def test_forbidden_media_tags_rejected(self) -> None:
        payload = {
            "status": "success",
            "text": "Here is chart: <media>/path/to/chart.png</media>",
        }
        with pytest.raises(EvalAssertionError, match="Forbidden XML <media> tag detected"):
            assert_decoupled_json_contract(payload)


class TestUltraConciseDisclosure:
    def test_ultra_concise_mode_passes(self) -> None:
        text = "Resumen diario:\n* Ventas brutas: $10,000\n* Crecimiento DoD: +5%\n* Ordenes: 120"
        res = assert_ultra_concise_disclosure(text, user_prompt="dame el reporte de ayer")
        assert res["is_expanded_request"] is False
        assert res["bullet_count"] == 3

    def test_ultra_concise_mode_rejects_markdown_table(self) -> None:
        text = "Ventas:\n| Dia | Monto |\n| --- | --- |\n| Lun | $500 |"
        with pytest.raises(EvalAssertionError, match="Markdown table generated in default ultra-concise mode"):
            assert_ultra_concise_disclosure(text, user_prompt="reporte normal")

    def test_ultra_concise_mode_rejects_excessive_bullets(self) -> None:
        text = "* B1\n* B2\n* B3\n* B4\n* B5"
        with pytest.raises(EvalAssertionError, match="Output contains 5 bullets, exceeding"):
            assert_ultra_concise_disclosure(text, user_prompt="reporte normal", max_bullet_points=4)

    def test_expanded_mode_allows_table_and_bullets(self) -> None:
        text = "Desglose completo:\n| Producto | Total |\n| --- | --- |\n* Item 1\n* Item 2\n* Item 3\n* Item 4\n* Item 5"
        res = assert_ultra_concise_disclosure(text, user_prompt="dame el reporte detallado con desglose")
        assert res["is_expanded_request"] is True
        assert res["has_markdown_table"] is True


class TestPromptContextIntegrity:
    def test_prompt_integrity_passes(self) -> None:
        ctx = "=== REPORT ===\n<DATA>\ndate,rev\n2026-08-01,100\n</DATA>\nDATO EXACTO UPT: 2.0"
        assert_prompt_context_integrity(
            prompt_context=ctx,
            required_markers=["=== REPORT ===", "<DATA>", "DATO EXACTO UPT: 2.0"],
            forbidden_markers=["<SECRET_KEY>", "UNKNOWN_VARIABLE"],
        )

    def test_prompt_integrity_missing_marker(self) -> None:
        ctx = "=== REPORT ==="
        with pytest.raises(EvalAssertionError, match="Missing required marker '<DATA>'"):
            assert_prompt_context_integrity(ctx, required_markers=["<DATA>"])

    def test_prompt_integrity_forbidden_marker(self) -> None:
        ctx = "=== REPORT === <SECRET_KEY>"
        with pytest.raises(EvalAssertionError, match="Forbidden marker '<SECRET_KEY>'"):
            assert_prompt_context_integrity(
                ctx,
                required_markers=["=== REPORT ==="],
                forbidden_markers=["<SECRET_KEY>"],
            )


class TestPropertyBasedAssertions:
    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-", min_size=1, max_size=50))
    def test_prompt_integrity_fuzzing(self, marker: str) -> None:
        # Prompt containing marker should always succeed
        ctx = f"HEADER {marker} FOOTER"
        assert_prompt_context_integrity(ctx, required_markers=[marker])

    @given(st.text(min_size=0, max_size=100))
    def test_ultra_concise_never_crashes_on_arbitrary_string(self, text: str) -> None:
        try:
            assert_ultra_concise_disclosure(text, user_prompt="test prompt")
        except EvalAssertionError:
            pass  # Expected when violating limits, must not raise unexpected exceptions
