import json

from counter import config
from counter.domain.models import ModelInfo


def test_load_model_registry_from_json_file(tmp_path):
    registry_path = tmp_path / 'models.json'
    registry_path.write_text(json.dumps({
        'default_model': 'current',
        'models': {
            'current': {
                'display_name': 'Current RFCN Model',
                'serving_name': 'rfcn',
            },
            'people-counter': {
                'display_name': 'People Counter',
                'serving_name': 'internal_people_v3',
            },
        },
    }))

    registry = config.load_model_registry(str(registry_path))

    assert registry.default_model == 'current'
    assert registry.models['current'] == ModelInfo('current', 'Current RFCN Model', 'rfcn')
    assert registry.models['people-counter'] == ModelInfo('people-counter', 'People Counter', 'internal_people_v3')


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


def test_dev_count_action_wires_fake_detector_selector(monkeypatch):
    monkeypatch.setenv('MODEL_NAMES', 'current,people-counter')
    monkeypatch.setenv('DEFAULT_MODEL', 'current')

    action = config.dev_count_action()

    assert action is not None


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


def test_get_default_model_name_prefers_env_override(monkeypatch):
    monkeypatch.setenv('ENV', 'prod')
    monkeypatch.setenv('DEFAULT_MODEL', 'current')

    assert config.get_default_model_name() == 'current'


def test_default_model_registry_path_is_packaged():
    registry = config.load_model_registry(config.DEFAULT_MODEL_REGISTRY_PATH)

    assert registry.default_model == 'current'
    assert registry.models['current'] == ModelInfo('current', 'Current RFCN Model', 'rfcn')
