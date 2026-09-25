import json
import os
from dataclasses import dataclass
from typing import Dict

from counter.adapters.count_repo import CountInMemoryRepo, CountPostgreSQLRepo
from counter.adapters.object_detector import ConfiguredObjectDetectorSelector, TFSObjectDetector, FakeObjectDetector
from counter.domain.actions import CountDetectedObjects
from counter.domain.models import ModelInfo


DEFAULT_DEV_MODELS = ('current', 'people-counter', 'shelf-detector')
DEFAULT_MODEL = 'current'
DEFAULT_MODEL_REGISTRY_PATH = 'resources/model_registry.json'


@dataclass(frozen=True)
class ModelRegistry:
    default_model: str
    models: Dict[str, ModelInfo]


def load_model_registry(registry_path: str) -> ModelRegistry:
    with open(registry_path) as registry_file:
        registry = json.load(registry_file)

    default_model = registry.get('default_model')
    if not default_model:
        raise ValueError("Model registry must define default_model")

    raw_models = registry.get('models')
    if not isinstance(raw_models, dict):
        raise ValueError("Model registry must contain a 'models' object")

    models = {}
    for model_name, model_config in raw_models.items():
        if not isinstance(model_config, dict) or not model_config.get('serving_name'):
            raise ValueError(f"Model '{model_name}' must define a serving_name")
        models[model_name] = ModelInfo(
            name=model_name,
            display_name=model_config.get('display_name', model_name),
            serving_name=model_config['serving_name'],
        )

    if default_model not in models:
        raise ValueError("default_model must exist in models")

    return ModelRegistry(default_model=default_model, models=models)


def _dev_model_names():
    raw_model_names = os.environ.get('MODEL_NAMES')
    if raw_model_names:
        return tuple(model_name.strip() for model_name in raw_model_names.split(',') if model_name.strip())
    return DEFAULT_DEV_MODELS


def dev_count_action() -> CountDetectedObjects:
    fake_detector = FakeObjectDetector()
    model_names = _dev_model_names()
    model_info_by_name = {
        model_name: ModelInfo(model_name, model_name, model_name)
        for model_name in model_names
    }
    selector = ConfiguredObjectDetectorSelector(
        {model_name: fake_detector for model_name in model_names},
        model_info_by_name,
    )
    return CountDetectedObjects(selector, CountInMemoryRepo())


def prod_count_action() -> CountDetectedObjects:
    tfs_host = os.environ.get('TFS_HOST', 'localhost')
    tfs_port = int(os.environ.get('TFS_PORT', 8501))
    database_url = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://object_counter:object_counter@localhost:5432/object_counter',
    )
    registry_path = os.environ.get('MODEL_REGISTRY_PATH', DEFAULT_MODEL_REGISTRY_PATH)
    model_registry = load_model_registry(registry_path)
    selector = ConfiguredObjectDetectorSelector(
        {
            model_name: TFSObjectDetector(tfs_host, tfs_port, model_info.serving_name)
            for model_name, model_info in model_registry.models.items()
        },
        model_registry.models,
    )
    return CountDetectedObjects(selector, CountPostgreSQLRepo(database_url=database_url))


def get_default_model_name() -> str:
    configured_default = os.environ.get('DEFAULT_MODEL')
    if configured_default:
        return configured_default

    if os.environ.get('ENV') == 'prod':
        registry_path = os.environ.get('MODEL_REGISTRY_PATH', DEFAULT_MODEL_REGISTRY_PATH)
        return load_model_registry(registry_path).default_model

    return DEFAULT_MODEL


def get_count_action() -> CountDetectedObjects:
    env = os.environ.get('ENV', 'dev')
    count_action_fn = f"{env}_count_action"
    return globals()[count_action_fn]()
