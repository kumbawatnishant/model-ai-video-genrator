#!/usr/bin/env bash
# Helper script to build, push, create Cloud Run job, and schedule it.
# Usage: ./deploy/deploy.sh [project-id] [region]

set -euo pipefail
PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION=${2:-us-central1}
IMAGE=gcr.io/${PROJECT_ID}/ai-orchestrator:latest
JOB_NAME=ai-orchestrator-job
SCHED_NAME=ai-orchestrator-schedule

echo "Building docker image ${IMAGE}..."
docker build -t ${IMAGE} .

echo "Pushing image..."
docker push ${IMAGE}

# Create or update job
if gcloud beta run jobs describe ${JOB_NAME} --region ${REGION} >/dev/null 2>&1; then
  echo "Updating existing job ${JOB_NAME}..."
  gcloud beta run jobs update ${JOB_NAME} --image ${IMAGE} --region ${REGION}
else
  echo "Creating job ${JOB_NAME}..."
  gcloud beta run jobs create ${JOB_NAME} --image ${IMAGE} --region ${REGION}
fi

# Execute once to verify
echo "Executing job once..."
gcloud beta run jobs execute ${JOB_NAME} --region ${REGION}

# Create scheduler job using OIDC; assumes a service account is available with correct permissions
SA_EMAIL=$(gcloud iam service-accounts list --format='value(email)' --limit=1)
if [ -z "$SA_EMAIL" ]; then
  echo "WARNING: No service account found; create one and grant it run.jobs.run, then re-run scheduler-create step manually."
else
  echo "Creating scheduler job ${SCHED_NAME} to execute the Run Job via OIDC..."
  gcloud scheduler jobs create http ${SCHED_NAME} --schedule="0 9 * * *" \
    --uri="https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST --oidc-service-account-email=${SA_EMAIL} --location=${REGION} || true
fi

echo "Deploy completed."
