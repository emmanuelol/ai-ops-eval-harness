#!/usr/bin/env python3
"""Example 02: Financial Circuit Breakers, Multi-Channel Reconciliation & Atomic Cache.

Demonstrates:
1. Guarding against ingestion data starvation.
2. Reconciling primary and secondary sales ledgers with floating-point tolerance.
3. Detecting Day-of-Week anomalies with statistical Z-scores.
4. Exporting sanitized financial metrics to Parquet cache.
"""

from __future__ import annotations

import tempfile
import pandas as pd

from ai_ops_eval_harness import (
    FinancialAnomalyError,
    assert_no_coercion_starvation,
    reconcile_channel_ledgers,
    safe_atomic_parquet_export,
    validate_financial_bounds,
)


def run_financial_pipeline() -> None:
    print("--- 1. Data Ingestion Starvation Check ---")
    raw_ingestion_count = 1500
    parsed_record_count = 1495

    # Enforce maximum 1.0% drop tolerance
    assert_no_coercion_starvation(
        initial_count=raw_ingestion_count,
        final_count=parsed_record_count,
        tolerance_pct=1.0,
        context="pos_ingestion",
    )
    print(f"✅ Ingestion passed: preserved {parsed_record_count}/{raw_ingestion_count} records.")

    print("\n--- 2. Multi-Channel Ledger Reconciliation ---")
    reconciliation = reconcile_channel_ledgers(
        primary_gross=12500.00,
        secondary_gross=3200.00,
        secondary_net=2624.00,
        secondary_tax=416.00,
        secondary_fee=160.00,
        platform_estimate=2624.00,
        abs_tol=0.01,
    )
    print(f"✅ Consolidated Gross : ${reconciliation['consolidated_gross']:.2f}")
    print(f"   Secondary Net      : ${reconciliation['secondary_net']:.2f}")
    print(f"   Net Variance       : ${reconciliation['variance_net']:.4f}")

    print("\n--- 3. Statistical Bound Evaluation (Day-of-Week Z-Score) ---")
    # Simulate normal history
    history = [
        {"date": "2026-09-02", "gross_amount": 5000.0},
        {"date": "2026-09-09", "gross_amount": 5100.0},
        {"date": "2026-09-16", "gross_amount": 4950.0},
        {"date": "2026-09-23", "gross_amount": 5050.0},
    ]
    df_normal = pd.DataFrame(history)
    normal_res = validate_financial_bounds(df_normal, metric_col="gross_amount", enable_t1_grace=False)
    print(f"✅ Baseline bounds check: status={normal_res['status']}")

    # Simulate anomalous day (8x spike)
    df_spike = pd.concat([
        df_normal,
        pd.DataFrame([{"date": "2026-09-30", "gross_amount": 40000.0}]),
    ], ignore_index=True)

    try:
        validate_financial_bounds(df_spike, metric_col="gross_amount", enable_t1_grace=False)
        print("❌ Circuit breaker failed to trip on 8x spike.")
    except FinancialAnomalyError as e:
        print(f"✅ Circuit breaker correctly caught anomaly:\n   {e}")

    print("\n--- 4. Safe Atomic Parquet Cache Export ---")
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        cache_path = tmp.name
        ok = safe_atomic_parquet_export(df_normal, cache_path)
        print(f"✅ Atomic cache write succeeded: {ok} -> {cache_path}")


if __name__ == "__main__":
    run_financial_pipeline()
