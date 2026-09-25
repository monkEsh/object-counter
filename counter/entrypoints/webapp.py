import os
from io import BytesIO

from flask import Flask, request, jsonify, render_template
from PIL import Image, UnidentifiedImageError

from counter import config
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


def create_app():
    app = Flask(__name__)

    count_action = config.get_count_action()

    @app.route('/', methods=['GET'])
    def index():
        return render_template('index.html')

    @app.route('/models', methods=['GET'])
    def list_models():
        return jsonify(_serialize_model_registry(config.get_model_registry()))

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

    return app


if __name__ == '__main__':
    app = create_app()
    app.run('0.0.0.0', debug=_is_debug_enabled(), port=5001)
