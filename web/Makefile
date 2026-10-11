# web/ — Vite + React 19 + TypeScript. Every target shells out to pnpm so the
# Makefile and package.json scripts never drift. Run from web/ or via the root
# Makefile as `make web-<target>`.
SHELL := /bin/bash
.DEFAULT_GOAL := help

PNPM := pnpm

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

setup: ## install dependencies from pnpm-lock.yaml (resolving install if the lockfile is stale)
	$(PNPM) install --frozen-lockfile || $(PNPM) install

check: ## prettier --check, eslint, tsc --noEmit
	$(PNPM) exec prettier --check .
	$(PNPM) exec eslint .
	$(PNPM) exec tsc --noEmit

test: ## vitest, single run
	$(PNPM) exec vitest run

fmt: ## prettier --write and eslint --fix
	$(PNPM) exec prettier --write .
	$(PNPM) exec eslint . --fix

dev: ## vite dev server on TRADE_WEB_PORT (default 5173), proxying /api and /ws to the gateway
	$(PNPM) exec vite

build: ## production build into dist/
	$(PNPM) exec vite build

.PHONY: help setup check test fmt dev build
