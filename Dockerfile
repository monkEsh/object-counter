FROM python:3.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

COPY counter ./counter
COPY resources ./resources
COPY alembic.ini .
COPY migrations ./migrations

EXPOSE 5001

CMD ["sh", "-c", "alembic upgrade head && python -m counter.entrypoints.webapp"]
