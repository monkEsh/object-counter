import os
import uuid
from io import BytesIO

from flask import Flask, request, jsonify, render_template, send_from_directory
from PIL import Image, UnidentifiedImageError

from counter import config
from counter.debug import draw
from counter.domain.ports import UnknownModelError


class ValidationError(Exception):
    def __init__(self, message):
        self.message = message


def _parse_threshold(raw_threshold):
    try:
        threshold = float(raw_threshold if raw_threshold is not None else 0.5)
    except (TypeError, ValueError):
        raise ValidationError("Field 'threshold' must be a number between 0 and 1")

    if not 0 <= threshold <= 1:
        raise ValidationError("Field 'threshold' must be a number between 0 and 1")

    return threshold


def _parse_model_name(raw_model_name):
    if raw_model_name is None or raw_model_name.strip() == '':
        return config.get_default_model_name()
    return raw_model_name.strip()


def _load_image_file(uploaded_file):
    if uploaded_file is None:
        raise ValidationError("Field 'file' is required")

    if uploaded_file.filename == '':
        raise ValidationError("Field 'file' is required")

    image = BytesIO()
    uploaded_file.save(image)

    try:
        image.seek(0)
        with Image.open(image) as parsed_image:
            parsed_image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("Field 'file' must be a valid image")

    image.seek(0)
    return image


def _is_debug_enabled():
    return os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes', 'on', True, 'True')


def _serialize_model_registry(model_registry):
    return {
        'default_model': model_registry.default_model,
        'models': [
            {
                'name': model_info.name,
                'display_name': model_info.display_name,
                'is_default': model_info.name == model_registry.default_model,
            }
            for model_info in model_registry.models.values()
        ],
    }


def _serialize_prediction(prediction):
    return {
        'class_name': prediction.class_name,
        'score': prediction.score,
        'box': {
            'xmin': prediction.box.xmin,
            'ymin': prediction.box.ymin,
            'xmax': prediction.box.xmax,
            'ymax': prediction.box.ymax,
        },
    }


def _annotated_prediction_image_name(prediction_run_id):
    return f'predictions_{prediction_run_id}.jpg'


def _annotated_prediction_image_path(image_name):
    return f'tmp/debug/{image_name}'


def _annotated_prediction_image_url(image_path):
    return f'/debug-images/{os.path.basename(image_path)}'


def _serialize_prediction_run(prediction_run):
    payload = {
        'id': prediction_run.id,
        'model_name': prediction_run.model_name,
        'threshold': prediction_run.threshold,
        'annotated_image': prediction_run.annotated_image,
        'annotated_image_url': _annotated_prediction_image_url(prediction_run.annotated_image),
        'predictions': [
            _serialize_prediction(prediction)
            for prediction in prediction_run.predictions
        ],
    }
    if prediction_run.created_at:
        payload['created_at'] = prediction_run.created_at
    return payload


def _parse_non_negative_int(raw_value, default, field_name):
    try:
        value = int(raw_value if raw_value is not None else default)
    except (TypeError, ValueError):
        raise ValidationError(f"Field '{field_name}' must be a non-negative integer")

    if value < 0:
        raise ValidationError(f"Field '{field_name}' must be a non-negative integer")

    return value


def _draw_predictions(predictions, image, image_name):
    image.seek(0)
    with Image.open(image) as parsed_image:
        draw(predictions, parsed_image.convert('RGB'), image_name)
    image.seek(0)
    return _annotated_prediction_image_path(image_name)


def create_app():
    app = Flask(__name__)

    count_action = config.get_count_action()
    prediction_action = config.get_prediction_action()

    @app.route('/', methods=['GET'])
    def index():
        return render_template('index.html')

    @app.route('/prediction', methods=['GET'])
    def prediction_page():
        return render_template('prediction.html')

    @app.route('/debug-images/<path:filename>', methods=['GET'])
    def debug_image(filename):
        return send_from_directory(os.path.abspath('tmp/debug'), filename)

    @app.route('/models', methods=['GET'])
    def list_models():
        return jsonify(_serialize_model_registry(config.get_model_registry()))

    @app.route('/prediction-runs', methods=['GET'])
    def list_prediction_runs():
        try:
            limit = _parse_non_negative_int(request.args.get('limit'), 10, 'limit')
            offset = _parse_non_negative_int(request.args.get('offset'), 0, 'offset')
        except ValidationError as error:
            return jsonify({'error': error.message}), 400

        limit = min(limit or 10, 50)
        prediction_runs = prediction_action.list_runs(limit + 1, offset)
        visible_runs = prediction_runs[:limit]
        return jsonify({
            'limit': limit,
            'offset': offset,
            'has_more': len(prediction_runs) > limit,
            'prediction_runs': [_serialize_prediction_run(run) for run in visible_runs],
        })

    @app.route('/prediction-runs/<prediction_run_id>', methods=['GET'])
    def get_prediction_run(prediction_run_id):
        prediction_run = prediction_action.get_run(prediction_run_id)
        if prediction_run is None:
            return jsonify({'error': 'Prediction run not found'}), 404
        return jsonify(_serialize_prediction_run(prediction_run))

    @app.route('/object-count', methods=['POST'])
    def object_detection():
        try:
            threshold = _parse_threshold(request.form.get('threshold'))
            model_name = _parse_model_name(request.form.get('model_name'))
            uploaded_file = request.files.get('file')
            image = _load_image_file(uploaded_file)
        except ValidationError as error:
            return jsonify({'error': error.message}), 400

        try:
            count_response = count_action.execute(image, threshold, model_name)
        except UnknownModelError:
            return jsonify({'error': 'Unknown model_name'}), 400
        return jsonify(count_response)

    @app.route('/predictions', methods=['POST'])
    def predictions():
        try:
            threshold = _parse_threshold(request.form.get('threshold'))
            model_name = _parse_model_name(request.form.get('model_name'))
            uploaded_file = request.files.get('file')
            image = _load_image_file(uploaded_file)
        except ValidationError as error:
            return jsonify({'error': error.message}), 400

        prediction_run_id = str(uuid.uuid4())
        annotated_image_name = _annotated_prediction_image_name(prediction_run_id)
        annotated_image_path = _annotated_prediction_image_path(annotated_image_name)

        try:
            prediction_response = prediction_action.execute(
                image,
                threshold,
                model_name,
                prediction_run_id,
                annotated_image_path,
            )
        except UnknownModelError:
            return jsonify({'error': 'Unknown model_name'}), 400

        _draw_predictions(prediction_response.predictions, image, annotated_image_name)

        return jsonify(_serialize_prediction_run(prediction_response))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run('0.0.0.0', debug=_is_debug_enabled(), port=5001)
