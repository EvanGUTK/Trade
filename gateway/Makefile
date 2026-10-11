# gateway/ — Makefile. The root Makefile delegates here as `make gateway-<target>`.
# Every target uses --locked so the committed Cargo.lock is authoritative.
SHELL := /bin/bash
CARGO ?= cargo

.PHONY: setup build check test fmt run clean

setup: ## install rustfmt + clippy (best-effort)
	-rustup component add rustfmt clippy

build: ## compile the gateway binary and library
	$(CARGO) build --locked

check: ## format check + clippy with warnings denied on every target
	$(CARGO) fmt --all -- --check
	$(CARGO) clippy --all-targets --locked -- -D warnings

test: ## unit + integration tests
	$(CARGO) test --locked

fmt: ## rewrite sources with rustfmt
	$(CARGO) fmt --all

run: ## run the gateway on 127.0.0.1:${TRADE_GATEWAY_PORT:-8787}
	$(CARGO) run --locked

clean: ## remove target/
	$(CARGO) clean
