from unittest.mock import Mock

import pytest

from counter.domain.actions import CountDetectedObjects
from counter.domain.models import ModelInfo, ObjectCount
from counter.domain.ports import UnknownModelError
from tests.domain.helpers import generate_prediction


class TestCountDetectedObjects:
    @pytest.fixture
    def object_detector(self) -> Mock:
        object_detector = Mock()
        object_detector.predict.return_value = [
            generate_prediction('cat', 0.9),
            generate_prediction('cat', 0.8),
            generate_prediction('dog', 0.8),
            generate_prediction('dog', 0.1),
            generate_prediction('rabbit', 0.9),
        ]
        return object_detector

    @pytest.fixture
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            name='current',
            display_name='Current RFCN Model',
            serving_name='rfcn',
        )

    @pytest.fixture
    def object_detector_selector(self, object_detector, model_info) -> Mock:
        selector = Mock()
        selector.detector_for.return_value = object_detector
        selector.model_info_for.return_value = model_info
        return selector

    @pytest.fixture
    def count_object_repo(self) -> Mock:
        repo = Mock()
        repo.read_values.return_value = []
        return repo

    def test_count_valid_predictions(self, object_detector_selector, count_object_repo, model_info) -> None:
        response = CountDetectedObjects(object_detector_selector, count_object_repo).execute(None, 0.5, 'current')

        assert sorted(response.current_objects, key=lambda x: x.object_class) == [
            ObjectCount('cat', 2),
            ObjectCount('dog', 1),
            ObjectCount('rabbit', 1),
        ]
        count_object_repo.read_values.assert_called_once_with(model_info)

    def test_selects_detector_and_model_details_by_model_name(self, object_detector_selector, count_object_repo, model_info):
        CountDetectedObjects(object_detector_selector, count_object_repo).execute(None, 0, 'current')

        object_detector_selector.detector_for.assert_called_once_with('current')
        object_detector_selector.model_info_for.assert_called_once_with('current')
        count_object_repo.update_values.assert_called_once_with(
            model_info,
            [ObjectCount('cat', 2), ObjectCount('dog', 2), ObjectCount('rabbit', 1)],
        )

    def test_rejects_unknown_model(self, object_detector_selector, count_object_repo):
        object_detector_selector.detector_for.side_effect = UnknownModelError('unknown-model')

        with pytest.raises(UnknownModelError):
            CountDetectedObjects(object_detector_selector, count_object_repo).execute(None, 0, 'unknown-model')

        count_object_repo.update_values.assert_not_called()
