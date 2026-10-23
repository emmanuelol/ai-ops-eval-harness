"""ai-ops-eval-harness: SRE-hardened QA scenario runner, contract assertions, and telemetry decorators."""

__version__ = "0.1.0"

from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    FinancialAnomalyError,
    EvalAssertionError,
)
from ai_ops_eval_harness.serialization import make_serializable
from ai_ops_eval_harness.auditor import (
    assert_no_coercion_starvation,
    reconcile_channel_ledgers,
    validate_financial_bounds,
    validate_cash_ratio_variance,
    validate_promo_threshold,
    safe_atomic_parquet_export,
    FinancialAuditor,
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
    ScenarioResult,
    ScenarioHarness,
)
from ai_ops_eval_harness.telemetry import track_llm_telemetry
from ai_ops_eval_harness.cli import main

__all__ = [
    "__version__",
    "main",
    "DataStarvationError",
    "FinancialAnomalyError",
    "EvalAssertionError",
    "make_serializable",
    "assert_no_coercion_starvation",
    "reconcile_channel_ledgers",
    "validate_financial_bounds",
    "validate_cash_ratio_variance",
    "validate_promo_threshold",
    "safe_atomic_parquet_export",
    "FinancialAuditor",
    "audit_temporal_completeness",
    "assert_decoupled_json_contract",
    "assert_ultra_concise_disclosure",
    "assert_prompt_context_integrity",
    "BlastShield",
    "QAScenario",
    "ScenarioResult",
    "ScenarioHarness",
    "track_llm_telemetry",
]
