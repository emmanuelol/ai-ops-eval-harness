.PHONY: all build test audit check-blacklist lint typecheck lock examples clean

all: lint typecheck test audit examples

build:
	docker compose build

test:
	uv run --extra dev pytest tests/ -v --cov=ai_ops_eval_harness

test-docker:
	docker compose run --rm test

check-blacklist:
	bash scripts/check_blacklist.sh .

audit:
	bash scripts/check_blacklist.sh .
	bash scripts/audit_image.sh ai-ops-eval-harness:latest

lint:
	uv run ruff check . --ignore=E501,W293,I001,F401,B904

typecheck:
	uv run mypy src/ai_ops_eval_harness --ignore-missing-imports

lock:
	uv lock

examples:
	uv run python examples/01_llm_contract_eval.py
	uv run python examples/02_financial_circuit_breaker.py
	uv run python examples/03_scenario_harness_runner.py

clean:
	rm -rf .pytest_cache .coverage coverage.xml build dist *.egg-info src/*.egg-info
