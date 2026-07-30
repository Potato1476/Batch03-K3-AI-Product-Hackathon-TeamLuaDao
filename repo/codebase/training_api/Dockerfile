FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

COPY codebase/ml /app/ml
COPY codebase/api /app/training-api

RUN --mount=type=cache,id=chan-pip,target=/root/.cache/pip \
    python -m pip install /app/ml /app/training-api \
    && useradd --create-home --uid 10001 chan \
    && mkdir -p /var/lib/chan/model-registry /var/lib/chan/datasets \
    && chown -R chan:chan /var/lib/chan

USER chan

EXPOSE 8001

CMD ["chan-training-api"]
