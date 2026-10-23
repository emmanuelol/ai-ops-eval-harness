"""ai-ops-eval-harness: SRE-hardened QA scenario runner and financial pipeline circuit breakers."""

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

__all__ = [
    "__version__",
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
]
