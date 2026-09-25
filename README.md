# NIQ Innovation Enablement - Challenge 1 (Object Counting)

This repo demonstrates a hexagonal-architecture object-counting service for ML-based image detection.

The Flask API receives an image, an optional public `model_name`, and a detection `threshold`. It can return per-request object counts, cumulative totals, or the filtered prediction list for a stored prediction run.

## Architecture

- `entrypoints`: Flask API, UI routes, request validation, and HTTP serialization.
- `domain`: use cases and business rules; independent of TensorFlow Serving and PostgreSQL.
- `adapters`: external service adapters for TensorFlow Serving and SQLAlchemy/PostgreSQL.

Request flow:

1. `counter/entrypoints/webapp.py` parses and validates HTTP form data.
2. `counter/domain/actions.py` selects a model, calls an `ObjectDetector`, filters predictions by threshold, and persists results.
3. `counter/adapters/object_detector.py` converts TensorFlow Serving responses into domain predictions.
4. `counter/adapters/count_repo.py` stores object-count observations and prediction runs.

The original sample model comes from IntelAI/Open Model Zoo:
https://github.com/IntelAI/models/blob/master/docs/object_detection/tensorflow_serving/Tutorial.md

## Implemented homework items

- `POST /predictions` returns filtered predictions and stores a prediction run.
- PostgreSQL adapters persist object-count observations and prediction runs.
- Alembic migrations define database schema.
- Multiple internal TensorFlow Serving models are supported through public aliases in a model registry.
- TensorFlow Serving failures return HTTP 502 with a clear error.
- Tests cover domain logic, config parsing, Flask endpoints, SQLAlchemy repositories, and TensorFlow Serving adapter error handling.
- `Makefile`, `scripts/smoke_test.py`, `DESIGN.md`, and `openapi.yaml` document and automate setup/verification.

## Model registry

The committed `resources/model_registry.json` exposes two public model instances for the two service use cases, while both point at the same checked-in TensorFlow Serving model (`rfcn`):

```json
{
  "default_model": "count-current",
  "default_count_model": "count-current",
  "default_prediction_model": "prediction-current",
  "models": {
    "count-current": {
      "display_name": "Current RFCN Count Model",
      "framework": "tensorflow-serving",
      "serving_name": "rfcn",
      "label_map": "counter/adapters/mscoco_label_map.json",
      "output_schema": "tensorflow-object-detection-api-v1"
    },
    "prediction-current": {
      "display_name": "Current RFCN Prediction Model",
      "framework": "tensorflow-serving",
      "serving_name": "rfcn",
      "label_map": "counter/adapters/mscoco_label_map.json",
      "output_schema": "tensorflow-object-detection-api-v1"
    }
  }
}
```

Public clients send aliases such as `count-current` or `prediction-current`; internal TensorFlow Serving names such as `rfcn` are not exposed by `/models`. This keeps count and prediction defaults configurable independently even while they share the same underlying model artifact.

To add internal models, copy `resources/model_registry.example.json`, add matching TensorFlow Serving entries in `tmp/model/model_config.config`, and place the SavedModel directories under `tmp/model/<serving_name>/<version>/`.

Example layout:

```text
resources/
  model_registry.json
tmp/model/
  model_config.config
  rfcn/
    1/
      saved_model.pb
  internal_people_v3/
    1/
      saved_model.pb
      variables/
```

Only `tensorflow-serving` is executable today. The registry already records `framework`, `label_map`, and `output_schema` so ONNX/TorchServe/local PyTorch adapters can be added later behind the existing `ObjectDetector` port.

## Prepare the sample model

```bash
wget -O rfcn_resnet101_fp32_coco_pretrained_model.tar.gz \
  https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/rfcn-resnet101-coco-tf/rfcn_resnet101_coco_2018_01_28.tar.gz

tar -xzvf rfcn_resnet101_fp32_coco_pretrained_model.tar.gz -C tmp
rm rfcn_resnet101_fp32_coco_pretrained_model.tar.gz
chmod -R 777 tmp/rfcn_resnet101_coco_2018_01_28
mkdir -p tmp/model/rfcn/1
mv tmp/rfcn_resnet101_coco_2018_01_28/saved_model/saved_model.pb tmp/model/rfcn/1
rm -rf tmp/rfcn_resnet101_coco_2018_01_28
```

## Setup

Recommended:

```bash
make setup
```

Manual equivalent:

```bash
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally with fakes

```bash
source .venv/bin/activate
python -m counter.entrypoints.webapp
```

In dev mode the app uses fake predictions and in-memory repositories, so no Docker services are required.

## Run with Docker services

```bash
make up
```

In another terminal, after services are ready:

```bash
make migrate
make smoke
```

Manual migration command:

```bash
DATABASE_URL=postgresql+psycopg2://object_counter:object_counter@localhost:5432/object_counter \
  .venv/bin/alembic upgrade head
```

## API examples

List models:

```bash
curl http://127.0.0.1:5001/models
```

Count objects with the default model:

```bash
curl -F "threshold=0.9" \
  -F "file=@resources/images/boy.jpg" \
  http://127.0.0.1:5001/object-count
```

Run predictions with an explicit public alias:

```bash
curl -F "model_name=prediction-current" \
  -F "threshold=0.9" \
  -F "file=@resources/images/boy.jpg" \
  http://127.0.0.1:5001/predictions
```

List stored prediction runs:

```bash
curl "http://127.0.0.1:5001/prediction-runs?limit=10&offset=0"
```

Fetch one run:

```bash
curl http://127.0.0.1:5001/prediction-runs/<prediction_run_id>
```

OpenAPI documentation is in `openapi.yaml`.

## Tests and verification

Run unit/adapter/endpoint tests:

```bash
make test
```

Smoke-test a running app:

```bash
make smoke
```

Smoke-test command without Make:

```bash
.venv/bin/python scripts/smoke_test.py --base-url http://127.0.0.1:5001 --image resources/images/boy.jpg
```

## Database migrations

Migrations are in `migrations/versions`.

- `0001_create_object_counts.py`: original cumulative table retained for schema-history clarity.
- `0002_create_object_count_observations.py`: current append-only count-observation table.
- `0003_create_object_prediction_runs.py`: stored prediction runs.

For a fresh production system these could be squashed into one initial migration. For this homework repo they remain separate to show the evolution from the original implementation to the current one.
