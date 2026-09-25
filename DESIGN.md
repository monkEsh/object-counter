# Homework implementation notes

## What the application does

This project is a Flask object-counting service organized with hexagonal architecture.

Request flow:

1. `counter/entrypoints/webapp.py` validates HTTP form input and returns JSON/UI responses.
2. `counter/domain/actions.py` orchestrates use cases:
   - `CountDetectedObjects` filters detections above a threshold, counts classes, and stores totals.
   - `PredictObjects` stores individual prediction runs and annotated-image metadata.
3. `counter/domain/ports.py` defines the object detector and repository ports.
4. `counter/adapters/object_detector.py` adapts TensorFlow Serving to domain `Prediction` objects.
5. `counter/adapters/count_repo.py` adapts PostgreSQL/SQLAlchemy and in-memory repositories.

## Homework coverage

- New prediction endpoint: `POST /predictions` accepts `file`, `threshold`, and optional `model_name` and returns filtered predictions.
- Relational DB adapter: `CountPostgreSQLRepo` and `PredictionRunPostgreSQLRepo` persist data in PostgreSQL with Alembic migrations.
- Multiple internal models: `resources/model_registry.json` maps public model aliases to internal serving names and model metadata.
- Improvements implemented: validation, tests, Docker Compose, Alembic migrations, UI, model registry, smoke-test script, OpenAPI docs, explicit backend error handling.
- Optional item chosen: improved testing and service verification through unit tests plus a runnable smoke test.

## Implemented next steps

### Task runner

`Makefile` now standardizes common operations:

- `make setup`
- `make test`
- `make up`
- `make migrate`
- `make smoke`
- `make integration-smoke`
- `make down`

### Smoke/integration verification

`scripts/smoke_test.py` verifies a running app by calling:

- `GET /models`
- `POST /object-count`
- `POST /predictions`
- `GET /prediction-runs/{id}`

This gives a lightweight end-to-end check without adding more dependencies.

### Model registry consistency

The committed `resources/model_registry.json` exposes two use-case-specific public aliases that both point at the checked-in TensorFlow Serving model: `count-current -> rfcn` and `prediction-current -> rfcn`.

`default_count_model` controls `/object-count` when `model_name` is omitted, and `default_prediction_model` controls `/predictions` when `model_name` is omitted.

### TensorFlow Serving robustness

`TFSObjectDetector` now:

- sends a request timeout;
- calls `raise_for_status()`;
- validates JSON structure;
- reports malformed responses as `DetectorUnavailableError`;
- supports per-model `label_map` configuration;
- returns fallback names like `class_123` when labels are missing.

Flask converts detector backend failures to HTTP `502` instead of leaking implementation tracebacks.

### Model-specific metadata

`ModelInfo` and the registry now include:

- `framework`
- `label_map`
- `output_schema`

Only `tensorflow-serving` is currently executable. Unsupported frameworks are rejected early with a clear config error. The shape is ready for future adapters such as ONNX Runtime or TorchServe.

## Migration story

The migration history intentionally shows the evolution of the homework:

- `0001_create_object_counts.py` creates the original cumulative table.
- `0002_create_object_count_observations.py` adds append-only observations used by the current repository.
- `0003_create_object_prediction_runs.py` adds stored prediction runs.

For a production greenfield deployment, these could be squashed into one initial migration. For this homework, keeping the history is useful because it demonstrates iterative schema evolution.

## Future work

If more time were available, the next production improvements would be:

1. Add a real Docker Compose CI job that waits for app health before running `make smoke`.
2. Add retention/cleanup for `tmp/debug/*.jpg`.
3. Add adapter implementations for `onnx-runtime`, `torchserve`, or `local-pytorch` behind the existing `ObjectDetector` port.
4. Add authentication/rate limiting if the endpoint becomes public.
