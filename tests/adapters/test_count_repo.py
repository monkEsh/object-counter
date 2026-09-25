import pytest

from counter.adapters.count_repo import (
    Base,
    CountPostgreSQLRepo,
    ObjectCountRecord,
    create_session_factory,
)
from counter.domain.models import ObjectCount


@pytest.fixture
def repo():
    session_factory, engine = create_session_factory("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return CountPostgreSQLRepo(session_factory=session_factory)


def test_postgresql_repo_inserts_new_counts(repo):
    repo.update_values([ObjectCount("cat", 2), ObjectCount("dog", 1)])

    assert sorted(repo.read_values(), key=lambda value: value.object_class) == [
        ObjectCount("cat", 2),
        ObjectCount("dog", 1),
    ]


def test_postgresql_repo_increments_existing_counts(repo):
    repo.update_values([ObjectCount("cat", 2)])
    repo.update_values([ObjectCount("cat", 3), ObjectCount("dog", 1)])

    assert sorted(repo.read_values(), key=lambda value: value.object_class) == [
        ObjectCount("cat", 5),
        ObjectCount("dog", 1),
    ]


def test_postgresql_repo_filters_by_object_class(repo):
    repo.update_values([ObjectCount("cat", 2), ObjectCount("dog", 1)])

    assert repo.read_values(["cat"]) == [ObjectCount("cat", 2)]


def test_object_count_record_schema_has_versioning_fields():
    column_names = {column.name for column in ObjectCountRecord.__table__.columns}

    assert {"id", "object_class", "count", "created_at", "updated_at"}.issubset(column_names)
