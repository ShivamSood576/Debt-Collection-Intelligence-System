# Contract Analysis API - Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY last_phase_app_api.py .
COPY test_streaming.py .
COPY test_streaming.html .

# Create necessary directories
RUN mkdir -p /app/chroma_store /app/uploaded_contracts /app/contract_metadata

# Expose port
EXPOSE 8000

# Environment variables (override with -e flag or docker-compose)
ENV OPENAI_API_KEY=""
ENV CHROMA_DIR="/app/chroma_store"
ENV UPLOAD_DIR="/app/uploaded_contracts"
ENV METADATA_DIR="/app/contract_metadata"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
CMD ["uvicorn", "last_phase_app_api:app", "--host", "0.0.0.0", "--port", "8000"]
