"""Shared test fixtures for ai-ops-eval-harness test suite."""

from __future__ import annotations

import pandas as pd
import pytest

from ai_ops_eval_harness.scenarios import ScenarioHarness


@pytest.fixture
def sample_timeseries_df() -> pd.DataFrame:
    """Provide standard 3-day revenue dataset."""
    return pd.DataFrame({"revenue": [100.0, 200.0, 300.0]})


@pytest.fixture
def sample_dow_spike_df() -> pd.DataFrame:
    """Provide historical weekly data with 10x spike on the same day of week."""
    return pd.DataFrame([
        {"date": "2026-07-01", "gross_amount": 1000.0},
        {"date": "2026-07-08", "gross_amount": 1020.0},
        {"date": "2026-07-15", "gross_amount": 1010.0},
        {"date": "2026-07-22", "gross_amount": 10000.0},
    ])


@pytest.fixture
def sample_cash_ratio_df() -> pd.DataFrame:
    """Provide cash payment history with an anomalous spike on final day."""
    history = [
        {"date": f"2026-06-{i:02d}", "total_cash": 10.0, "total_digital": 90.0}
        for i in range(1, 20)
    ]
    history.append({"date": "2026-06-25", "total_cash": 60.0, "total_digital": 40.0})
    return pd.DataFrame(history)


@pytest.fixture
def valid_json_contract_payload() -> dict[str, str]:
    """Provide valid decoupled JSON contract payload."""
    return {
        "status": "success",
        "text": "Report completed successfully. ![Chart](https://storage.local/chart.png)",
        "chart_path": "/storage/chart.png",
    }


@pytest.fixture
def harness() -> ScenarioHarness:
    """Provide fresh ScenarioHarness instance."""
    return ScenarioHarness(name="test_fixture_harness")
