"""Unit tests for ScenarioHarness, BlastShield, and declarative QAScenario runner."""

from __future__ import annotations

import pandas as pd

from ai_ops_eval_harness.assertions import assert_decoupled_json_contract, audit_temporal_completeness
from ai_ops_eval_harness.scenarios import (
    BlastShield,
    QAScenario,
    ScenarioHarness,
)


class TestBlastShield:
    def test_blast_shield_intercepts_calls(self) -> None:
        shield = BlastShield(simulate_success=True)
        with shield:
            ok = shield.record_dispatch("+1234567890", {"message": "Hello"})
            assert ok is True

        assert len(shield.intercepted_calls) == 1
        assert shield.intercepted_calls[0]["destination"] == "+1234567890"

    def test_blast_shield_simulate_failure(self) -> None:
        shield = BlastShield(simulate_success=False)
        with shield:
            ok = shield.record_dispatch("+1234567890", {"message": "Fail"})
            assert ok is False


class TestScenarioHarness:
    def test_scenario_harness_suite(self, harness: ScenarioHarness) -> None:
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
        assert report["results"][0]["passed"] is True
        assert report["results"][1]["passed"] is False
