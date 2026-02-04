# Deploy helpers and IAM notes

This document describes the GitHub Actions workflow and the minimum secrets and IAM bindings needed to build, push, and schedule the Cloud Run Job created by this repo.

Required GitHub repository secrets

- `GCP_SA_KEY` — JSON key for a service account used by the workflow to run `gcloud` commands.
- `GCP_PROJECT` — your GCP project id.
- `GCP_REGION` — (optional) region for Cloud Run jobs; defaults to `us-central1`.
- `SCHEDULER_SA_EMAIL` — (recommended) email of the service account Cloud Scheduler will use to call the Run Jobs API (optional; if not provided the workflow will use the workflow's service account).
- `SCHEDULER_CRON` / `SCHEDULER_JOB_NAME` — optional defaults for the scheduler.
- `SCHEDULER_OIDC_AUD` — optional OIDC audience; defaults to `https://run.googleapis.com/`.

Recommended minimal IAM for the workflow service account (`GCP_SA_KEY`)

Grant the workflow SA the following roles (least privilege where possible):

- `roles/run.admin` — create/update Cloud Run Jobs.
- `roles/cloudscheduler.admin` — create/update Cloud Scheduler jobs.
- `roles/storage.admin` or the necessary Artifact Registry / Container Registry writer role — push images.

Recommended IAM for the scheduler service account (`SCHEDULER_SA_EMAIL`)

This SA will be used by Cloud Scheduler to obtain an OIDC token and call the Run Jobs REST endpoint. Grant it the minimum necessary permission to run the job. For example:

1) Create a scheduler SA:

```bash
gcloud iam service-accounts create scheduler-invoker --display-name "Scheduler invoker"
```

2) Grant it permission to run the Cloud Run Job (least-privilege option):

```bash
# Grant just the run.jobs.run permission (via a custom role or predefined role). Example uses roles/run.invoker broadly.
gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:scheduler-invoker@$GCP_PROJECT.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

If your environment requires broader rights, you can grant `roles/run.admin` to the scheduler SA, but that's more permissive than necessary.

Using the workflow

- The workflow `Build, Push, and Deploy Cloud Run Job` will:
  - Build and push the Docker image to `gcr.io/$GCP_PROJECT/model-ai-orchestrator:{{sha}}` and `:latest`.
  - If `deploy/cloudrun-job.yaml` exists, it will apply the manifest with `gcloud beta run jobs replace --source=deploy/cloudrun-job.yaml` (this keeps retries/timeout/task settings from your manifest).
  - Create or update a Cloud Scheduler job (idempotent). By default it will schedule at `0 19,23 * * *` (19:00 and 23:00 daily). Override via workflow inputs or the `SCHEDULER_CRON` secret.

Manual run

- You can run the workflow manually from GitHub Actions (Run workflow) and provide these inputs:
  - `schedule_cron` — cron expression (overrides repo secret)
  - `scheduler_job_name` — name for the scheduler job
  - `scheduler_sa_email` — service account email Cloud Scheduler should use
  - `scheduler_oidc_audience` — OIDC audience (default `https://run.googleapis.com/`)
  - `run_once` — `true` to execute the job once after deploy

Troubleshooting

- If the scheduler job creation fails with permission errors, ensure the workflow SA has `roles/cloudscheduler.admin` and that the scheduler SA has permission to invoke the Run Job (see IAM recommendations above).
- If the job manifest doesn't apply, run locally:

```bash
gcloud auth activate-service-account --key-file=path/to/key.json
gcloud config set project $GCP_PROJECT
gcloud beta run jobs replace --source=deploy/cloudrun-job.yaml --region=$GCP_REGION
```

If you want, I can add a small script to the repo that automates granting the recommended IAM bindings (requires admin privileges when run).
