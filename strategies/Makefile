# strategies/ — Python 3.14, uv. Every target is real; see strategies/CLAUDE.md.
.DEFAULT_GOAL := help
UV ?= uv

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

setup: ## create .venv and install runtime + dev dependencies
	$(UV) sync

check: ## format check + lint + strict typecheck (src and tests)
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run mypy src tests

test: ## unit tests
	$(UV) run pytest -q

fmt: ## format and autofix lint
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

run: ## strategy runner CLI (argparse stub until Phase 1)
	$(UV) run python -m trade_strategies --help

build: ## build sdist + wheel into dist/
	$(UV) build

.PHONY: help setup check test fmt run build
