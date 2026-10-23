# ai-ops-eval-harness 🧪

[![CI Pipeline](https://github.com/emmanuelol/ai-ops-eval-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/emmanuelol/ai-ops-eval-harness/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

SRE-hardened evaluation harness, deterministic QA scenario runner, LLM prompt/output contract assertions, and statistical circuit breakers for automated financial and operational pipelines.

---

## 🏛️ Architecture & Evaluation Flow

```mermaid
flowchart TD
    subgraph INGESTION["Data Ingestion & Normalization"]
        A["External Time-Series Data"] --> B["assert_no_coercion_starvation"]
        B --> C["audit_temporal_completeness"]
    end

    subgraph AUDITING["Statistical Circuit Breakers"]
        C --> D["reconcile_channel_ledgers (IEEE 754 float tolerance)"]
        D --> E["validate_financial_bounds (DoW Z-Score & Drop Breaker)"]
        E --> F["validate_cash_ratio_variance & validate_promo_threshold"]
    end

    subgraph ORCHESTRATION["LLM Contracts & Telemetry"]
        F --> G["assert_prompt_context_integrity"]
        G --> H["@track_llm_telemetry (Backoff on 429)"]
        H --> I["LLM Inference / Generation"]
        I --> J["assert_decoupled_json_contract & assert_ultra_concise_disclosure"]
    end

    subgraph STORAGE["Safe Atomic Cache"]
        F --> K["safe_atomic_parquet_export (PyArrow-safe schema swap)"]
    end
```

---

## 🛡️ SRE Circuit Breaker Matrix

| Mechanism | Trigger Condition | Default Action | Error / Metric |
|---|---|---|---|
| **Zero-Tolerance Starvation** | Dropped 100% records or drop > threshold | Immediate fail-closed exception | `DataStarvationError` |
| **Channel Ledger Reconciliation** | Reported Net != Gross - Tax - Fees | Detect hidden variance, fail if > abs_tol | `FinancialAnomalyError` |
| **Contextual DoW Anomaly** | \|Z-Score\| > 3.0 or drop > 90% | Anomaly quarantine halt (with T-1 grace period) | `FinancialAnomalyError` |
| **Cash Ratio Spike** | Z-Score > 2.0 vs 30-day baseline | Flags payment fraud/divergence anomaly | `FinancialAnomalyError` |
| **Promo Cannibalization** | Promo Share > 8.0% | Anomaly trip on marketing margin leak | `FinancialAnomalyError` |
| **PyArrow Cache Hardening** | Object columns in Parquet | Automatic string coercion & atomic temp-swap | Fail-open on `OSError` |
| **LLM Rate-Limit Backoff** | HTTP 429 or Resource Exhausted | Exponential backoff (2s, 4s, 8s) + alert webhook | `track_llm_telemetry` |
| **Progressive Disclosure UX** | Markdown tables without keywords | Rejects verbose wall-of-text | `EvalAssertionError` |

---

## 🚀 Quickstart

### 1. Installation
```bash
pip install ai-ops-eval-harness
```

### 2. Reconciliation & Starvation Check
```python
from ai_ops_eval_harness import (
    assert_no_coercion_starvation,
    reconcile_channel_ledgers,
    FinancialAnomalyError,
)

# Guard against silent coercion drops
assert_no_coercion_starvation(initial_count=100, final_count=100)

# Reconcile multi-channel ledgers with float precision tolerance
reconciliation = reconcile_channel_ledgers(
    primary_gross=12000.50,
    secondary_gross=3500.00,
    secondary_net=2800.00,
    secondary_tax=400.00,
    secondary_fee=300.00,
    platform_estimate=2800.00,
    abs_tol=0.01,
)
print(f"Consolidated Gross: ${reconciliation['consolidated_gross']}")
```

### 3. Declarative Scenario Runner
```python
from ai_ops_eval_harness import (
    ScenarioHarness,
    QAScenario,
    BlastShield,
    assert_decoupled_json_contract,
)

harness = ScenarioHarness(name="daily_eval")

def sample_pipeline():
    with BlastShield(simulate_success=True) as shield:
        # Simulate dispatching report
        shield.record_dispatch("+1234567890", {"message": "All systems operational"})
        return {"status": "success", "text": "Daily summary"}

harness.register(
    QAScenario(
        name="daily_health_check",
        description="Verifies pipeline produces decoupled JSON",
        runner=sample_pipeline,
        assertions=[assert_decoupled_json_contract],
    )
)

report = harness.run_all()
print(f"Passed: {report['passed']}/{report['total_scenarios']}")
```

---

## 🧪 Verification & Security Audit

This repository enforces 100% containerized execution and Trivy vulnerability auditing:

```bash
# Build Docker image
make build

# Run unit and integration tests inside container
make test

# Scan image for vulnerabilities and prohibited secrets
make audit
```
