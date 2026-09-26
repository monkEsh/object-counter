.PHONY: test prepare-model up down tfs-up tfs-down migrate smoke integration-smoke integration-test clean-debug

MODEL_URL         ?= https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/rfcn-resnet101-coco-tf/rfcn_resnet101_coco_2018_01_28.tar.gz
MODEL_ARCHIVE     ?= rfcn_resnet101_fp32_coco_pretrained_model.tar.gz
MODEL_EXTRACT_DIR ?= tmp/rfcn_resnet101_coco_2018_01_28
MODEL_OUTPUT_DIR  ?= tmp/model/rfcn/1
MODEL_OUTPUT_FILE ?= $(MODEL_OUTPUT_DIR)/saved_model.pb

# ── tests ─────────────────────────────────────────────────────────────────────
# Runs unit/adapter/endpoint tests in the Docker Compose test service.
test:
	docker compose --profile test run --rm test

# ── sample model ──────────────────────────────────────────────────────────────
# Downloads and stages the RFCN sample model used by TensorFlow Serving.
prepare-model:
	@if [ -f "$(MODEL_OUTPUT_FILE)" ]; then \
		echo "Sample model already prepared at $(MODEL_OUTPUT_FILE)"; \
		exit 0; \
	fi; \
	set -e; \
	mkdir -p tmp "$(MODEL_OUTPUT_DIR)"; \
	if [ ! -f "$(MODEL_ARCHIVE)" ]; then \
		echo "Downloading sample model..."; \
		wget -O "$(MODEL_ARCHIVE)" "$(MODEL_URL)"; \
	fi; \
	echo "Extracting sample model..."; \
	tar -xzvf "$(MODEL_ARCHIVE)" -C tmp; \
	mv "$(MODEL_EXTRACT_DIR)/saved_model/saved_model.pb" "$(MODEL_OUTPUT_FILE)"; \
	chmod -R u+rwX,go+rX tmp/model/rfcn; \
	rm -rf "$(MODEL_EXTRACT_DIR)" "$(MODEL_ARCHIVE)"; \
	echo "Sample model prepared at $(MODEL_OUTPUT_FILE)"

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
	docker compose --profile tfserving down

# ── migrations ────────────────────────────────────────────────────────────────
migrate:
	docker compose --profile migrate run --rm migrate

# ── smoke test ────────────────────────────────────────────────────────────────
# Requires `make up` already running in another terminal.
smoke:
	docker compose --profile smoke run --rm smoke

# ── full integration flow (build → up → migrate → smoke) ─────────────────────
integration-smoke:
	$(MAKE) prepare-model
	$(MAKE) tfs-up
	docker compose up -d --build postgres app
	docker compose --profile migrate run --rm migrate
	docker compose --profile smoke  run --rm smoke

# ── full integration test (build → smoke → DB assertions → cleanup) ───────────
integration-test:
	@set -e; \
	cleanup() { \
		docker compose --profile tfserving down --remove-orphans; \
	}; \
	trap cleanup EXIT; \
	$(MAKE) prepare-model; \
	$(MAKE) tfs-up; \
	docker compose up -d --build postgres app; \
	docker compose --profile migrate run --rm migrate; \
	docker compose --profile smoke run --rm smoke; \
	docker compose exec -T postgres psql -U object_counter -d object_counter -tAc "SELECT COUNT(*) > 0 FROM object_count_observations" | grep -q t; \
	docker compose exec -T postgres psql -U object_counter -d object_counter -tAc "SELECT COUNT(*) > 0 FROM object_prediction_runs" | grep -q t; \
	echo "Integration test passed: smoke succeeded and database rows exist."

# ── misc ──────────────────────────────────────────────────────────────────────
clean-debug:
	rm -f tmp/debug/*.jpg
