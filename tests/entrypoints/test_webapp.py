import io
import json
import uuid

import pytest

from pathlib import Path
from counter.entrypoints.webapp import create_app, _is_debug_enabled


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def image_path():
    ref_dir = Path(__file__).parent
    return ref_dir.parent.parent / "resources" / "images" / "boy.jpg"


def test_index_serves_ui(client):
    response = client.get('/')

    assert response.status_code == 200
    assert b'Object Counter' in response.data
    assert b'/object-count' in response.data
    assert b'/prediction' in response.data


def test_prediction_page_serves_ui(client):
    response = client.get('/prediction')

    assert response.status_code == 200
    assert b'Prediction Runner' in response.data
    assert b'/predictions' in response.data
    assert b'prediction-output' in response.data
    assert b'stored-runs-list' in response.data


def test_ui_static_assets_are_served(client):
    js_response = client.get('/static/app.js')
    prediction_js_response = client.get('/static/prediction.js')
    css_response = client.get('/static/app.css')

    assert js_response.status_code == 200
    assert b"fetch('/object-count'" in js_response.data
    assert prediction_js_response.status_code == 200
    assert b"fetch('/predictions'" in prediction_js_response.data
    assert b'/prediction-runs?limit=' in prediction_js_response.data
    assert b'/debug-images/' in prediction_js_response.data
    assert css_response.status_code == 200
    assert b'.page-shell' in css_response.data
    assert b'.prediction-output' in css_response.data


def test_models_endpoint_lists_available_aliases(monkeypatch):
    monkeypatch.delenv('ENV', raising=False)
    monkeypatch.setenv('MODEL_NAMES', 'current,people-counter')
    monkeypatch.setenv('DEFAULT_MODEL', 'people-counter')
    app = create_app()
    app.config['TESTING'] = True

    with app.test_client() as client:
        response = client.get('/models')

    assert response.status_code == 200
    assert response.get_json() == {
        'default_model': 'people-counter',
        'models': [
            {'name': 'current', 'display_name': 'current', 'is_default': False},
            {'name': 'people-counter', 'display_name': 'people-counter', 'is_default': True},
        ],
    }


def test_models_endpoint_does_not_expose_serving_names(tmp_path, monkeypatch):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'current',
        'models': {
            'current': {
                'display_name': 'Current RFCN Model',
                'serving_name': 'internal_rfcn_service',
            },
        },
    }))
    monkeypatch.setenv('ENV', 'prod')
    monkeypatch.setenv('MODEL_REGISTRY_PATH', str(registry_path))
    monkeypatch.delenv('DEFAULT_MODEL', raising=False)
    app = create_app()
    app.config['TESTING'] = True

    with app.test_client() as client:
        response = client.get('/models')

    assert response.status_code == 200
    assert response.get_json() == {
        'default_model': 'current',
        'models': [
            {'name': 'current', 'display_name': 'Current RFCN Model', 'is_default': True},
        ],
    }


def test_object_detection_defaults_to_current_model(client, image_path):
    with open(image_path, 'rb') as f:
        image_data = f.read()
    image = io.BytesIO(image_data)

    data = {
        'threshold': '0.9',
    }
    data['file'] = (image, 'test.jpg')

    response = client.post('/object-count', data=data,
                           content_type='multipart/form-data', buffered=True)

    assert response.status_code == 200
    assert json.loads(response.data) is not None


def test_object_detection_accepts_explicit_model_name(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/object-count',
                           data={
                               'threshold': '0.9',
                               'model_name': 'people-counter',
                               'file': (image, 'test.jpg'),
                           },
                           content_type='multipart/form-data', buffered=True)

    assert response.status_code == 200
    assert json.loads(response.data) is not None


def test_predictions_endpoint_returns_filtered_predictions(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/predictions',
                           data={
                               'threshold': '0.9',
                               'model_name': 'current',
                               'file': (image, 'test.jpg'),
                           },
                           content_type='multipart/form-data', buffered=True)

    assert response.status_code == 200
    response_json = response.get_json()
    prediction_run_id = response_json.pop('id')
    uuid.UUID(prediction_run_id)

    assert response_json == {
        'model_name': 'current',
        'threshold': 0.9,
        'annotated_image': f'tmp/debug/predictions_{prediction_run_id}.jpg',
        'annotated_image_url': f'/debug-images/predictions_{prediction_run_id}.jpg',
        'predictions': [
            {
                'class_name': 'cat',
                'score': 0.999190748,
                'box': {
                    'xmin': 0.367288858,
                    'ymin': 0.278333426,
                    'xmax': 0.735821366,
                    'ymax': 0.6988855,
                },
            },
        ],
    }


def test_predictions_endpoint_saves_annotated_image(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/predictions',
                           data={
                               'threshold': '0.9',
                               'model_name': 'current',
                               'file': (image, 'test.jpg'),
                           },
                           content_type='multipart/form-data', buffered=True)

    assert response.status_code == 200
    response_json = response.get_json()
    annotated_image = Path(response_json['annotated_image'])
    assert annotated_image.exists()
    assert annotated_image.stat().st_size > 0

    image_response = client.get(response_json['annotated_image_url'])
    assert image_response.status_code == 200
    assert image_response.content_type == 'image/jpeg'
    assert len(image_response.data) > 0


def test_prediction_runs_endpoint_lists_and_gets_stored_runs(client, image_path):
    with open(image_path, 'rb') as f:
        first_image = io.BytesIO(f.read())
    with open(image_path, 'rb') as f:
        second_image = io.BytesIO(f.read())

    first_response = client.post('/predictions',
                                 data={
                                     'threshold': '0.8',
                                     'model_name': 'current',
                                     'file': (first_image, 'first.jpg'),
                                 },
                                 content_type='multipart/form-data', buffered=True)
    second_response = client.post('/predictions',
                                  data={
                                      'threshold': '0.9',
                                      'model_name': 'current',
                                      'file': (second_image, 'second.jpg'),
                                  },
                                  content_type='multipart/form-data', buffered=True)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_run_id = first_response.get_json()['id']
    second_run_id = second_response.get_json()['id']

    list_response = client.get('/prediction-runs?limit=1&offset=0')
    assert list_response.status_code == 200
    list_json = list_response.get_json()
    assert list_json['limit'] == 1
    assert list_json['offset'] == 0
    assert list_json['has_more'] is True
    assert [run['id'] for run in list_json['prediction_runs']] == [second_run_id]

    next_page_response = client.get('/prediction-runs?limit=1&offset=1')
    assert next_page_response.status_code == 200
    assert [run['id'] for run in next_page_response.get_json()['prediction_runs']] == [first_run_id]

    get_response = client.get(f'/prediction-runs/{first_run_id}')
    assert get_response.status_code == 200
    assert get_response.get_json()['id'] == first_run_id

    missing_response = client.get('/prediction-runs/missing-run')
    assert missing_response.status_code == 404
    assert missing_response.get_json() == {'error': 'Prediction run not found'}


def test_predictions_endpoint_rejects_unknown_model(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/predictions',
                           data={
                               'threshold': '0.9',
                               'model_name': 'unknown-model',
                               'file': (image, 'test.jpg'),
                           },
                           content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Unknown model_name'}


def test_object_detection_rejects_unknown_model(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/object-count',
                           data={
                               'threshold': '0.9',
                               'model_name': 'unknown-model',
                               'file': (image, 'test.jpg'),
                           },
                           content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json() == {'error': 'Unknown model_name'}


def test_object_detection_requires_file(client):
    response = client.post('/object-count', data={'threshold': '0.9'},
                           content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json() == {'error': "Field 'file' is required"}


def test_object_detection_requires_numeric_threshold(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/object-count',
                           data={'threshold': 'abc', 'file': (image, 'test.jpg')},
                           content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json() == {'error': "Field 'threshold' must be a number between 0 and 1"}


def test_object_detection_rejects_threshold_outside_range(client, image_path):
    with open(image_path, 'rb') as f:
        image = io.BytesIO(f.read())

    response = client.post('/object-count',
                           data={'threshold': '1.1', 'file': (image, 'test.jpg')},
                           content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json() == {'error': "Field 'threshold' must be a number between 0 and 1"}


def test_object_detection_rejects_non_image_file(client):
    response = client.post('/object-count',
                           data={'threshold': '0.9', 'file': (io.BytesIO(b'not an image'), 'test.txt')},
                           content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json() == {'error': "Field 'file' must be a valid image"}


def test_debug_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv('FLASK_DEBUG', raising=False)

    assert _is_debug_enabled() is False


def test_debug_can_be_enabled_from_env(monkeypatch):
    monkeypatch.setenv('FLASK_DEBUG', 'true')

    assert _is_debug_enabled() is True
