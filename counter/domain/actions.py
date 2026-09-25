from PIL import Image

from counter.debug import draw
from counter.domain.models import CountResponse, PredictionRun
from counter.domain.ports import ObjectDetectorSelector, ObjectCountRepo, PredictionRunRepo
from counter.domain.predictions import over_threshold, count


class CountDetectedObjects:
    def __init__(self, object_detector_selector: ObjectDetectorSelector, object_count_repo: ObjectCountRepo):
        self.__object_detector_selector = object_detector_selector
        self.__object_count_repo = object_count_repo

    def execute(self, image, threshold, model_name) -> CountResponse:
        model_info = self.__object_detector_selector.model_info_for(model_name)
        predictions = self.__find_valid_predictions(image, threshold, model_name)
        object_counts = count(predictions)
        self.__object_count_repo.update_values(model_info, object_counts)
        total_objects = self.__object_count_repo.read_values(model_info)
        return CountResponse(current_objects=object_counts, total_objects=total_objects)

    def __find_valid_predictions(self, image, threshold, model_name):
        object_detector = self.__object_detector_selector.detector_for(model_name)
        predictions = object_detector.predict(image)
        self.__debug_image(image, predictions, "all_predictions.jpg")
        valid_predictions = list(over_threshold(predictions, threshold=threshold))
        self.__debug_image(image, valid_predictions, f"valid_predictions_with_threshold_{threshold}.jpg")
        return valid_predictions

    @staticmethod
    def __debug_image(image, predictions, image_name):
        if __debug__ and image is not None:
            image = Image.open(image)
            draw(predictions, image, image_name)


class PredictObjects:
    def __init__(self, object_detector_selector: ObjectDetectorSelector, prediction_run_repo: PredictionRunRepo):
        self.__object_detector_selector = object_detector_selector
        self.__prediction_run_repo = prediction_run_repo

    def execute(self, image, threshold, model_name, prediction_run_id, annotated_image):
        model_info = self.__object_detector_selector.model_info_for(model_name)
        object_detector = self.__object_detector_selector.detector_for(model_name)
        predictions = object_detector.predict(image)
        valid_predictions = list(over_threshold(predictions, threshold=threshold))
        return self.__prediction_run_repo.save(
            PredictionRun(
                id=prediction_run_id,
                annotated_image=annotated_image,
                model_name=model_info.name,
                predictions=valid_predictions,
                threshold=threshold,
            )
        )