FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

COPY codebase/ml /app/ml
COPY codebase/detection /app/detection

RUN --mount=type=cache,id=chan-pip,target=/root/.cache/pip \
    python -m pip install /app/ml /app/detection \
    && useradd --create-home --uid 10001 chan

USER chan

EXPOSE 8003

CMD ["chan-detection-api"]
