FROM python:3.9-slim

# Install system deps including ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Environment: require ffmpeg by default in container
ENV VIDEO_REQUIRE_FFMPEG=true

# Default command: run orchestrator (override in Cloud Run if you want HTTP server)
CMD ["python", "-m", "src.main"]
