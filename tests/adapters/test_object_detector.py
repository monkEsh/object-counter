import io
import json
from unittest.mock import Mock

import pytest
import requests
from PIL import Image

from counter.adapters.object_detector import TFSObjectDetector
from counter.domain.models import Box, Prediction
from counter.domain.ports import DetectorUnavailableError


def _image_bytes():
    image = Image.new('RGB', (1, 1), color='white')
    payload = io.BytesIO()
    image.save(payload, format='JPEG')
    payload.seek(0)
    return payload


def _label_map(tmp_path):
    label_map = tmp_path / 'labels.json'
    label_map.write_text(json.dumps([
        {'id': 1.0, 'display_name': 'person'},
        {'id': 2.0, 'display_name': 'cat'},
    ]))
    return str(label_map)


def test_tfs_detector_posts_with_timeout_and_parses_predictions(tmp_path, monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        'predictions': [
            {
                'num_detections': 1,
                'detection_boxes': [[0.1, 0.2, 0.3, 0.4]],
                'detection_scores': [0.95],
                'detection_classes': [1.0],
            }
        ]
    }
    post = Mock(return_value=response)
    monkeypatch.setattr('counter.adapters.object_detector.requests.post', post)

    detector = TFSObjectDetector('tfserving', 8501, 'rfcn', label_map=_label_map(tmp_path), timeout_seconds=3)

    predictions = detector.predict(_image_bytes())

    assert predictions == [
        Prediction(class_name='person', score=0.95, box=Box(xmin=0.2, ymin=0.1, xmax=0.4, ymax=0.3))
    ]
    post.assert_called_once()
    assert post.call_args.kwargs['timeout'] == 3
    assert post.call_args.args[0] == 'http://tfserving:8501/v1/models/rfcn:predict'


def test_tfs_detector_wraps_request_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(
        'counter.adapters.object_detector.requests.post',
        Mock(side_effect=requests.Timeout('timeout')),
    )
    detector = TFSObjectDetector('tfserving', 8501, 'rfcn', label_map=_label_map(tmp_path))

    with pytest.raises(DetectorUnavailableError, match='TensorFlow Serving request failed'):
        detector.predict(_image_bytes())


def test_tfs_detector_rejects_malformed_prediction_response(tmp_path, monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {'predictions': [{}]}
    monkeypatch.setattr('counter.adapters.object_detector.requests.post', Mock(return_value=response))
    detector = TFSObjectDetector('tfserving', 8501, 'rfcn', label_map=_label_map(tmp_path))

    with pytest.raises(DetectorUnavailableError, match='missing fields'):
        detector.predict(_image_bytes())
