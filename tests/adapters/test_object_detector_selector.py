import pytest

from counter.adapters.object_detector import ConfiguredObjectDetectorSelector, FakeObjectDetector
from counter.domain.models import ModelInfo
from counter.domain.ports import UnknownModelError


def test_returns_detector_for_known_model():
    detector = FakeObjectDetector()
    model_info = ModelInfo('current', 'Current RFCN Model', 'rfcn')
    selector = ConfiguredObjectDetectorSelector({'current': detector}, {'current': model_info})

    assert selector.detector_for('current') is detector


def test_returns_model_info_for_known_model():
    detector = FakeObjectDetector()
    model_info = ModelInfo('current', 'Current RFCN Model', 'rfcn')
    selector = ConfiguredObjectDetectorSelector({'current': detector}, {'current': model_info})

    assert selector.model_info_for('current') == model_info


def test_rejects_unknown_detector_model():
    selector = ConfiguredObjectDetectorSelector({}, {})

    with pytest.raises(UnknownModelError) as error:
        selector.detector_for('unknown-model')

    assert error.value.model_name == 'unknown-model'


def test_rejects_unknown_model_info_model():
    selector = ConfiguredObjectDetectorSelector({}, {})

    with pytest.raises(UnknownModelError) as error:
        selector.model_info_for('unknown-model')

    assert error.value.model_name == 'unknown-model'
