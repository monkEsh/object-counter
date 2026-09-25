import os

from counter.adapters.count_repo import CountInMemoryRepo, CountPostgreSQLRepo
from counter.adapters.object_detector import TFSObjectDetector, FakeObjectDetector
from counter.domain.actions import CountDetectedObjects


def dev_count_action() -> CountDetectedObjects:
    return CountDetectedObjects(FakeObjectDetector(), CountInMemoryRepo())


def prod_count_action() -> CountDetectedObjects:
    tfs_host = os.environ.get('TFS_HOST', 'localhost')
    tfs_port = int(os.environ.get('TFS_PORT', 8501))
    database_url = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://object_counter:object_counter@localhost:5432/object_counter',
    )
    return CountDetectedObjects(TFSObjectDetector(tfs_host, tfs_port, 'rfcn'),
                                CountPostgreSQLRepo(database_url=database_url))


def get_count_action() -> CountDetectedObjects:
    env = os.environ.get('ENV', 'dev')
    count_action_fn = f"{env}_count_action"
    return globals()[count_action_fn]()
