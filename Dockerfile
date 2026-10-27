FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN python -m pip install -r requirements.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY --chown=10001:10001 app/ ./app/
COPY --chown=10001:10001 main.py ./main.py
COPY --chown=10001:10001 data/dataset.csv data/templates.json ./data/
COPY --chown=10001:10001 data/unit_conversion/unit_catalog.json ./data/unit_conversion/unit_catalog.json
COPY --chown=10001:10001 models/template_model.joblib models/vectorizer.joblib ./models/

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).close(); urllib.request.urlopen('http://127.0.0.1:8000/api/v1/telemetry/health', timeout=2).close()"]

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-graceful-shutdown", "30"]
