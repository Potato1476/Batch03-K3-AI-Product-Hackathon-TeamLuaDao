FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY codebase/ml /app/ml
COPY codebase/api /app/training-api

RUN python -m pip install --no-cache-dir /app/ml /app/training-api \
    && useradd --create-home --uid 10001 chan \
    && mkdir -p /var/lib/chan/model-registry /var/lib/chan/datasets \
    && chown -R chan:chan /var/lib/chan

USER chan

EXPOSE 8001

CMD ["chan-training-api"]
