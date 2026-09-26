# Homework Assessment

This document maps the NielsenIQ Innovation Enablement homework requirements to the implementation in this repository. It is intended to make the review and interview discussion explicit instead of requiring evaluators to infer the work only from source code.

## Assignment coverage

| Requirement | Status | Evidence |
|---|---|---|
| Add an endpoint that receives an image and threshold and returns predictions. | Done | `POST /predictions` in `counter/entrypoints/webapp.py`; `PredictObjects` in `counter/domain/actions.py`; endpoint tests in `tests/entrypoints/test_webapp.py`. |
| Add a relational database adapter for `ObjectCountRepo`. | Done | `CountPostgreSQLRepo` in `counter/adapters/count_repo.py`; Alembic migration `0002_create_object_count_observations.py`; adapter tests in `tests/adapters/test_count_repo.py`. |
| Review the source and propose improvements. | Done here | See “Implemented improvements”, “Additional improvements implemented”, and “Remaining future improvement”. |
| Implement at least one proposed improvement. | Done | Implemented Docker Compose automation, improved validation/error handling, model registry support, PostgreSQL persistence, and smoke verification. |
| Explain what should change for multiple internally trained private models. | Done | Public model aliases map to private TensorFlow Serving names through `resources/model_registry.json`; `/models` hides internal serving names; `resources/model_registry.example.json` and `tmp/model/model_config.example.config` show multi-model setup. |
| Improve testing/integration/e2e tests or support other frameworks. | Done | Unit/adapter/endpoint tests are present; `scripts/smoke_test.py` verifies the running Docker app; `make integration-test` verifies persisted rows in PostgreSQL. |

## Implemented improvements

### Docker Compose development setup

The local development path is Docker Compose-first. The stack includes:

- Flask app
- PostgreSQL
- Alembic migration runner
- TensorFlow Serving
- smoke-test runner
- test runner

The Makefile automates common workflows:

- `make prepare-model`
- `make tfs-up`
- `make up`
- `make migrate`
- `make smoke`
- `make integration-smoke`

### Automated model preparation

`make prepare-model` downloads and stages the sample RFCN model under `tmp/model/rfcn/1/saved_model.pb`. This replaces a long manual README sequence and keeps setup reproducible.

### Prediction endpoint

`POST /predictions` accepts the same core inputs as `/object-count`:

- `file`
- `threshold`
- optional public `model_name`

It returns filtered predictions with:

- class name
- confidence score
- bounding box
- model name
- threshold
- prediction-run id
- annotated-image metadata

Prediction runs can also be listed and fetched through:

- `GET /prediction-runs`
- `GET /prediction-runs/<prediction_run_id>`

### PostgreSQL persistence

`CountPostgreSQLRepo` stores append-only count observations and reads totals by aggregating those observations. This keeps a history of count events instead of overwriting a single counter row.

Prediction runs are persisted in `object_prediction_runs`, including threshold, model, annotated image path, and prediction payload.

### Model registry for private model names

External clients use stable public aliases such as:

- `count-current`
- `prediction-current`

The registry maps those aliases to internal TensorFlow Serving names such as `rfcn`. The `/models` response intentionally exposes public aliases and display names, not internal serving names.

### Validation and error handling

The API validates:

- required image upload
- valid image content
- numeric threshold
- threshold range from 0 to 1
- known model aliases

TensorFlow Serving request failures are converted into HTTP 502 responses instead of leaking lower-level exceptions.

## Tradeoffs and current limitations

### TensorFlow Serving is the only executable detector backend

The domain layer depends on an `ObjectDetector` port, and `ModelInfo` already records fields such as `framework`, `label_map`, and `output_schema`. However, only the `tensorflow-serving` framework is executable today.

This is intentional for the homework scope: the code is shaped for future framework support without adding untested TorchServe, ONNX, or PyTorch implementations.

### Multiple model aliases are supported, but the sample stack serves one model

The default registry describes the runnable sample stack and points both current aliases at the RFCN sample model. `resources/model_registry.example.json` and `tmp/model/model_config.example.config` show how to add additional private TensorFlow Serving models without changing the API contract.

### Smoke testing exercises the stack and database writes

`scripts/smoke_test.py` verifies the running API by calling `/models`, `/object-count`, `/predictions`, and `/prediction-runs/<id>`. `make integration-test` adds PostgreSQL assertions for `object_count_observations` and `object_prediction_runs` so the Docker path verifies both API behavior and persisted rows.

### Annotated images are development artifacts

Prediction runs include an annotated image path under `tmp/debug`. This is useful for demos and debugging but should be treated as a local artifact, not durable production storage.

## Additional improvements implemented

### Makefile is Docker-first

The README presents Docker Compose as the local development path, and the Makefile aligns with that path: `make test` runs the Compose test service, while stack operations use Compose services for the app, database, migrations, TensorFlow Serving, and smoke tests.

### Multiple-internal-model examples

The repository includes example files showing how to configure more than one internally trained TensorFlow Serving model:

- `resources/model_registry.example.json`
- `tmp/model/model_config.example.config`

`tests/test_config.py` verifies that public aliases can map to different internal `serving_name` values.

### Docker integration target

`make integration-test` now:

1. prepares the model
2. starts TensorFlow Serving
3. starts PostgreSQL and the Flask app
4. runs migrations
5. runs smoke tests
6. verifies database rows exist in `object_count_observations` and `object_prediction_runs`
7. cleans up Compose services

This strengthens the end-to-end testing story for the homework.

### App health checks

The app exposes `GET /health`, Docker Compose defines an app healthcheck, and the smoke service waits for a healthy app before running.

## Remaining future improvement

### Add OpenAPI documentation

The README has curl examples, but a small `openapi.yaml` would make the API contract clearer and easier to review.

## Interview notes

The main design choices to discuss are:

- Hexagonal architecture keeps Flask, TensorFlow Serving, and PostgreSQL outside the domain use cases.
- Public model aliases decouple client-facing API names from private internal model-serving names.
- Append-only count observations preserve event history and allow total recomputation.
- Docker Compose is the intended local development environment to reduce host setup drift.
- Non-TensorFlow frameworks are intentionally not implemented until there is a concrete model format and serving runtime to test against.
