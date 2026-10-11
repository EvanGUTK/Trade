# Trade — root Makefile. Every target delegates to a component. Components may be
# absent during Phase 0: their targets print a notice and succeed. A component
# that exists and fails makes the target fail (this is the merge gate, ADR 0005).
SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPONENTS := engine gateway strategies mcp trader web

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-20s %s\n",$$1,$$2}'

setup: ## install toolchains/deps for every scaffolded component
	@for c in $(COMPONENTS); do if [ -f $$c/Makefile ]; then $(MAKE) -C $$c setup || exit 1; else echo "[$$c] not scaffolded yet"; fi; done

check: ## format-check + lint + typecheck everywhere (fails if any component fails)
	@for c in $(COMPONENTS); do if [ -f $$c/Makefile ]; then $(MAKE) -C $$c check || exit 1; else echo "[$$c] not scaffolded yet"; fi; done

test: ## unit tests everywhere (fails if any component fails)
	@for c in $(COMPONENTS); do if [ -f $$c/Makefile ]; then $(MAKE) -C $$c test || exit 1; else echo "[$$c] not scaffolded yet"; fi; done

build: ## build everywhere
	@for c in $(COMPONENTS); do if [ -f $$c/Makefile ]; then $(MAKE) -C $$c build || exit 1; else echo "[$$c] not scaffolded yet"; fi; done

dev: ## gateway + web + mcp with hot reload (planned: process-compose)
	@echo "planned: run 'make gateway-run', 'make web-dev', 'make mcp-run' in separate panes"

# Per-component passthrough: make engine-build, make web-dev, etc.
# A missing component prints a notice; an existing component's failure propagates.
$(foreach c,$(COMPONENTS),$(eval $(c)-%: ; @if [ -f $(c)/Makefile ]; then $$(MAKE) -C $(c) $$*; else echo "[$(c)] not scaffolded yet"; fi))

worktrees: ## list worker worktrees
	@git worktree list

.PHONY: help setup check test build dev worktrees
