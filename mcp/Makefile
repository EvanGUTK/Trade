# mcp/ — Python 3.14, uv. Every target is real; see mcp/CLAUDE.md.
.DEFAULT_GOAL := help
UV ?= uv
ENV_FILE ?= ../.env
ENV_FLAG := $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

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

run: ## serve over stdio (what Claude Code / claude.ai launch)
	$(UV) run $(ENV_FLAG) python -m trade_mcp --transport stdio

stdio: run ## alias of run

run-http: ## serve streamable HTTP on 127.0.0.1:$$TRADE_MCP_PORT (default 8788)
	$(UV) run $(ENV_FLAG) python -m trade_mcp --transport streamable-http

build: ## build sdist + wheel into dist/
	$(UV) build

.PHONY: help setup check test fmt run stdio run-http build
