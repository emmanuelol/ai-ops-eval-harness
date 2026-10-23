.PHONY: build test audit check-blacklist clean

build:
	docker compose build

test:
	docker compose run --rm test

check-blacklist:
	bash scripts/check_blacklist.sh

audit:
	bash scripts/audit_image.sh ai-ops-eval-harness:latest
	bash scripts/check_blacklist.sh

clean:
	rm -rf .pytest_cache build dist *.egg-info src/*.egg-info
