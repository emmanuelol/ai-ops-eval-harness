"""Unit tests for @track_llm_telemetry decorator, backoff, and alerts."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
import pytest

from ai_ops_eval_harness.telemetry import track_llm_telemetry


class TestTelemetryDecorator:
    def test_telemetry_successful_call(self) -> None:
        mock_response = MagicMock()
        mock_response.usage_metadata.total_token_count = 150

        @track_llm_telemetry(retries=2)
        def call_llm(model: str = "test_model") -> Any:
            return mock_response

        res = call_llm(model="test_model")
        assert res is mock_response

    def test_telemetry_retry_on_429(self) -> None:
        attempts = 0

        @track_llm_telemetry(retries=3, base_backoff=0.01)
        def call_flaky_llm() -> Any:
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

    def test_telemetry_exhaustion_triggers_alert(self) -> None:
        alert_payload: dict[str, Any] | None = None

        def record_alert(payload: dict[str, Any]) -> None:
            nonlocal alert_payload
            alert_payload = payload

        @track_llm_telemetry(retries=2, base_backoff=0.01, on_alert=record_alert)
        def call_failing_llm() -> None:
            raise ConnectionError("Server unavailable")

        with pytest.raises(ConnectionError):
            call_failing_llm()

        assert alert_payload is not None
        assert alert_payload["event"] == "LLM_TELEMETRY_EXHAUSTION"
        assert alert_payload["attempts"] == 2
