"""QA scenario runner and blast shield mocking harness for chaotic or offline evaluation."""

import time
import contextlib
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass, field

from ai_ops_eval_harness.exceptions import EvalAssertionError


@dataclass
class ScenarioResult:
    scenario_name: str
    passed: bool
    duration_seconds: float
    output: Any = None
    error: Optional[str] = None


@dataclass
class QAScenario:
    name: str
    description: str
    runner: Callable[[], Any]
    assertions: List[Callable[[Any], None]] = field(default_factory=list)


class BlastShield(contextlib.ContextDecorator):
    """Context manager / decorator to intercept external network dispatches and simulate in-memory delivery."""

    def __init__(self, simulate_success: bool = True, latency_seconds: float = 0.0):
        self.simulate_success = simulate_success
        self.latency_seconds = latency_seconds
        self.intercepted_calls: List[Dict[str, Any]] = []

    def __enter__(self):
        self.intercepted_calls.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def record_dispatch(self, destination: str, payload: Any) -> bool:
        if self.latency_seconds > 0:
            time.sleep(self.latency_seconds)
        self.intercepted_calls.append({"destination": destination, "payload": payload})
        return self.simulate_success


class ScenarioHarness:
    """Orchestrates declarative QA scenario suites with deterministic metrics."""

    def __init__(self, name: str = "default_harness"):
        self.name = name
        self.scenarios: List[QAScenario] = []

    def register(self, scenario: QAScenario) -> None:
        self.scenarios.append(scenario)

    def run_all(self) -> Dict[str, Any]:
        results: List[ScenarioResult] = []
        total_start = time.perf_counter()

        for sc in self.scenarios:
            sc_start = time.perf_counter()
            try:
                out = sc.runner()
                for assertion in sc.assertions:
                    assertion(out)
                duration = time.perf_counter() - sc_start
                results.append(ScenarioResult(scenario_name=sc.name, passed=True, duration_seconds=duration, output=out))
            except Exception as e:
                duration = time.perf_counter() - sc_start
                results.append(
                    ScenarioResult(
                        scenario_name=sc.name,
                        passed=False,
                        duration_seconds=duration,
                        error=f"{type(e).__name__}: {str(e)}",
                    )
                )

        total_duration = time.perf_counter() - total_start
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        return {
            "harness": self.name,
            "total_scenarios": len(results),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate_pct": round((passed_count / len(results)) * 100.0, 2) if results else 100.0,
            "duration_seconds": round(total_duration, 4),
            "results": [
                {
                    "name": r.scenario_name,
                    "passed": r.passed,
                    "duration_seconds": round(r.duration_seconds, 4),
                    "error": r.error,
                }
                for r in results
            ],
        }
