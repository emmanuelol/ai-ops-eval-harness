"""Defensive serialization helpers for analytical outputs and LLM payload envelopes."""

from typing import Any
from datetime import datetime, date
import numpy as np
import pandas as pd


def make_serializable(data: Any) -> Any:
    """Recursively converts Pandas/NumPy types to native Python primitives for JSON serialization.
    
    Guarantees that NaT, NaN, and Null representations cleanly coerce to None,
    and all numeric and temporal structures map directly to JSON primitives.
    """
    if data is None:
        return None

    if type(data).__name__ == "NaTType":
        return None

    try:
        if bool(pd.isna(data)):
            return None
    except (ValueError, TypeError):
        pass

    if isinstance(data, dict):
        return {str(k): make_serializable(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple, set)):
        return [make_serializable(v) for v in data]
    elif isinstance(data, (datetime, date, pd.Timestamp)):
        return data.isoformat()
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, (np.floating, float)):
        val = float(data)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    elif isinstance(data, (np.bool_, bool)):
        return bool(data)
    elif isinstance(data, np.ndarray):
        return [make_serializable(v) for v in data.tolist()]
    elif hasattr(data, "item"):
        try:
            return make_serializable(data.item())
        except Exception:
            pass
    elif hasattr(data, "tolist"):
        try:
            return [make_serializable(v) for v in data.tolist()]
        except Exception:
            pass

    return data
