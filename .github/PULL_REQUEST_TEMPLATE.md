## Summary
Concise summary of changes introduced in this PR.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding evaluation functionality)
- [ ] Breaking change (fix or feature changing public interface/assertions)
- [ ] Documentation update
- [ ] CI/CD or DX enhancement

## Quality Checklist
- [ ] Tests added/updated covering all new assertions and branches
- [ ] `uv run --extra dev pytest tests/ -v --cov=ai_ops_eval_harness` passes
- [ ] `uv run ruff check .` passes without errors
- [ ] `uv run mypy src/ai_ops_eval_harness` passes
- [ ] `bash scripts/check_blacklist.sh .` passes (no secret/IP leaks)
- [ ] PEP 561 typed markers and docstrings preserved
