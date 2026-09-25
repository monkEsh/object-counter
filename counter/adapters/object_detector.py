import json
from typing import Dict, List, BinaryIO

import numpy as np
import requests
from PIL import Image

from counter.domain.models import ModelInfo, Prediction, Box
from counter.domain.ports import DetectorUnavailableError, ObjectDetector, ObjectDetectorSelector, UnknownModelError


class FakeObjectDetector(ObjectDetector):
    def predict(self, image: BinaryIO) -> List[Prediction]:
        return [Prediction(class_name='cat',
                           score=0.999190748,
                           box=Box(xmin=0.367288858, ymin=0.278333426,
                                   xmax=0.735821366, ymax=0.6988855)
                           ),
                ]


class ConfiguredObjectDetectorSelector(ObjectDetectorSelector):
    def __init__(self, detectors_by_model_name: Dict[str, ObjectDetector], model_info_by_name: Dict[str, ModelInfo]):
        self.__detectors_by_model_name = detectors_by_model_name
        self.__model_info_by_name = model_info_by_name

    def detector_for(self, model_name: str) -> ObjectDetector:
        try:
            return self.__detectors_by_model_name[model_name]
        except KeyError:
            raise UnknownModelError(model_name)

    def model_info_for(self, model_name: str) -> ModelInfo:
        try:
            return self.__model_info_by_name[model_name]
        except KeyError:
            raise UnknownModelError(model_name)


class TFSObjectDetector(ObjectDetector):
    def __init__(self, host, port, model, label_map='counter/adapters/mscoco_label_map.json', timeout_seconds=5):
        self.url = f"http://{host}:{port}/v1/models/{model}:predict"
        self.timeout_seconds = timeout_seconds
        self.classes_dict = self.__build_classes_dict(label_map)

    def predict(self, image: BinaryIO) -> List[Prediction]:
        np_image = self.__to_np_array(image)
        predict_request = '{"instances" : %s}' % np.expand_dims(np_image, 0).tolist()
        print(f"Sending request to TFS...{self.url}")
        try:
            response = requests.post(self.url, data=predict_request, timeout=self.timeout_seconds)
            response.raise_for_status()
            response_json = response.json()
            predictions = response_json['predictions'][0]
        except requests.RequestException as error:
            raise DetectorUnavailableError("TensorFlow Serving request failed", error)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise DetectorUnavailableError("TensorFlow Serving returned an invalid prediction response", error)
        return self.__raw_predictions_to_domain(predictions)

    @staticmethod
    def __build_classes_dict(label_map):
        with open(label_map) as json_file:
            labels = json.load(json_file)
            return {label['id']: label['display_name'] for label in labels}

    @staticmethod
    def __to_np_array(image: BinaryIO):
        image_ = Image.open(image)
        (im_width, im_height) = image_.size
        return np.array(image_.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)

    def __raw_predictions_to_domain(self, raw_predictions: dict) -> List[Prediction]:
        print("Parsing raw predictions...")
        required_fields = ('num_detections', 'detection_boxes', 'detection_scores', 'detection_classes')
        missing_fields = [field for field in required_fields if field not in raw_predictions]
        if missing_fields:
            raise DetectorUnavailableError(f"TensorFlow Serving response missing fields: {', '.join(missing_fields)}")

        try:
            num_detections = int(raw_predictions.get('num_detections'))
            predictions = []
            for i in range(0, num_detections):
                detection_box = raw_predictions['detection_boxes'][i]
                box = Box(xmin=detection_box[1], ymin=detection_box[0], xmax=detection_box[3], ymax=detection_box[2])
                detection_score = raw_predictions['detection_scores'][i]
                detection_class = raw_predictions['detection_classes'][i]
                class_name = self.classes_dict.get(detection_class, f'class_{detection_class}')
                predictions.append(Prediction(class_name=class_name, score=detection_score, box=box))
        except (ValueError, IndexError, TypeError) as error:
            raise DetectorUnavailableError("TensorFlow Serving returned malformed prediction values", error)
        print(predictions)
        return predictions
