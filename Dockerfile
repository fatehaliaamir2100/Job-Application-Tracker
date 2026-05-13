FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY run.py .

# Data directory for SQLite DB, credentials, and token
RUN mkdir -p /data

# Default env — overridden by docker-compose or -e flags
ENV DATABASE_URL=sqlite:////data/job_tracker.db \
    GMAIL_CREDENTIALS_FILE=/data/credentials.json \
    GMAIL_TOKEN_FILE=/data/token.json \
    OLLAMA_BASE_URL=http://ollama:11434 \
    OLLAMA_MODEL=qwen2.5:1.5b \
    SYNC_INTERVAL_MINUTES=60 \
    MAX_EMAILS_PER_SYNC=50 \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

CMD ["python", "run.py"]
