# DeathStar / PeopleSoft Hypergraph Intelligence
# Developer convenience targets.
#
# Typical workflow:
#   make check          run syntax check + unit tests (fast, no DB)
#   make smoke          run admin shell smoke test (needs Chrome + running server)
#   make lint           syntax check only
#   make test           unit tests only

PYTHON  ?= python3
VENV    ?= .venv
PY      := $(VENV)/bin/python3
PORT    ?= 8088
HOST    ?= 127.0.0.1

.PHONY: all check lint test smoke serve help

all: check

# ── fast checks (no DB / Chrome required) ─────────────────────────────────

## lint: syntax-check all Python source files
lint:
	$(PYTHON) scripts/syntax_check.py --quiet

## test: run unit tests (no DB required)
test:
	$(PYTHON) -m unittest discover -s tests/ -v

## check: run lint + unit tests
check: lint test

# ── server ────────────────────────────────────────────────────────────────

## serve: start the dev server (hot-reload disabled; use with live Oracle)
serve:
	$(PY) -m uvicorn main:app --host $(HOST) --port $(PORT)

# ── smoke test (requires Chrome + running server) ─────────────────────────

## smoke: run admin shell smoke test against a local running server
smoke:
	$(PYTHON) scripts/smoke_admin_shell.py --base-url http://$(HOST):$(PORT)

# ── help ─────────────────────────────────────────────────────────────────

help:
	@echo "Targets:"
	@grep -E '^## ' Makefile | sed 's/^## /  /'
