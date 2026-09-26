.PHONY: setup test up down tfs-up tfs-down migrate smoke integration-smoke local-smoke clean-debug

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
# Tests use only fakes/in-memory repos — no Docker needed.
# Run setup first if .venv doesn't exist.
test:
	$(PY) -m pytest -q

# ── stack ─────────────────────────────────────────────────────────────────────
# Starts app + postgres only. TF Serving is a separate opt-in (see tfs-up).
up:
	docker compose up --build

down:
	docker compose down

# ── TF Serving ────────────────────────────────────────────────────────────────
# Start TF Serving in the background and wait until its healthcheck passes.
tfs-up:
	docker compose --profile tfserving up -d tfserving
	@echo "Waiting for TF Serving to become healthy..."
	@until docker inspect --format='{{.State.Health.Status}}' object-counter-tfserving 2>/dev/null | grep -q healthy; do \
		echo "  still waiting..."; sleep 5; \
	done
	@echo "TF Serving is healthy."

tfs-down:
	docker compose --profile tfserving down tfserving

# ── migrations ────────────────────────────────────────────────────────────────
migrate:
	docker compose --profile migrate run --rm migrate

# ── smoke test ────────────────────────────────────────────────────────────────
# Requires `make up` already running in another terminal.
smoke:
	docker compose --profile smoke run --rm smoke

# ── full integration flow (build → up → migrate → smoke → down) ───────────────
integration-smoke:
	$(MAKE) tfs-up
	docker compose up -d --build postgres app
	docker compose --profile migrate run --rm migrate
	docker compose --profile smoke  run --rm smoke

# ── local smoke (against a locally running app on 5001) ──────────────────────
LOCAL_BASE_URL ?= http://127.0.0.1:5001
LOCAL_IMAGE    ?= resources/images/boy.jpg
local-smoke:
	$(PY) scripts/smoke_test.py --base-url $(LOCAL_BASE_URL) --image $(LOCAL_IMAGE)

# ── misc ──────────────────────────────────────────────────────────────────────
clean-debug:
	rm -f tmp/debug/*.jpg
