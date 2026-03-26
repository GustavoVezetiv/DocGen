# Dockerfile - DocGen API
# Multi-stage build para otimizar tamanho da imagem

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (WeasyPrint needs some system packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    fontconfig \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Add local pip packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY main.py .
COPY requirements.txt .

# Create non-root user
RUN useradd -m -u 1000 docgen && chown -R docgen:docgen /app
USER docgen

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
