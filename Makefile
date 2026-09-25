.PHONY: setup test up down migrate smoke integration-smoke clean-debug

# ── local dev (venv) ──────────────────────────────────────────────────────────
PYTHON ?= python3.9
VENV   ?= .venv
PIP    := $(VENV)/bin/pip
PY     := $(VENV)/bin/python

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

# ── tests ─────────────────────────────────────────────────────────────────────
# Runs entirely inside Docker — no local venv required.
test:
	docker compose --profile test run --rm test

# ── stack ─────────────────────────────────────────────────────────────────────
up:
	docker compose up --build

down:
	docker compose down

# ── migrations ────────────────────────────────────────────────────────────────
# Runs alembic inside a one-off container connected to the Compose postgres.
migrate:
	docker compose --profile migrate run --rm migrate

# ── smoke test ────────────────────────────────────────────────────────────────
# Requires `make up` already running.  Runs smoke_test.py inside Docker,
# calling the app container over the internal Docker network (app:5001).
smoke:
	docker compose --profile smoke run --rm smoke

# ── full integration flow (build → migrate → smoke) ──────────────────────────
integration-smoke:
	docker compose up -d --build postgres tfserving app
	docker compose --profile migrate run --rm migrate
	docker compose --profile smoke  run --rm smoke

# ── local smoke (against a locally running app on 5001) ──────────────────────
# Useful when running `python -m counter.entrypoints.webapp` directly.
LOCAL_BASE_URL ?= http://127.0.0.1:5001
LOCAL_IMAGE    ?= resources/images/boy.jpg
local-smoke:
	$(PY) scripts/smoke_test.py --base-url $(LOCAL_BASE_URL) --image $(LOCAL_IMAGE)

# ── misc ──────────────────────────────────────────────────────────────────────
clean-debug:
	rm -f tmp/debug/*.jpg
