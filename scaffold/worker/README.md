# Worker

This folder contains a minimal Python worker that polls Redis (list `ai_jobs`) and runs the Python orchestrator in `src/`.

Build and run (local Docker, example):

1. Build the image:

```bash
docker build -t ai-orchestrator-worker -f scaffold/worker/Dockerfile .
```

2. Run Redis locally (if you don't have one):

```bash
docker run -p 6379:6379 -d redis:7
```

3. Run the worker image (it expects `REDIS_URL` if not on default localhost):

```bash
docker run -e REDIS_URL=redis://host.docker.internal:6379 ai-orchestrator-worker
```

How it works
- Backend enqueues jobs to the `ai_jobs` list in Redis when `REDIS_URL` is set.
- Worker BLPOP's that list and runs `python -m src.main` for each job. By default the worker runs in dry-run mode; set `DRY_RUN=false` in the environment to run real API calls (be careful).

Local development (no Docker)
--------------------------------

If you're developing locally and the project has a `.venv` (created by `python3 -m venv .venv`), you can use the helper script at `scripts/start-worker.sh` to activate the venv, install missing Python deps, and start the worker:

```bash
# From project root
source .venv/bin/activate  # or just run scripts/start-worker.sh
scripts/start-worker.sh
```

Or run it explicitly with a specific Redis URL:

```bash
REDIS_URL=redis://localhost:6379 scripts/start-worker.sh
```

This script will ensure `redis` Python package is installed and then exec the worker process so logs appear directly in your terminal.
