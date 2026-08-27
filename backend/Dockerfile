# ==========================================
# Multi-Stage Optimized Dockerfile for ML & Backend
# ==========================================

# Stage 1: Build & Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python packages into isolated user local directory
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Final Production Runtime
FROM python:3.11-slim AS runner

WORKDIR /app

# Security: Create non-root system user and home
RUN groupadd -r appuser && useradd -r -m -g appuser -u 1001 appuser

# Create necessary app directories with proper permissions
RUN mkdir -p /app/models /app/reports /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appuser . .

USER appuser

# Environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MODEL_DIR=/app/models

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]