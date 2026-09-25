import pytest

from counter.adapters.count_repo import (
    Base,
    CountPostgreSQLRepo,
    ObjectCountObservation,
    create_session_factory,
)
from counter.domain.models import ModelInfo, ObjectCount


@pytest.fixture
def model_info():
    return ModelInfo('current', 'Current RFCN Model', 'rfcn')


@pytest.fixture
def other_model_info():
    return ModelInfo('shelf-detector', 'Shelf Detector', 'internal_shelf_v2')


@pytest.fixture
def repo():
    session_factory, engine = create_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return CountPostgreSQLRepo(session_factory=session_factory)


def test_postgresql_repo_inserts_model_aware_count_observations(repo, model_info):
    repo.update_values(model_info, [ObjectCount("cat", 2), ObjectCount("dog", 1)])

    assert sorted(repo.read_values(model_info), key=lambda value: value.object_class) == [
        ObjectCount("cat", 2),
        ObjectCount("dog", 1),
    ]


def test_postgresql_repo_aggregates_existing_counts_for_same_model(repo, model_info):
    repo.update_values(model_info, [ObjectCount("cat", 2)])
    repo.update_values(model_info, [ObjectCount("cat", 3), ObjectCount("dog", 1)])

    assert sorted(repo.read_values(model_info), key=lambda value: value.object_class) == [
        ObjectCount("cat", 5),
        ObjectCount("dog", 1),
    ]


def test_postgresql_repo_keeps_totals_separate_by_model(repo, model_info, other_model_info):
    repo.update_values(model_info, [ObjectCount("cat", 2)])
    repo.update_values(other_model_info, [ObjectCount("cat", 99)])

    assert repo.read_values(model_info) == [ObjectCount("cat", 2)]
    assert repo.read_values(other_model_info) == [ObjectCount("cat", 99)]


def test_postgresql_repo_filters_by_object_class(repo, model_info):
    repo.update_values(model_info, [ObjectCount("cat", 2), ObjectCount("dog", 1)])

    assert repo.read_values(model_info, ["cat"]) == [ObjectCount("cat", 2)]


def test_object_count_observation_schema_has_model_details():
    column_names = {column.name for column in ObjectCountObservation.__table__.columns}

    assert {
        "id",
        "model_name",
        "model_display_name",
        "serving_name",
        "object_class",
        "count",
        "created_at",
    }.issubset(column_names)
