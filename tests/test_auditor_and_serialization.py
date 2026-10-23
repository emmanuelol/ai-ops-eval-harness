"""Unit tests for core financial auditor primitives and recursive serialization."""

import os
import math
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, date

from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    FinancialAnomalyError,
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


class TestDataStarvation:
    def test_starvation_raises_on_zero_yield(self):
        with pytest.raises(DataStarvationError, match="100% data starvation detected"):
            assert_no_coercion_starvation(initial_count=100, final_count=0, context="temporal_coercion")

    def test_starvation_passes_when_all_records_preserved(self):
        assert_no_coercion_starvation(initial_count=50, final_count=50)

    def test_starvation_tolerance_exceeded(self):
        with pytest.raises(DataStarvationError, match="Dropped 10 of 100"):
            assert_no_coercion_starvation(initial_count=100, final_count=90, tolerance_pct=5.0)


class TestChannelReconciliation:
    def test_reconciliation_tolerates_floating_point_fuzziness(self):
        # 10.10 vs 10.0999999999999 precision variance
        res = reconcile_channel_ledgers(
            primary_gross=100.0,
            secondary_gross=20.0,
            secondary_net=10.0999999999999,
            secondary_tax=3.2,
            secondary_fee=6.7,
            abs_tol=0.01,
        )
        assert math.isclose(res["consolidated_gross"], 120.0, abs_tol=0.01)
        assert math.isclose(res["calculated_secondary_net"], 10.10, abs_tol=0.01)
        assert res["variance_net"] <= 0.01

    def test_reconciliation_detects_gross_divergence(self):
        with pytest.raises(FinancialAnomalyError, match="Gross Variance detected"):
            reconcile_channel_ledgers(
                primary_gross=100.0,
                secondary_gross=50.0,
                secondary_net=40.0,
                secondary_tax=5.0,
                secondary_fee=5.0,
                reported_consolidated_gross=160.0,  # Reported 160 vs actual 100 + 50 = 150
                abs_tol=0.01,
            )

    def test_reconciliation_detects_net_equation_divergence(self):
        with pytest.raises(FinancialAnomalyError, match="Net Equation Variance detected"):
            reconcile_channel_ledgers(
                primary_gross=100.0,
                secondary_gross=20.0,
                secondary_net=15.0,  # Reported 15.0, but 20 - 3 - 6 = 11.0
                secondary_tax=3.0,
                secondary_fee=6.0,
            )

    def test_reconciliation_tracks_hidden_platform_variance(self):
        res = reconcile_channel_ledgers(
            primary_gross=100.0,
            secondary_gross=20.0,
            secondary_net=11.0,
            secondary_tax=3.0,
            secondary_fee=6.0,
            platform_estimate=13.50,
        )
        assert res["hidden_variance"] == 2.50


class TestStatisticalBounds:
    def test_bounds_trips_on_z_score_spike(self):
        # 3 normal historical days, 1 massive spike on same day of week
        df = pd.DataFrame([
            {"date": "2026-07-01", "gross_amount": 1000.0},
            {"date": "2026-07-08", "gross_amount": 1020.0},
            {"date": "2026-07-15", "gross_amount": 1010.0},
            {"date": "2026-07-22", "gross_amount": 10000.0},  # 10x spike
        ])
        with pytest.raises(FinancialAnomalyError, match="Statistical circuit breaker tripped"):
            validate_financial_bounds(df, metric_col="gross_amount", enable_t1_grace=False)

    def test_bounds_trips_on_90_percent_drop(self):
        df = pd.DataFrame([
            {"date": "2026-07-01", "gross_amount": 1000.0},
            {"date": "2026-07-08", "gross_amount": 1050.0},
            {"date": "2026-07-15", "gross_amount": 1020.0},
            {"date": "2026-07-22", "gross_amount": 50.0},  # 95% drop
        ])
        with pytest.raises(FinancialAnomalyError, match="Statistical circuit breaker tripped"):
            validate_financial_bounds(df, metric_col="gross_amount", enable_t1_grace=False)

    def test_bounds_skips_when_t1_grace_period_active(self):
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
        df = pd.DataFrame([
            {"date": "2026-07-01", "gross_amount": 1000.0},
            {"date": "2026-07-08", "gross_amount": 1050.0},
            {"date": "2026-07-15", "gross_amount": 1020.0},
            {"date": today_str, "gross_amount": 10.0},  # Current operating day
        ])
        res = validate_financial_bounds(df, metric_col="gross_amount", enable_t1_grace=True)
        assert res["status"] == "grace_period_skipped"


class TestPaymentAndPromoGuards:
    def test_cash_ratio_spike_detection(self):
        history = [
            {"date": f"2026-06-{i:02d}", "total_cash": 10.0, "total_digital": 90.0}
            for i in range(1, 20)
        ]
        history.append({"date": "2026-06-25", "total_cash": 60.0, "total_digital": 40.0})  # 60% cash vs ~10% avg
        df = pd.DataFrame(history)

        with pytest.raises(FinancialAnomalyError, match="Cash ratio spike anomaly detected"):
            validate_cash_ratio_variance(df, z_threshold=2.0)

    def test_promo_cannibalization_guardrail(self):
        df = pd.DataFrame([
            {"date": "2026-08-01", "promo_share_pct": 5.0},
            {"date": "2026-08-02", "promo_share_pct": 12.5},  # > 8.0% threshold
        ])
        with pytest.raises(FinancialAnomalyError, match="Promo cannibalization guardrail tripped"):
            validate_promo_threshold(df, max_threshold=8.0)


class TestParquetExportAndCoordinator:
    def test_safe_parquet_export_handles_mixed_types(self, tmp_path):
        target = str(tmp_path / "financial_cache.parquet")
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-08-01", "2026-08-02"]),
            "gross": [1000.5, 2000.75],
            "metadata_obj": [{"tag": 1}, {"tag": 2}],  # Object column
        })

        ok = safe_atomic_parquet_export(df, target)
        assert ok is True
        assert os.path.exists(target)

        # Verify reload
        df_loaded = pd.read_parquet(target)
        assert len(df_loaded) == 2
        assert isinstance(df_loaded["metadata_obj"].iloc[0], str)

    def test_safe_parquet_export_fails_open_on_io_error(self, monkeypatch):
        def _mock_to_parquet(*args, **kwargs):
            raise OSError("Read-only filesystem")

        monkeypatch.setattr(pd.DataFrame, "to_parquet", _mock_to_parquet)
        df = pd.DataFrame({"a": [1, 2]})
        ok = safe_atomic_parquet_export(df, "/dev/null/impossible_path.parquet")
        assert ok is False

    def test_financial_auditor_coordinator(self, tmp_path):
        auditor = FinancialAuditor()
        auditor.check_starvation(10, 10)
        reconciled = auditor.reconcile(100.0, 50.0, 40.0, 5.0, 5.0)
        assert reconciled["consolidated_gross"] == 150.0

        target = str(tmp_path / "coordinator_cache.parquet")
        ok = auditor.export_cache(pd.DataFrame({"x": [10]}), target)
        assert ok is True


class TestSerialization:
    def test_make_serializable_handles_all_structures(self):
        payload = {
            "int_val": np.int64(42),
            "float_val": np.float64(3.1415),
            "nan_val": np.float64(np.nan),
            "nat_val": pd.NaT,
            "none_val": None,
            "timestamp": pd.Timestamp("2026-08-20 12:00:00"),
            "date_obj": date(2026, 8, 20),
            "datetime_obj": datetime(2026, 8, 20, 15, 30),
            "array_val": np.array([1, 2, 3]),
            "nested_list": [{"inner_ts": pd.Timestamp("2026-08-21")}],
            "set_val": {np.int32(1), np.int32(2)},
        }

        clean = make_serializable(payload)
        assert clean["int_val"] == 42
        assert clean["float_val"] == 3.1415
        assert clean["nan_val"] is None
        assert clean["nat_val"] is None
        assert clean["none_val"] is None
        assert clean["timestamp"] == "2026-08-20T12:00:00"
        assert clean["date_obj"] == "2026-08-20"
        assert clean["datetime_obj"] == "2026-08-20T15:30:00"
        assert clean["array_val"] == [1, 2, 3]
        assert clean["nested_list"][0]["inner_ts"] == "2026-08-21T00:00:00"
        assert set(clean["set_val"]) == {1, 2}
