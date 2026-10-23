"""Financial auditing, mathematical reconciliation, and pipeline anomaly circuit breakers."""

import os
import math
import uuid
import logging
from typing import Optional, Dict, Any
import pandas as pd
import pytz

from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    FinancialAnomalyError,
)

logger = logging.getLogger(__name__)


def assert_no_coercion_starvation(
    initial_count: int,
    final_count: int,
    tolerance_pct: float = 0.0,
    context: str = "pipeline",
) -> None:
    """Zero-tolerance circuit breaker verifying that parsing or temporal coercion did not drop records unexpectedly."""
    if initial_count <= 0:
        return

    if final_count == 0:
        raise DataStarvationError(
            f"FATAL: [{context}] 100% data starvation detected. Initial records: {initial_count}, Final: 0"
        )

    dropped = initial_count - final_count
    dropped_pct = (dropped / initial_count) * 100.0

    if dropped_pct > tolerance_pct:
        raise DataStarvationError(
            f"FATAL: [{context}] Dropped {dropped} of {initial_count} records ({dropped_pct:.2f}% > threshold {tolerance_pct:.2f}%)"
        )


def reconcile_channel_ledgers(
    primary_gross: float,
    secondary_gross: float,
    secondary_net: float,
    secondary_tax: float,
    secondary_fee: float,
    reported_consolidated_gross: Optional[float] = None,
    platform_estimate: Optional[float] = None,
    abs_tol: float = 0.01,
) -> Dict[str, Any]:
    """Reconciles consolidated gross and channel net equations across distributed financial ledgers.
    
    Enforces Net = Gross - Tax - Channel_Fees with IEEE 754 floating point tolerance.
    Identifies hidden variances between external platform estimates and audited net.
    """
    pos_gross = round(float(primary_gross), 2)
    sec_gross = round(float(secondary_gross), 2)
    sec_net = round(float(secondary_net), 2)
    sec_tax = round(float(secondary_tax), 2)
    sec_fee = round(float(secondary_fee), 2)

    calculated_gross = round(pos_gross + sec_gross, 2)
    consolidated_gross = round(float(reported_consolidated_gross), 2) if reported_consolidated_gross is not None else calculated_gross
    variance_gross = round(abs(consolidated_gross - calculated_gross), 2)

    if not math.isclose(consolidated_gross, calculated_gross, abs_tol=abs_tol) and variance_gross >= abs_tol:
        raise FinancialAnomalyError(
            f"AUDIT_FAILED: Gross Variance detected across channels: {variance_gross} (Expected: {consolidated_gross}, Calculated: {calculated_gross})"
        )

    calculated_sec_net = round(sec_gross - sec_tax - sec_fee, 2)
    variance_net = round(abs(sec_net - calculated_sec_net), 2)

    if not math.isclose(sec_net, calculated_sec_net, abs_tol=abs_tol) and variance_net >= abs_tol:
        raise FinancialAnomalyError(
            f"AUDIT_FAILED: Net Equation Variance detected. Reported Net: {sec_net}, Calculated: {calculated_sec_net}, Variance: {variance_net}"
        )

    hidden_variance = 0.0
    if platform_estimate is not None:
        plat_est = round(float(platform_estimate), 2)
        hidden_variance = round(abs(plat_est - calculated_sec_net), 2)
        if hidden_variance >= abs_tol:
            logger.warning(
                f"[AUDIT] Platform Estimate: ${plat_est} | Audited Real Net: ${calculated_sec_net} | Hidden Variance: ${hidden_variance}"
            )

    return {
        "consolidated_gross": consolidated_gross,
        "primary_gross": pos_gross,
        "secondary_gross": sec_gross,
        "secondary_net": sec_net,
        "calculated_secondary_net": calculated_sec_net,
        "variance_gross": variance_gross,
        "variance_net": variance_net,
        "hidden_variance": hidden_variance,
    }


def validate_financial_bounds(
    df: pd.DataFrame,
    metric_col: str = "gross_amount",
    date_col: str = "date",
    z_threshold: float = 3.0,
    drop_threshold: float = -0.90,
    timezone_str: str = "America/Mexico_City",
    enable_t1_grace: bool = True,
) -> Dict[str, Any]:
    """Contextual Day-of-Week (DoW) statistical circuit breaker for baseline metrics."""
    if df is None or df.empty or metric_col not in df.columns or date_col not in df.columns:
        return {"status": "insufficient_data"}

    if len(df) < 3:
        return {"status": "insufficient_history"}

    df_clean = df.copy()
    df_clean["_date_dt"] = pd.to_datetime(df_clean[date_col], errors="coerce").dt.normalize()
    df_clean = df_clean.dropna(subset=["_date_dt"]).sort_values("_date_dt", ascending=True)

    if len(df_clean) < 3:
        return {"status": "insufficient_valid_dates"}

    recent = df_clean.iloc[-1]
    recent_date = recent["_date_dt"]

    # Grace Period for current operating day (T-1 offline synchronization)
    try:
        tz = pytz.timezone(timezone_str)
    except Exception:
        tz = pytz.timezone("America/Mexico_City")

    today = pd.Timestamp.now(tz=tz).tz_localize(None).normalize()
    if enable_t1_grace and recent_date >= today:
        logger.info(f"Skipping statistical anomaly check for real-time operating date {recent_date.date()}")
        return {"status": "grace_period_skipped", "operating_date": str(recent_date.date())}

    try:
        recent_dow = recent_date.day_of_week
    except (AttributeError, KeyError):
        recent_dow = getattr(recent_date, "dayofweek", 0)

    historical = df_clean.iloc[:-1]
    dow_series = historical["_date_dt"].dt.day_of_week if hasattr(historical["_date_dt"].dt, "day_of_week") else historical["_date_dt"].dt.dayofweek
    historical_dow = historical[dow_series == recent_dow]

    if len(historical_dow) < 2:
        historical_dow = historical

    hist_mean = float(historical_dow[metric_col].mean())
    hist_std = float(historical_dow[metric_col].std())

    if pd.isna(hist_std) or hist_std <= 0:
        hist_std = hist_mean * 0.05 if hist_mean > 0 else 1.0

    recent_val = float(recent[metric_col])
    z_score = (recent_val - hist_mean) / hist_std
    percent_change = ((recent_val - hist_mean) / hist_mean) if hist_mean > 0 else 0.0

    if abs(z_score) > z_threshold or percent_change < drop_threshold:
        raise FinancialAnomalyError(
            f"Statistical circuit breaker tripped. Date {recent_date.date()} showed {recent_val} "
            f"vs expected mean {hist_mean:.2f} (Z-Score: {z_score:.2f}, Change: {percent_change*100:.2f}%)"
        )

    return {
        "status": "verified",
        "recent_date": str(recent_date.date()),
        "recent_val": recent_val,
        "historical_mean": hist_mean,
        "historical_std": hist_std,
        "z_score": z_score,
        "percent_change": percent_change,
    }


def validate_cash_ratio_variance(
    df: pd.DataFrame,
    cash_col: str = "total_cash",
    digital_col: str = "total_digital",
    date_col: str = "date",
    z_threshold: float = 2.0,
    window: int = 30,
) -> Dict[str, Any]:
    """Tracks payment method ratios and trips anomaly breaker on unexpected cash ratio spikes."""
    if df is None or df.empty or cash_col not in df.columns or digital_col not in df.columns:
        return {"status": "skipped"}

    df_clean = df.copy()
    if date_col in df_clean.columns:
        df_clean["_date_dt"] = pd.to_datetime(df_clean[date_col], errors="coerce").dt.normalize()
        df_clean = df_clean.sort_values("_date_dt", ascending=True)

    if len(df_clean) < 3:
        return {"status": "insufficient_history"}

    cash_series = pd.to_numeric(df_clean[cash_col], errors="coerce").fillna(0.0)
    digital_series = pd.to_numeric(df_clean[digital_col], errors="coerce").fillna(0.0)
    total_payments = (cash_series + digital_series).replace(0, 1.0)

    df_clean["_cash_ratio"] = cash_series / total_payments
    recent_def = df_clean.iloc[-1]
    historical_def = df_clean.iloc[:-1].tail(window)

    if historical_def.empty:
        return {"status": "insufficient_history"}

    hist_mean = float(historical_def["_cash_ratio"].mean())
    hist_std = float(historical_def["_cash_ratio"].std())
    if pd.isna(hist_std) or hist_std <= 0:
        hist_std = hist_mean * 0.05 + 0.01

    recent_cash_ratio = float(recent_def["_cash_ratio"])
    cash_z_score = (recent_cash_ratio - hist_mean) / hist_std

    if cash_z_score > z_threshold:
        raise FinancialAnomalyError(
            f"Cash ratio spike anomaly detected. Current: {recent_cash_ratio*100:.2f}% "
            f"vs historical mean {hist_mean*100:.2f}% (Z-Score: {cash_z_score:.2f} > {z_threshold})"
        )

    return {
        "status": "verified",
        "recent_cash_ratio": recent_cash_ratio,
        "historical_mean": hist_mean,
        "cash_z_score": cash_z_score,
    }


def validate_promo_threshold(
    df: pd.DataFrame,
    promo_col: str = "promo_share_pct",
    date_col: str = "date",
    max_threshold: float = 8.0,
) -> float:
    """Enforces promotional discount cannibalization ceiling guardrail."""
    if df is None or df.empty or promo_col not in df.columns:
        return 0.0

    df_clean = df.copy()
    if date_col in df_clean.columns:
        df_clean["_date_dt"] = pd.to_datetime(df_clean[date_col], errors="coerce").dt.normalize()
        df_clean = df_clean.sort_values("_date_dt", ascending=True)

    recent = df_clean.iloc[-1]
    promo_share = float(pd.to_numeric(recent.get(promo_col, 0.0), errors="coerce") or 0.0)

    if promo_share > max_threshold:
        raise FinancialAnomalyError(
            f"Promo cannibalization guardrail tripped: {promo_share:.2f}% exceeds threshold of {max_threshold:.2f}%"
        )

    return promo_share


def safe_atomic_parquet_export(df: pd.DataFrame, target_path: str) -> bool:
    """Safely serializes DataFrame to Parquet using PyArrow schema hardening and atomic swap.
    
    All object columns are explicitly coerced to string to prevent PyArrow mixed-type crashes.
    I/O errors fail open to ensure audit serialization never halts execution.
    """
    if df is None or df.empty:
        return False

    try:
        target_dir = os.path.dirname(os.path.abspath(target_path))
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        df_safe = df.copy()
        for col in df_safe.columns:
            if df_safe[col].dtype == "object":
                df_safe[col] = df_safe[col].astype(str)

        tmp_path = f"{target_path}.tmp_{uuid.uuid4().hex}"
        df_safe.to_parquet(tmp_path)
        os.replace(tmp_path, target_path)
        return True
    except Exception as e:
        logger.warning(f"Parquet export bypassed for {target_path}. Reason: {e}")
        return False


class FinancialAuditor:
    """SRE-hardened audit coordinator for analytical pipelines."""

    def __init__(
        self,
        timezone_str: str = "America/Mexico_City",
        z_threshold: float = 3.0,
        drop_threshold: float = -0.90,
        max_promo_share: float = 8.0,
    ):
        self.timezone_str = timezone_str
        self.z_threshold = z_threshold
        self.drop_threshold = drop_threshold
        self.max_promo_share = max_promo_share

    def check_starvation(self, initial: int, final: int, context: str = "") -> None:
        assert_no_coercion_starvation(initial, final, tolerance_pct=0.0, context=context)

    def reconcile(
        self,
        pos_gross: float,
        delivery_gross: float,
        delivery_net: float,
        delivery_tax: float,
        delivery_fee: float,
        platform_estimate: Optional[float] = None,
    ) -> Dict[str, Any]:
        return reconcile_channel_ledgers(
            primary_gross=pos_gross,
            secondary_gross=delivery_gross,
            secondary_net=delivery_net,
            secondary_tax=delivery_tax,
            secondary_fee=delivery_fee,
            platform_estimate=platform_estimate,
        )

    def check_bounds(self, df: pd.DataFrame, metric_col: str, date_col: str = "date") -> Dict[str, Any]:
        return validate_financial_bounds(
            df=df,
            metric_col=metric_col,
            date_col=date_col,
            z_threshold=self.z_threshold,
            drop_threshold=self.drop_threshold,
            timezone_str=self.timezone_str,
        )

    def check_cash_ratio(self, df: pd.DataFrame, cash_col: str, digital_col: str, date_col: str = "date") -> Dict[str, Any]:
        return validate_cash_ratio_variance(
            df=df,
            cash_col=cash_col,
            digital_col=digital_col,
            date_col=date_col,
        )

    def check_promo_share(self, df: pd.DataFrame, promo_col: str, date_col: str = "date") -> float:
        return validate_promo_threshold(
            df=df,
            promo_col=promo_col,
            date_col=date_col,
            max_threshold=self.max_promo_share,
        )

    def export_cache(self, df: pd.DataFrame, target_path: str) -> bool:
        return safe_atomic_parquet_export(df, target_path)
