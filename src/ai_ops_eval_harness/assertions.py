"""Deterministic contract assertions for AI Ops outputs, prompt contexts, and pipeline completeness."""

import re
import logging
from typing import Optional, List, Dict, Any
import pandas as pd

from ai_ops_eval_harness.exceptions import (
    DataStarvationError,
    EvalAssertionError,
)

logger = logging.getLogger(__name__)


def audit_temporal_completeness(
    df: pd.DataFrame,
    expected_days: int,
    value_col: str = "revenue",
    date_col: str = "date",
    raise_on_fatal: bool = True,
) -> Dict[str, Any]:
    """Audits temporal density of time-series data to detect silent starvation.
    
    Returns structured audit diagnostics:
    - fatal_starvation: 0 valid days found within expected temporal window.
    - partial_starvation: Less than expected days found.
    - complete: All expected days contain valid non-zero values.
    """
    if df is None or df.empty or value_col not in df.columns:
        if raise_on_fatal and expected_days > 0:
            raise DataStarvationError(f"FATAL: Temporal dataset is empty. Expected {expected_days} days.")
        return {
            "status": "fatal_starvation",
            "valid_days": 0,
            "expected_days": expected_days,
            "completeness_pct": 0.0,
        }

    valid_mask = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0) > 0
    valid_days = int(valid_mask.sum())
    completeness_pct = round((valid_days / expected_days) * 100.0, 2) if expected_days > 0 else 100.0

    if valid_days == 0:
        if raise_on_fatal and expected_days > 0:
            raise DataStarvationError(f"FATAL: 0 valid days with positive {value_col} detected across {expected_days} requested days.")
        status = "fatal_starvation"
    elif valid_days < expected_days:
        logger.warning(f"PARTIAL STARVATION: Only {valid_days}/{expected_days} days have valid data.")
        status = "partial_starvation"
    else:
        status = "complete"

    return {
        "status": status,
        "valid_days": valid_days,
        "expected_days": expected_days,
        "completeness_pct": completeness_pct,
    }


def assert_decoupled_json_contract(
    payload: Dict[str, Any],
    required_keys: Optional[List[str]] = None,
    allowed_statuses: Optional[List[str]] = None,
) -> None:
    """Validates that agent execution output conforms strictly to decoupled JSON contract.
    
    Verifies absence of raw python exception tracebacks, raw <ERROR> tags, or forbidden XML media tags.
    """
    if not isinstance(payload, dict):
        raise EvalAssertionError(f"Contract violation: Expected dict payload, got {type(payload).__name__}")

    keys = required_keys or ["status", "text"]
    for k in keys:
        if k not in payload:
            raise EvalAssertionError(f"Contract violation: Missing required key '{k}' in response payload.")

    statuses = allowed_statuses or ["success", "error", "anomaly_halt", "data_unavailable", "partial_success"]
    actual_status = payload.get("status")
    if actual_status not in statuses:
        raise EvalAssertionError(f"Contract violation: Unexpected status '{actual_status}'. Expected one of {statuses}")

    text_content = str(payload.get("text", "")) + " " + str(payload.get("message", ""))

    # Reject raw stack trace leaks
    if "Traceback (most recent call last)" in text_content:
        raise EvalAssertionError("Contract violation: Raw python traceback detected in user-facing payload.")

    # Reject raw unparsed XML error tags
    if "<ERROR>" in text_content or "</ERROR>" in text_content:
        raise EvalAssertionError("Contract violation: Unparsed <ERROR> XML tags detected in user-facing output.")

    # Reject deprecated XML media tags
    if "<media>" in text_content or "</media>" in text_content:
        raise EvalAssertionError("Contract violation: Forbidden XML <media> tag detected. Use standard markdown syntax.")


def assert_ultra_concise_disclosure(
    text: str,
    user_prompt: str = "",
    max_bullet_points: int = 4,
    expansion_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Enforces progressive disclosure UX guardrail.
    
    By default, responses must remain ultra-concise (short bullet summary, NO markdown tables).
    Deep dives and tables are only permitted if user prompt explicitly includes trigger keywords.
    """
    keywords = expansion_keywords or ["detallado", "completo", "desglose", "detalle", "tabla", "deep-dive"]
    prompt_lower = user_prompt.lower()
    is_expanded_request = any(kw in prompt_lower for kw in keywords)

    # Detect markdown table pattern: '| header |' followed by '| --- |'
    has_markdown_table = bool(re.search(r"\|[^\n]+\|\n\s*\|[\s:\-]+\|", text))

    # Count bullet points
    bullet_matches = re.findall(r"(?:^|\n)\s*[\*\-]\s+[^\n]+", text)
    bullet_count = len(bullet_matches)

    if not is_expanded_request:
        if has_markdown_table:
            raise EvalAssertionError(
                "UX Regresion: Markdown table generated in default ultra-concise mode without expansion keywords."
            )
        if bullet_count > max_bullet_points:
            raise EvalAssertionError(
                f"UX Regresion: Output contains {bullet_count} bullets, exceeding ultra-concise ceiling of {max_bullet_points}."
            )

    return {
        "is_expanded_request": is_expanded_request,
        "bullet_count": bullet_count,
        "has_markdown_table": has_markdown_table,
    }


def assert_prompt_context_integrity(
    prompt_context: str,
    required_markers: List[str],
    forbidden_markers: Optional[List[str]] = None,
) -> None:
    """Verifies that pre-aggregated KPIs and XML blocks are cleanly assembled prior to LLM call."""
    for marker in required_markers:
        if marker not in prompt_context:
            raise EvalAssertionError(f"Prompt integrity failed: Missing required marker '{marker}' in context.")

    if forbidden_markers:
        for marker in forbidden_markers:
            if marker in prompt_context:
                raise EvalAssertionError(f"Prompt integrity failed: Forbidden marker '{marker}' detected in context.")
