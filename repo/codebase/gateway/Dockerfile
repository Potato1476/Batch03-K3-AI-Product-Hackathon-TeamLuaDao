# Build from the repo/ project root, not from this directory:
#   docker build -f codebase/gateway/Dockerfile -t chan-gateway .
#
# Mirrors codebase/api/Dockerfile so both services are built the same way.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

COPY codebase/ml /app/ml
COPY codebase/gateway /app/gateway
# The Rule Bundle is data the service serves, so it ships inside the image and
# its version is pinned to the build.
COPY codebase/rules /app/rules

RUN --mount=type=cache,id=chan-pip,target=/root/.cache/pip \
    pip install /app/ml /app/gateway

ENV CHAN_RULES_DIR=/app/rules

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin chan

USER chan

EXPOSE 8000

# The public service. The private training control plane is a separate image on
# port 8001 — see codebase/api/Dockerfile.
CMD ["chan-gateway"]
