import io
import json

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
