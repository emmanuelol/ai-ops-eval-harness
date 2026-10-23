# Contributing to ai-ops-eval-harness

Contributions are welcome! Please adhere to the following principles:

## Architectural & Security Standards
1. **Clean-Room Isolation:** Code must contain zero organization-specific strings, hardcoded IDs, or internal secrets.
2. **Deterministic Verification:** Every PR must pass `make test`, `make check-blacklist`, and `make audit`.
3. **Fail-Open Observability:** Parquet cache exports, logging, and telemetry must never crash primary business or analytical execution.
4. **Strict Contract Assertions:** Financial anomalies and data starvation must trip explicit exceptions rather than generating hallucinated reports.
