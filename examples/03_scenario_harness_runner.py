#!/usr/bin/env python3
"""Example 03: End-to-End ScenarioHarness Evaluation Suite.

Demonstrates:
1. Creating and configuring a ScenarioHarness.
2. Registering custom declarative QAScenario cases with assertion chains.
3. Executing the suite and generating structured JSON and tabular evaluation metrics.
"""

from __future__ import annotations

import json
import pandas as pd

from ai_ops_eval_harness import (
    BlastShield,
    QAScenario,
    ScenarioHarness,
    assert_decoupled_json_contract,
    audit_temporal_completeness,
)


def run_eval_suite() -> None:
    print("=== Initializing AI-Ops Scenario Harness ===")
    harness = ScenarioHarness(name="production_eval_suite")

    # Scenario 1: Clean report generation with BlastShield
    def scenario_clean_dispatch() -> dict[str, str]:
        with BlastShield(simulate_success=True) as shield:
            shield.record_dispatch("+1-555-0100", {"alert": "Report Ready"})
            return {"status": "success", "text": "* Pipeline ran cleanly in 12ms"}

    harness.register(
        QAScenario(
            name="clean_dispatch_scenario",
            description="Verifies outward alert dispatch interception and JSON output contract",
            runner=scenario_clean_dispatch,
            assertions=[assert_decoupled_json_contract],
        )
    )

    # Scenario 2: Temporal completeness validation
    def scenario_timeseries_completeness() -> dict[str, object]:
        df = pd.DataFrame({"revenue": [1200.0, 1400.0, 1100.0, 1500.0]})
        return audit_temporal_completeness(df, expected_days=4)

    def assert_complete_data(result: object) -> None:
        assert isinstance(result, dict)
        assert result.get("status") == "complete"
        assert result.get("completeness_pct") == 100.0

    harness.register(
        QAScenario(
            name="temporal_completeness_scenario",
            description="Verifies dataset has no dropped dates across 4-day window",
            runner=scenario_timeseries_completeness,
            assertions=[assert_complete_data],
        )
    )

    # Execute all scenarios
    print("\nExecuting evaluation scenarios...")
    report = harness.run_all()

    print("\n--- Evaluation Summary Report ---")
    print(f"Suite Name       : {report['harness']}")
    print(f"Total Scenarios  : {report['total_scenarios']}")
    print(f"Passed           : {report['passed']}")
    print(f"Failed           : {report['failed']}")
    print(f"Success Rate     : {report['success_rate_pct']:.1f}%")
    print(f"Total Duration   : {report['duration_seconds']:.4f}s")

    print("\n--- Detailed Results (JSON) ---")
    print(json.dumps(report["results"], indent=2))


if __name__ == "__main__":
    run_eval_suite()
