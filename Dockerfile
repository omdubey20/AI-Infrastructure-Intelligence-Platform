# Multi-Stage Production Dockerfile for Railway Deployment
# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
ENV CI=false
RUN npm run build

# Stage 2: Python FastAPI Backend & Unified Server
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend application code
COPY backend/ ./backend/

# Copy built frontend from Stage 1 into frontend/build
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Copy root delegation proxy
COPY main.py ./main.py

# Create unprivileged system user for enterprise least-privilege compliance
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Set working directory to backend for execution
WORKDIR /app/backend
USER appuser

# Environment defaults
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend:/app

EXPOSE 8000

# Healthcheck for container orchestrators (Docker Swarm / Kubernetes / Railway)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start Uvicorn server on $PORT provided dynamically by Railway
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
