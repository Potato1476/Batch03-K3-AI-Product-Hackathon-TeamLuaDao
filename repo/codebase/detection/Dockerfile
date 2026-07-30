FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHAN_MODEL_PATH=/opt/chan/models/chan-signal-model.joblib \
    CHAN_MODEL_SHA256=44a885db58d96d3b9dcd378504f9b329643fbfbd05518c8b146542fbd07e8445 \
    CHAN_MODEL_VERSION=chan-signal-20260730

WORKDIR /app

COPY codebase/ml /app/ml
COPY codebase/detection /app/detection

RUN python -m pip install --no-cache-dir /app/ml \
    && python -m pip install --no-cache-dir /app/detection \
    && useradd --create-home --uid 10001 chan \
    && mkdir -p /opt/chan/models \
    && cp /app/ml/artifacts/chan-signal-model.joblib /opt/chan/models/ \
    && chown -R chan:chan /opt/chan

USER chan

EXPOSE 8000

CMD ["chan-detection-api"]
