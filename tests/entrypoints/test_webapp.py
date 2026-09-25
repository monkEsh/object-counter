import io
import json

import pytest

from pathlib import Path
from counter.entrypoints.webapp import create_app


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


def test_object_detection(client, image_path):
    # Load the image from the path resource/boy.jpg
    with open(image_path, 'rb') as f:
        image_data = f.read()
    image = io.BytesIO(image_data)
    
    data = {
        'threshold': '0.9',
        'model_name': 'rfcn',
    }
    data['file'] = (image, 'test.jpg')

    # Make a test request to the object_detection endpoint
    response = client.post('/object-count', data = data,
        content_type='multipart/form-data', buffered=True)

    # Check that the count_action was called with the correct arguments and
    # and status code is correct(Integration test)
    assert response.status_code == 200
    assert json.loads(response.data) != None


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