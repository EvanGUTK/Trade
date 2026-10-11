# trader/ — Python 3.14, uv. Every target is real; see trader/CLAUDE.md.
.DEFAULT_GOAL := help
UV ?= uv
ENV_FILE ?= ../.env
ENV_FLAG := $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)
TRADE_DATA_DIR ?= $(abspath ../data)
export TRADE_DATA_DIR
RUN_ID ?=

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

setup: ## create .venv and install runtime + dev dependencies
	$(UV) sync

check: ## format check + lint + strict typecheck (src and tests)
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run mypy src tests

test: ## unit tests (never call the Anthropic API)
	$(UV) run pytest -q

fmt: ## format and autofix lint
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

run: ## propose loop: the Trader writes/revises one strategy (planned until Phase 2)
	$(UV) run $(ENV_FLAG) python -m trade_trader run

review: ## post-mortem loop for RUN_ID=<run id> (planned until Phase 2)
	$(UV) run $(ENV_FLAG) python -m trade_trader review $(if $(RUN_ID),--run-id $(RUN_ID),)

build: ## build sdist + wheel into dist/
	$(UV) build

.PHONY: help setup check test fmt run review build
