# Docker Hub index bytes and Docker-Content-Digest verified 2026-10-25.
FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=UTC PIP_NO_CACHE_DIR=1
WORKDIR /quality
# Build context is tests/. Tests and the frozen contract are mounted read-only in T022.
COPY requirements.lock /tmp/quality-requirements.lock
RUN python -m pip install --require-hashes -r /tmp/quality-requirements.lock
USER 65532:65532
# No app sources, Docker CLI/socket, host lifecycle, secrets or browser storage in this image.
CMD ["python", "-m", "pytest", "-c", "/quality/pytest.ini", "/quality/contract"]
