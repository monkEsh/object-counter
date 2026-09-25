import pytest

from counter.adapters.count_repo import (
    Base,
    CountPostgreSQLRepo,
    ObjectCountObservation,
    ObjectPredictionRunRecord,
    PredictionRunPostgreSQLRepo,
    create_session_factory,
)
from counter.domain.models import ModelInfo, ObjectCount, PredictionRun
from tests.domain.helpers import generate_prediction


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


def test_prediction_run_repo_inserts_prediction_run(repo, model_info):
    session_factory = repo._CountPostgreSQLRepo__session_factory
    prediction_repo = PredictionRunPostgreSQLRepo(session_factory=session_factory)
    prediction_run = PredictionRun(
        id='prediction-id',
        annotated_image='tmp/debug/predictions_prediction-id.jpg',
        model_name=model_info.name,
        predictions=[generate_prediction('cat', 0.9)],
        threshold=0.5,
    )

    assert prediction_repo.save(prediction_run) == prediction_run

    with session_factory() as session:
        stored_run = session.query(ObjectPredictionRunRecord).one()

    assert stored_run.id == 'prediction-id'
    assert stored_run.annotated_image == 'tmp/debug/predictions_prediction-id.jpg'
    assert stored_run.model_name == 'current'
    assert stored_run.threshold == 0.5
    assert stored_run.predictions == [
        {
            'class_name': 'cat',
            'score': 0.9,
            'box': {
                'xmin': 0,
                'ymin': 0,
                'xmax': 0,
                'ymax': 0,
            },
        },
    ]


def test_prediction_run_repo_lists_and_gets_prediction_runs(repo, model_info):
    session_factory = repo._CountPostgreSQLRepo__session_factory
    prediction_repo = PredictionRunPostgreSQLRepo(session_factory=session_factory)
    first_run = PredictionRun(
        id='first-run',
        annotated_image='tmp/debug/predictions_first-run.jpg',
        model_name=model_info.name,
        predictions=[generate_prediction('cat', 0.9)],
        threshold=0.5,
    )
    second_run = PredictionRun(
        id='second-run',
        annotated_image='tmp/debug/predictions_second-run.jpg',
        model_name=model_info.name,
        predictions=[generate_prediction('dog', 0.8)],
        threshold=0.7,
    )

    prediction_repo.save(first_run)
    prediction_repo.save(second_run)

    stored_runs = prediction_repo.list(limit=10, offset=0)
    assert [run.id for run in stored_runs] == ['second-run', 'first-run']
    assert stored_runs[0].created_at is not None
    assert prediction_repo.get('first-run').id == 'first-run'
    assert prediction_repo.get('missing-run') is None


def test_object_prediction_run_schema_has_required_fields():
    column_names = {column.name for column in ObjectPredictionRunRecord.__table__.columns}

    assert {
        "id",
        "annotated_image",
        "model_name",
        "predictions",
        "threshold",
        "created_at",
    }.issubset(column_names)
