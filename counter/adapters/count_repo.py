from typing import List, Optional

from sqlalchemy import Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from counter.domain.models import ObjectCount
from counter.domain.ports import ObjectCountRepo

Base = declarative_base()


class ObjectCountRecord(Base):
    __tablename__ = "object_counts"

    id = Column(Integer, primary_key=True)
    object_class = Column(String, nullable=False, unique=True, index=True)
    count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def create_session_factory(database_url: str):
    engine = create_engine(database_url, future=True)
    return sessionmaker(bind=engine, future=True), engine


class CountInMemoryRepo(ObjectCountRepo):

    def __init__(self):
        self.store = dict()

    def read_values(self, object_classes: List[str] = None) -> List[ObjectCount]:
        if object_classes is None:
            return list(self.store.values())

        return [self.store.get(object_class) for object_class in object_classes]

    def update_values(self, new_values: List[ObjectCount]):
        for new_object_count in new_values:
            key = new_object_count.object_class
            try:
                stored_object_count = self.store[key]
                self.store[key] = ObjectCount(key, stored_object_count.count + new_object_count.count)
            except KeyError:
                self.store[key] = ObjectCount(key, new_object_count.count)


class CountPostgreSQLRepo(ObjectCountRepo):

    def __init__(self, database_url: Optional[str] = None, session_factory=None):
        if session_factory is None:
            session_factory, _ = create_session_factory(database_url)
        self.__session_factory = session_factory

    def read_values(self, object_classes: List[str] = None) -> List[ObjectCount]:
        with self.__session_factory() as session:
            query = session.query(ObjectCountRecord)
            if object_classes:
                query = query.filter(ObjectCountRecord.object_class.in_(object_classes))

            return [
                ObjectCount(record.object_class, record.count)
                for record in query.order_by(ObjectCountRecord.object_class).all()
            ]

    def update_values(self, new_values: List[ObjectCount]):
        with self.__session_factory() as session:
            for value in new_values:
                self.__increment_count(session, value)
            session.commit()

    @staticmethod
    def __increment_count(session: Session, value: ObjectCount):
        record = (
            session.query(ObjectCountRecord)
            .filter(ObjectCountRecord.object_class == value.object_class)
            .one_or_none()
        )

        if record is None:
            session.add(ObjectCountRecord(object_class=value.object_class, count=value.count))
            return

        record.count += value.count
