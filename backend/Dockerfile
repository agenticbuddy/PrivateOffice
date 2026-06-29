# Multi-stage: build Vue SPA, then bundle into the Python backend image.
# The app container serves both the API (/api, /wopi) and the built SPA (/).

# ---- Stage 1: build frontend ----
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: python backend ----
FROM python:3.12-slim AS backend
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY backend/ ./
COPY --from=frontend /fe/dist /app/static

ENV PYTHONPATH=/app/backend STATIC_DIR=/app/static
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
