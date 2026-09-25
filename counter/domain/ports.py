from abc import ABC, abstractmethod
from typing import BinaryIO, List

from counter.domain.models import ModelInfo, Prediction, ObjectCount


class UnknownModelError(ValueError):
    def __init__(self, model_name: str):
        super().__init__(f"Unknown model_name: {model_name}")
        self.model_name = model_name


class ObjectDetector(ABC):
    @abstractmethod
    def predict(self, image: BinaryIO) -> List[Prediction]:
        raise NotImplementedError


class ObjectDetectorSelector(ABC):
    @abstractmethod
    def detector_for(self, model_name: str) -> ObjectDetector:
        raise NotImplementedError

    @abstractmethod
    def model_info_for(self, model_name: str) -> ModelInfo:
        raise NotImplementedError


class ObjectCountRepo(ABC):
    @abstractmethod
    def read_values(self, model_info: ModelInfo, object_classes: List[str] = None) -> List[ObjectCount]:
        raise NotImplementedError

    @abstractmethod
    def update_values(self, model_info: ModelInfo, new_values: List[ObjectCount]):
        raise NotImplementedError
