"""Unit tests and property-based tests for recursive serialization primitive."""

from __future__ import annotations

from datetime import date, datetime
import json
from hypothesis import given, strategies as st
import numpy as np
import pandas as pd

from ai_ops_eval_harness.serialization import make_serializable


class TestSerialization:
    def test_make_serializable_handles_all_structures(self) -> None:
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

        # Must be natively JSON dumpable
        dumped = json.dumps(clean)
        assert isinstance(dumped, str)


class TestPropertyBasedSerialization:
    @given(st.recursive(
        st.none() | st.booleans() | st.integers() | st.floats(allow_nan=True) | st.text(),
        lambda children: st.lists(children, max_size=5) | st.dictionaries(st.text(max_size=10), children, max_size=5),
        max_leaves=15,
    ))
    def test_fuzz_json_serializability(self, arbitrary_data: object) -> None:
        cleaned = make_serializable(arbitrary_data)
        # Result must serialize via json.dumps without raising TypeError
        json_str = json.dumps(cleaned)
        assert isinstance(json_str, str)
