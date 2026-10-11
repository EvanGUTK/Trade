# Trade — root Makefile. Every target delegates to a component; components may be
# absent during Phase 0, in which case their targets are no-ops that say so.
SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPONENTS := engine gateway strategies mcp trader web

define exists
$(if $(wildcard $(1)/Makefile),,@echo "[$(1)] not scaffolded yet, skipping";)
endef

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n",$$1,$$2}'

setup: ## install toolchains/deps for every scaffolded component
	@for c in $(COMPONENTS); do [ -f $$c/Makefile ] && $(MAKE) -C $$c setup || echo "[$$c] not scaffolded yet"; done

check: ## format-check + lint + typecheck everywhere
	@for c in $(COMPONENTS); do [ -f $$c/Makefile ] && $(MAKE) -C $$c check || echo "[$$c] not scaffolded yet"; done

test: ## unit tests everywhere
	@for c in $(COMPONENTS); do [ -f $$c/Makefile ] && $(MAKE) -C $$c test || echo "[$$c] not scaffolded yet"; done

build: ## build everywhere
	@for c in $(COMPONENTS); do [ -f $$c/Makefile ] && $(MAKE) -C $$c build || echo "[$$c] not scaffolded yet"; done

dev: ## gateway + web + mcp with hot reload (planned: process-compose)
	@echo "planned: run 'make gateway-run', 'make web-dev', 'make mcp-run' in separate panes"

# Per-component passthrough: make engine-build, make web-dev, etc.
$(foreach c,$(COMPONENTS),$(eval $(c)-%: ; @[ -f $(c)/Makefile ] && $$(MAKE) -C $(c) $$* || echo "[$(c)] not scaffolded yet"))

worktrees: ## list worker worktrees
	@git worktree list

.PHONY: help setup check test build dev worktrees
