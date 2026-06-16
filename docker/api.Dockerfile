FROM python:3.12-slim

WORKDIR /app

COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY apps/api/atlas_api /app/apps/api/atlas_api

WORKDIR /app/apps/api
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "atlas_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
