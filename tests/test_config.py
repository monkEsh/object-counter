import json

from counter import config
from counter.domain.models import ModelInfo


def test_load_model_registry_from_json_file(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'count-current',
        'default_count_model': 'count-current',
        'default_prediction_model': 'prediction-current',
        'models': {
            'count-current': {
                'display_name': 'Current RFCN Count Model',
                'serving_name': 'rfcn',
                'framework': 'tensorflow-serving',
                'label_map': 'custom-labels.json',
                'output_schema': 'tensorflow-object-detection-api-v1',
            },
            'prediction-current': {
                'display_name': 'Current RFCN Prediction Model',
                'serving_name': 'rfcn',
            },
            'people-counter': {
                'display_name': 'People Counter',
                'serving_name': 'internal_people_v3',
            },
        },
    }))

    registry = config.load_model_registry(str(registry_path))

    assert registry.default_model == 'count-current'
    assert registry.default_count_model == 'count-current'
    assert registry.default_prediction_model == 'prediction-current'
    assert registry.models['count-current'] == ModelInfo(
        'count-current',
        'Current RFCN Count Model',
        'rfcn',
        framework='tensorflow-serving',
        label_map='custom-labels.json',
        output_schema='tensorflow-object-detection-api-v1',
    )
    assert registry.models['prediction-current'] == ModelInfo(
        'prediction-current',
        'Current RFCN Prediction Model',
        'rfcn',
    )
    assert registry.models['people-counter'] == ModelInfo('people-counter', 'People Counter', 'internal_people_v3')


def test_load_model_registry_rejects_unsupported_framework(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'current',
        'models': {
            'current': {
                'display_name': 'Current PyTorch Model',
                'serving_name': 'torch_people_v1',
                'framework': 'torchserve',
            },
        },
    }))

    try:
        config.load_model_registry(str(registry_path))
    except ValueError as error:
        assert "unsupported framework 'torchserve'" in str(error)
    else:
        raise AssertionError('expected ValueError')


def test_load_model_registry_rejects_missing_default_model(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({'models': {}}))

    try:
        config.load_model_registry(str(registry_path))
    except ValueError as error:
        assert str(error) == "Model registry must define default_model"
    else:
        raise AssertionError('expected ValueError')


def test_load_model_registry_rejects_default_model_not_in_models(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'missing',
        'models': {
            'current': {'display_name': 'Current RFCN Model', 'serving_name': 'rfcn'},
        },
    }))

    try:
        config.load_model_registry(str(registry_path))
    except ValueError as error:
        assert str(error) == "default_model must exist in models"
    else:
        raise AssertionError('expected ValueError')


def test_load_model_registry_rejects_default_count_model_not_in_models(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'current',
        'default_count_model': 'missing',
        'models': {
            'current': {'display_name': 'Current RFCN Model', 'serving_name': 'rfcn'},
        },
    }))

    try:
        config.load_model_registry(str(registry_path))
    except ValueError as error:
        assert str(error) == "default_count_model must exist in models"
    else:
        raise AssertionError('expected ValueError')


def test_load_model_registry_rejects_default_prediction_model_not_in_models(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'current',
        'default_prediction_model': 'missing',
        'models': {
            'current': {'display_name': 'Current RFCN Model', 'serving_name': 'rfcn'},
        },
    }))

    try:
        config.load_model_registry(str(registry_path))
    except ValueError as error:
        assert str(error) == "default_prediction_model must exist in models"
    else:
        raise AssertionError('expected ValueError')


def test_dev_count_action_wires_fake_detector_selector(monkeypatch):
    monkeypatch.setenv('MODEL_NAMES', 'count-current,prediction-current')
    monkeypatch.setenv('DEFAULT_MODEL', 'count-current')

    action = config.dev_count_action()

    assert action is not None


def test_dev_model_registry_uses_available_model_aliases(monkeypatch):
    monkeypatch.delenv('ENV', raising=False)
    monkeypatch.setenv('MODEL_NAMES', 'count-current,prediction-current,people-counter')
    monkeypatch.setenv('DEFAULT_MODEL', 'people-counter')

    registry = config.get_model_registry()

    assert registry.default_model == 'people-counter'
    assert list(registry.models) == ['count-current', 'prediction-current', 'people-counter']
    assert registry.models['people-counter'] == ModelInfo('people-counter', 'people-counter', 'people-counter')


def test_dev_model_registry_falls_back_when_configured_default_is_unknown(monkeypatch):
    monkeypatch.delenv('ENV', raising=False)
    monkeypatch.setenv('MODEL_NAMES', 'count-current,people-counter')
    monkeypatch.setenv('DEFAULT_MODEL', 'missing')

    registry = config.get_model_registry()

    assert registry.default_model == 'count-current'


def test_dev_model_registry_uses_separate_count_and_prediction_defaults(monkeypatch):
    monkeypatch.delenv('ENV', raising=False)
    monkeypatch.setenv('MODEL_NAMES', 'count-current,prediction-current')
    monkeypatch.setenv('DEFAULT_COUNT_MODEL', 'count-current')
    monkeypatch.setenv('DEFAULT_PREDICTION_MODEL', 'prediction-current')

    registry = config.get_model_registry()

    assert registry.default_count_model == 'count-current'
    assert registry.default_prediction_model == 'prediction-current'


def test_get_default_model_name_uses_registry_in_prod_without_env_override(tmp_path, monkeypatch):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'people-counter',
        'models': {
            'people-counter': {'display_name': 'People Counter', 'serving_name': 'internal_people_v3'},
        },
    }))
    monkeypatch.setenv('ENV', 'prod')
    monkeypatch.setenv('MODEL_REGISTRY_PATH', str(registry_path))
    monkeypatch.delenv('DEFAULT_MODEL', raising=False)

    assert config.get_default_model_name() == 'people-counter'


def test_use_case_default_model_names_use_registry_in_prod(tmp_path, monkeypatch):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'count-current',
        'default_count_model': 'count-current',
        'default_prediction_model': 'prediction-current',
        'models': {
            'count-current': {'display_name': 'Count Model', 'serving_name': 'rfcn'},
            'prediction-current': {'display_name': 'Prediction Model', 'serving_name': 'rfcn'},
        },
    }))
    monkeypatch.setenv('ENV', 'prod')
    monkeypatch.setenv('MODEL_REGISTRY_PATH', str(registry_path))
    monkeypatch.delenv('DEFAULT_MODEL', raising=False)
    monkeypatch.delenv('DEFAULT_COUNT_MODEL', raising=False)
    monkeypatch.delenv('DEFAULT_PREDICTION_MODEL', raising=False)

    assert config.get_default_count_model_name() == 'count-current'
    assert config.get_default_prediction_model_name() == 'prediction-current'


def test_get_default_model_name_prefers_env_override(monkeypatch):
    monkeypatch.setenv('ENV', 'prod')
    monkeypatch.setenv('DEFAULT_MODEL', 'count-current')

    assert config.get_default_model_name() == 'count-current'


def test_default_model_registry_path_is_packaged():
    registry = config.load_model_registry(config.DEFAULT_MODEL_REGISTRY_PATH)

    assert registry.default_model == 'count-current'
    assert registry.default_count_model == 'count-current'
    assert registry.default_prediction_model == 'prediction-current'
    assert registry.models['count-current'] == ModelInfo('count-current', 'Current RFCN Count Model', 'rfcn')
    assert registry.models['prediction-current'] == ModelInfo('prediction-current', 'Current RFCN Prediction Model', 'rfcn')
