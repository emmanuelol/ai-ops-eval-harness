"""Module execution entrypoint for python -m ai_ops_eval_harness."""

from __future__ import annotations

import sys
from ai_ops_eval_harness.cli import main

if __name__ == "__main__":
    sys.exit(main())
