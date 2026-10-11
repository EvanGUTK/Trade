# engine/ — OCaml 5 + dune. Called by the root Makefile as `make engine-<target>`.
#
# Every target runs through `opam exec --` when dune is not already on PATH, so
# `make engine-check` works from a shell that never ran `eval $(opam env)`.
SHELL := /bin/bash

# Pin ocamlformat to the version in .ocamlformat: ocamlformat refuses to run
# when the versions differ, which would break `check` in CI.
OPAM_PKGS := dune ocamlformat.0.29.0 yojson alcotest

ifeq ($(shell command -v dune 2>/dev/null),)
DUNE := opam exec -- dune
else
DUNE := dune
endif

.PHONY: setup build check test fmt run clean

setup: ## install dune, ocamlformat, yojson, alcotest into the current opam switch
	opam install -y $(OPAM_PKGS)

build: ## compile library, binary, and tests
	$(DUNE) build

check: ## format check (fails on diff) + full build
	$(DUNE) build @fmt
	$(DUNE) build

test: ## run alcotest suites
	$(DUNE) test

fmt: ## rewrite sources with ocamlformat
	$(DUNE) fmt

run: ## start the engine on stdin/stdout (JSON-RPC lines)
	$(DUNE) exec trade_engine

clean:
	$(DUNE) clean
