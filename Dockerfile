FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY dashboard/ ./dashboard/
COPY model/artifacts/shap_importance.parquet ./model/artifacts/

ENV PORT=8000
CMD uvicorn dashboard.api:app --host 0.0.0.0 --port $PORT