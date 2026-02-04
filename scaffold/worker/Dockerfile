FROM python:3.11-slim
WORKDIR /app

# Install OS deps for ffmpeg if desired; keep minimal for scaffold
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy repo and install Python deps (use top-level requirements.txt)
COPY . /app
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt || true
# Ensure redis client is available
RUN pip install redis

ENV PYTHONUNBUFFERED=1

CMD ["python", "scaffold/worker/worker.py"]
