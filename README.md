# AI Content Orchestrator (sample)

This repository contains a minimal, modular Python sample that demonstrates how to orchestrate AI-driven content creation (concept -> image -> video -> caption) and post the result to Instagram. It's designed as a starting point: each integration is a small client you can replace with real API calls.

Features
- Modular clients for: Gemini (prompt + caption), Image generation, Video generation, Instagram posting
- Dry-run mode so you can test locally without calling external APIs
- Example test to validate the orchestrator flow

Quick start
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your API keys / IDs. If you have Gemini Pro, set `GEMINI_API_KEY` and `GEMINI_API_URL` to your endpoint. Example options:

- Use a hosted proxy or the vendor endpoint that accepts a JSON payload with keys `model` and `instruction`. Set `GEMINI_API_URL` to that URL.
- If you prefer an SDK-backed approach, you can still use this client by running a small proxy that converts SDK calls into the same JSON contract.

3. Run the orchestrator in dry-run mode:

```bash
python -m src.main
```

4. To run the tests:

```bash
pytest -q
```

- Notes
- This sample uses a simple, configurable HTTP contract for the Gemini client. When `dry_run=false` the `GeminiClient` will POST JSON {"model": <model>, "instruction": <text>} to the `GEMINI_API_URL` with a Bearer token from `GEMINI_API_KEY`. The client expects either a JSON response or textual output that contains a JSON snippet.
- If you have Gemini Pro, set `GEMINI_API_KEY` and `GEMINI_API_URL` to your vendor or proxy endpoint. The `GEMINI_MODEL` environment variable can be used to change the model string (default: `gemini-pro`).
- Replace the image/video/instagram placeholders with your vendor SDK or direct HTTP endpoints when ready.

Image provider (Leonardo / Midjourney)
------------------------------------

This sample supports multiple image providers via the `IMAGE_PROVIDER` env var (default: `leonardo`).

- Leonardo: point `IMAGE_API_URL` to your Leonardo endpoint (or a proxy) and set `IMAGE_API_KEY`. The client sends `{ "prompt": ..., "width": ..., "height": ..., "cref": ... }` and expects a response containing `image_url` or a similar result field.
- Midjourney: direct integration typically requires a Discord bot or a hosted Midjourney API. You can run a small proxy that accepts the same JSON contract and communicates with your bot/Discord integration. Set `IMAGE_PROVIDER=midjourney` and `IMAGE_API_URL` to your proxy.

For character consistency use the `cref` parameter on each request (set `cref` to the character reference id your image vendor provides for Aria). If you don't yet have a `cref`, generate an initial reference image and capture the provider's reference id; reuse it for future calls.

SDK-backed Gemini Pro and local proxy
-------------------------------------

If you prefer to call Gemini Pro via the `google-generativeai` SDK, two options are supported:

1. Direct SDK usage inside `GeminiClient`:
	- Set `GEMINI_USE_SDK=true` in your `.env` (and ensure `GEMINI_API_KEY` is set).
	- Install the SDK: `pip install google-generativeai` (we added it to `requirements.txt`).
	- When `dry_run=False` and `GEMINI_USE_SDK` is true, `GeminiClient` will attempt to call the SDK first and fall back to the HTTP path if needed.

2. Run the small SDK proxy included at `scripts/gemini_sdk_proxy.py`:
	- This exposes a simple HTTP endpoint `/v1/agent` that accepts the same JSON payload used by `GeminiClient`.
	- Running it lets you avoid linking the SDK into every service; useful for hosting in a small GCE/Cloud Run service where you keep the SDK key secure.

To run the proxy locally (dev):

```bash
python scripts/gemini_sdk_proxy.py
```

It will run on port 8080 by default. Point `GEMINI_API_URL` to `http://localhost:8080/v1/agent` and set `GEMINI_USE_SDK=false` (or leave false) so the client uses the HTTP path and your proxy provides SDK-backed responses.
- Instagram posting is implemented as a simple placeholder that uses the Graph API endpoints when provided with a public video URL. For local files you'll need to upload the file to a public URL (or implement the chunked upload flow).
 - Instagram posting is implemented as a simple placeholder that uses the Graph API endpoints when provided with a public video URL. For local files you'll need to upload the file to a public URL (or implement the chunked upload flow).

ffmpeg and local video generation
--------------------------------

This repository can synthesize short playable MP4s from images using `ffmpeg` (used in dry-run when local output is requested). `ffmpeg` is optional by default, but you can require it at startup by setting `VIDEO_REQUIRE_FFMPEG=true` in your `.env` which will cause the orchestrator to fail early with a clear error if `ffmpeg` is not found on the PATH.

If `ffmpeg` is present, the `VideoGenerator` will attempt to create a short pan & zoom (Ken Burns) style clip from the generated image when `output_local=True`. If `ffmpeg` is missing or synthesis fails, the generator falls back to a tiny placeholder file so tests and local runs still work.

To use ffmpeg-based local output in the orchestrator dry-run, run:

```bash
# copy .env.example -> .env and set VIDEO_REQUIRE_FFMPEG=true (optional)
python -m src.main
```

If you need higher-quality or audio, install `ffmpeg` on your system (macOS: `brew install ffmpeg`, Ubuntu: `sudo apt install ffmpeg`) and adjust `VideoGenerator` if you need different encoding settings.

CI and production recommendation
--------------------------------

This project enables an ffmpeg-required mode for CI and production by setting `VIDEO_REQUIRE_FFMPEG=true`. A sample GitHub Actions workflow is included at `.github/workflows/ci.yml` which installs ffmpeg on the runner and sets that environment variable so the orchestrator will fail early if ffmpeg is not available. This helps catch configuration issues early in CI and ensures local-file video paths are reliably processable in production.

If you deploy to other CI systems or production, ensure `ffmpeg` is installed on the host/container and set `VIDEO_REQUIRE_FFMPEG=true` in the environment to enable the pre-flight check.

Cloud Run and Scheduler examples
--------------------------------

This repo includes a sample `Dockerfile` that installs `ffmpeg` into the container so the video generation path is available at runtime. Build and push the image, then deploy to Cloud Run:

```bash
# Build and push (example using Google Container Registry)
docker build -t gcr.io/PROJECT_ID/ai-orchestrator:latest .
docker push gcr.io/PROJECT_ID/ai-orchestrator:latest

# Deploy to Cloud Run (replace PROJECT_ID, REGION)
gcloud run deploy ai-orchestrator \
	--image gcr.io/PROJECT_ID/ai-orchestrator:latest \
	--region REGION \
	--platform managed \
	--set-env-vars VIDEO_REQUIRE_FFMPEG=true,DRY_RUN=false
```

If your orchestrator is intended to run on a schedule, you can either:

- Deploy an HTTP handler (Cloud Run service) and have Cloud Scheduler POST to it. An example Cloud Scheduler job template is included at `deploy/cloud-scheduler-job.yaml`.
- Or deploy as a Cloud Run Job (recommended for one-off or batch runs) and trigger it from Cloud Scheduler using the `gcloud run jobs execute` command.

Example Cloud Run service and scheduler templates are provided in the `deploy/` folder. They are meant as starting points — replace `PROJECT_ID`, `REGION`, and `SERVICE_URL` with your values and configure authentication (OIDC) for secure invocations.

Cloud Run Job + Scheduler (no HTTP server)
-----------------------------------------

If you prefer not to add an HTTP server to the container, use Cloud Run Jobs. A sample job manifest is included at `deploy/cloudrun-job.yaml`. After building and pushing your image, create the job and then you can execute it on demand:

```bash
# create the job (beta/latest gcloud may vary)
gcloud beta run jobs create ai-orchestrator-job --image gcr.io/PROJECT_ID/ai-orchestrator:latest --region REGION

# execute the job once
gcloud beta run jobs execute ai-orchestrator-job --region REGION
```

To schedule the job, use Cloud Scheduler to call the Run Jobs execute endpoint with OIDC authentication. A sample scheduler template that calls the Run Jobs API directly is provided at `deploy/cloud-scheduler-execute-job.yaml`. Replace variables in the template and ensure the scheduler's service account has `roles/run.invoker` / `run.jobs.run` as appropriate.

If you prefer, Cloud Scheduler can trigger a small Cloud Function or Cloud Build step that runs the `gcloud beta run jobs execute` command — choose whichever fits your security model.

CI/CD: automatic build & push
--------------------------------

This repository includes a GitHub Actions workflow `.github/workflows/build-and-push.yml` that will build and push the Docker image to Google Container Registry on push to `main`.

Requirements for the workflow to push to GCR:
- Add a secret `GCP_SA_KEY` containing a JSON service account key with `roles/storage.admin` and `roles/run.admin` (or narrower roles as appropriate).
- Add a secret `GCP_PROJECT` with your GCP project id.

The workflow will tag the image as `gcr.io/$GCP_PROJECT/ai-orchestrator:latest`. You can change tagging strategy to include commit SHA or use semantic tags.

License: MIT
