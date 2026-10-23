# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-22

### Added
- **CLI Entrypoint (`ai-ops-eval`)**: Added headless CLI commands for `eval`, `reconcile`, and `starvation-check`.
- **Python Package Entrypoint**: Enabled execution via `python -m ai_ops_eval_harness`.
- **PEP 561 Typing Marker**: Added `py.typed` marker for downstream `mypy` and `pyright` type checks.
- **Deterministic Lockfile**: Generated `uv.lock` for reproducible dependency environments.
- **Runnable End-to-End Examples**:
  - `examples/01_llm_contract_eval.py`: Prompt assertion, telemetry backoff, and BlastShield isolation.
  - `examples/02_financial_circuit_breaker.py`: Ledger reconciliation, Z-score anomaly tripping, and parquet cache.
  - `examples/03_scenario_harness_runner.py`: Multi-scenario suite execution with JSON reporting.
- **Modular Test Suite (1:1 Mapping)**:
  - Decomposed monolithic test files into dedicated modules: `test_assertions.py`, `test_auditor.py`, `test_scenarios.py`, `test_serialization.py`, `test_telemetry.py`, `test_cli.py`, `test_scripts.py`.
  - Added centralized fixtures in `tests/conftest.py`.
  - Added property-based fuzz testing via `hypothesis` for assertions and recursive serialization.
  - Added unit test suite for operational bash scripts.
- **CI/CD Matrix & DevOps**:
  - Matrix testing across Python 3.11, 3.12, and 3.13.
  - Strict quality gates: `ruff check`, `mypy`, and pytest coverage enforcement (>= 85%).
  - Automated release workflow (`.github/workflows/release.yml`).
  - Automated dependency updates via Dependabot (`.github/dependabot.yml`).
  - Community health templates: issue templates for bug reports and feature requests, and PR template.
  - Enhanced `Makefile` with `lint`, `typecheck`, `lock`, `examples`, and `audit` targets.
- **System Documentation**:
  - `ARCHITECTURE.md`: Subsystem domain models, evaluation lifecycle, and failure modes.
  - `SECURITY.md`: Threat model, clean-room leak scanning policy, and vulnerability reporting.

## [0.1.0] - 2026-10-22

### Added
- Core contract assertions: `assert_decoupled_json_contract`, `assert_ultra_concise_disclosure`, `assert_prompt_context_integrity`, `audit_temporal_completeness`.
- Financial auditor primitives: `reconcile_channel_ledgers`, `validate_financial_bounds`, `validate_cash_ratio_variance`, `validate_promo_threshold`, `safe_atomic_parquet_export`.
- Declarative `ScenarioHarness` and `BlastShield` sandboxing context manager.
- Telemetry decorator `@track_llm_telemetry` with exponential backoff on HTTP 429.
- Clean-room static blacklist scanner (`scripts/check_blacklist.sh`).
- Containerized build and execution environment (`Dockerfile`, `docker-compose.yml`, `scripts/audit_image.sh`).
