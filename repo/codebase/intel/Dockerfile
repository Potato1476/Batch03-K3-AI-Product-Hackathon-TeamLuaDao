FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY codebase/intel /app/intel

RUN python -m pip install --no-cache-dir /app/intel \
    && useradd --create-home --uid 10002 chan

USER chan

EXPOSE 8002

CMD ["chan-intel-api"]
