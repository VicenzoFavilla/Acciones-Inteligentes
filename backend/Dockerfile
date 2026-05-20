# Stage 1: Build
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.10-slim

WORKDIR /app

# Create a non-root user
# Create a non-root user and their home directory
RUN groupadd -r appuser && useradd -r -m -g appuser appuser

# Set up caching directory with proper permissions
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appuser /home/appuser

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser/.local

# Copy application code
COPY . .

# Set permissions
RUN chown -R appuser:appuser /app
USER appuser

# Ensure local bin is in PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]