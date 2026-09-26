# NIQ Innovation Enablement - Challenge 1 (Object Counting)

This repo demonstrates a hexagonal-architecture object-counting service for ML-based image detection.

The Flask API receives an image, an optional public `model_name`, and a detection `threshold`. It can return per-request object counts, cumulative totals, or the filtered prediction list for a stored prediction run.

## Quick start for new developers

Use Docker Compose for local development. The Compose stack runs Flask, PostgreSQL, migrations, TensorFlow Serving, and the smoke test without installing Python dependencies on the host.

Prerequisites:

- Docker and Docker Compose
- `make`
- `wget` and `tar`
- enough disk space for the downloaded sample model

1. Prepare the sample model:

```bash
mkdir -p tmp
wget -O rfcn_resnet101_fp32_coco_pretrained_model.tar.gz \
  https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/rfcn-resnet101-coco-tf/rfcn_resnet101_coco_2018_01_28.tar.gz

tar -xzvf rfcn_resnet101_fp32_coco_pretrained_model.tar.gz -C tmp
rm rfcn_resnet101_fp32_coco_pretrained_model.tar.gz
chmod -R 777 tmp/rfcn_resnet101_coco_2018_01_28
mkdir -p tmp/model/rfcn/1
mv tmp/rfcn_resnet101_coco_2018_01_28/saved_model/saved_model.pb tmp/model/rfcn/1
rm -rf tmp/rfcn_resnet101_coco_2018_01_28
```

2. Start the full stack and smoke-test it:

```bash
make integration-smoke
```

This starts TensorFlow Serving, starts PostgreSQL and the Flask app, runs migrations, then runs the smoke test. It intentionally leaves the services running so you can inspect the app afterward.

The local app listens on http://127.0.0.1:5001.

Try the API:

```bash
curl http://127.0.0.1:5001/models
curl -F "threshold=0.9" \
  -F "file=@resources/images/boy.jpg" \
  http://127.0.0.1:5001/object-count
```

Stop services when done:

```bash
make down
make tfs-down
```

Note: `docker-compose.yml` currently uses an ARM64 TensorFlow Serving image for Apple Silicon Macs. On amd64 Linux/Intel machines, replace the `tfserving` image with an amd64-compatible TensorFlow Serving image before running the local Docker setup.

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
- `Makefile` and `scripts/smoke_test.py` automate setup, tests, migrations, and smoke verification.

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

## Useful Make targets

- `make up`: build and start the Flask app and PostgreSQL. Use this after TensorFlow Serving is already running.
- `make tfs-up`: start TensorFlow Serving and wait for the `rfcn` model to become healthy.
- `make migrate`: run Alembic migrations against the Docker PostgreSQL service.
- `make smoke`: run the smoke test against the Docker app service.
- `make integration-smoke`: run the full integration path: TensorFlow Serving, app, PostgreSQL, migrations, and smoke test.
- `make down`: stop the app/PostgreSQL stack.
- `make tfs-down`: stop TensorFlow Serving.

Run tests in Docker:

```bash
docker compose --profile test run --rm test
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

## Tests and verification

Run unit/adapter/endpoint tests in Docker:

```bash
docker compose --profile test run --rm test
```

Smoke-test the running Docker app:

```bash
make smoke
```

## Database migrations

Migrations are in `migrations/versions`.

- `0001_create_object_counts.py`: original cumulative table retained for schema-history clarity.
- `0002_create_object_count_observations.py`: current append-only count-observation table.
- `0003_create_object_prediction_runs.py`: stored prediction runs.

For a fresh production system these could be squashed into one initial migration. For this homework repo they remain separate to show the evolution from the original implementation to the current one.
