FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY codebase/ml /app/ml
COPY codebase/detection /app/detection

RUN python -m pip install --no-cache-dir /app/ml \
    && python -m pip install --no-cache-dir /app/detection \
    && useradd --create-home --uid 10001 chan

USER chan

EXPOSE 8003

CMD ["chan-detection-api"]
