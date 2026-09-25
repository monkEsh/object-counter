from typing import List, Optional

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

from counter.domain.models import Box, ModelInfo, ObjectCount, Prediction, PredictionRun
from counter.domain.ports import ObjectCountRepo, PredictionRunRepo

Base = declarative_base()


class ObjectCountObservation(Base):
    __tablename__ = "object_count_observations"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False, index=True)
    model_display_name = Column(String, nullable=False)
    serving_name = Column(String, nullable=False, index=True)
    object_class = Column(String, nullable=False, index=True)
    count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ObjectPredictionRunRecord(Base):
    __tablename__ = "object_prediction_runs"

    id = Column(String, primary_key=True)
    annotated_image = Column(String, nullable=False)
    model_name = Column(String, nullable=False, index=True)
    predictions = Column(JSON, nullable=False)
    threshold = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


def prediction_to_dict(prediction: Prediction):
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


def prediction_from_dict(raw_prediction):
    box = raw_prediction['box']
    return Prediction(
        class_name=raw_prediction['class_name'],
        score=raw_prediction['score'],
        box=Box(
            xmin=box['xmin'],
            ymin=box['ymin'],
            xmax=box['xmax'],
            ymax=box['ymax'],
        ),
    )


def create_session_factory(database_url: str):
    engine = create_engine(database_url, future=True)
    return sessionmaker(bind=engine, future=True), engine


class CountInMemoryRepo(ObjectCountRepo):
    def __init__(self):
        self.store = dict()

    def read_values(self, model_info: ModelInfo, object_classes: List[str] = None) -> List[ObjectCount]:
        model_store = self.store.get(model_info.name, {})
        if object_classes is None:
            return list(model_store.values())

        return [model_store[object_class] for object_class in object_classes if object_class in model_store]

    def update_values(self, model_info: ModelInfo, new_values: List[ObjectCount]):
        model_store = self.store.setdefault(model_info.name, {})
        for new_object_count in new_values:
            key = new_object_count.object_class
            try:
                stored_object_count = model_store[key]
                model_store[key] = ObjectCount(key, stored_object_count.count + new_object_count.count)
            except KeyError:
                model_store[key] = ObjectCount(key, new_object_count.count)


class PredictionRunInMemoryRepo(PredictionRunRepo):
    def __init__(self):
        self.store = dict()

    def save(self, prediction_run: PredictionRun) -> PredictionRun:
        self.store[prediction_run.id] = prediction_run
        return prediction_run


class CountPostgreSQLRepo(ObjectCountRepo):
    def __init__(self, database_url: Optional[str] = None, session_factory=None):
        if session_factory is None:
            session_factory, _ = create_session_factory(database_url)
        self.__session_factory = session_factory

    def read_values(self, model_info: ModelInfo, object_classes: List[str] = None) -> List[ObjectCount]:
        with self.__session_factory() as session:
            query = (
                session.query(
                    ObjectCountObservation.object_class,
                    func.sum(ObjectCountObservation.count).label("total_count"),
                )
                .filter(ObjectCountObservation.model_name == model_info.name)
                .group_by(ObjectCountObservation.object_class)
            )
            if object_classes:
                query = query.filter(ObjectCountObservation.object_class.in_(object_classes))

            return [
                ObjectCount(object_class, int(total_count))
                for object_class, total_count in query.order_by(ObjectCountObservation.object_class).all()
            ]

    def update_values(self, model_info: ModelInfo, new_values: List[ObjectCount]):
        with self.__session_factory() as session:
            for value in new_values:
                session.add(
                    ObjectCountObservation(
                        model_name=model_info.name,
                        model_display_name=model_info.display_name,
                        serving_name=model_info.serving_name,
                        object_class=value.object_class,
                        count=value.count,
                    )
                )
            session.commit()


class PredictionRunPostgreSQLRepo(PredictionRunRepo):
    def __init__(self, database_url: Optional[str] = None, session_factory=None):
        if session_factory is None:
            session_factory, _ = create_session_factory(database_url)
        self.__session_factory = session_factory

    def save(self, prediction_run: PredictionRun) -> PredictionRun:
        with self.__session_factory() as session:
            session.add(
                ObjectPredictionRunRecord(
                    id=prediction_run.id,
                    annotated_image=prediction_run.annotated_image,
                    model_name=prediction_run.model_name,
                    predictions=[prediction_to_dict(prediction) for prediction in prediction_run.predictions],
                    threshold=prediction_run.threshold,
                )
            )
            session.commit()
        return prediction_run
