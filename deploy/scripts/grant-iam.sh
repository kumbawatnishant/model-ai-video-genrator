#!/usr/bin/env bash
set -euo pipefail

# grant-iam.sh
# Helper to create a Cloud Scheduler service account and apply minimal IAM bindings.
# Requires project-owner or IAM admin to run.
# Usage: ./deploy/scripts/grant-iam.sh <PROJECT_ID> [SA_NAME]

PROJECT_ID=${1:-}
if [ -z "$PROJECT_ID" ]; then
  echo "Usage: $0 <PROJECT_ID> [SA_NAME] [--grant-run-admin]"
  exit 2
fi

# Optional second argument is the service account name; default 'scheduler-invoker'
SA_NAME=${2:-scheduler-invoker}
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Optional third argument --grant-run-admin to also grant roles/run.admin (not recommended)
GRANT_RUN_ADMIN=false
if [ "${3:-}" = "--grant-run-admin" ] || [ "${3:-}" = "grant-run-admin" ]; then
  GRANT_RUN_ADMIN=true
fi

echo "Creating service account: $SA_EMAIL in project $PROJECT_ID (if it doesn't exist)"
if gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "Service account already exists: $SA_EMAIL"
else
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name "Scheduler invoker" --project "$PROJECT_ID"
fi

echo "Granting roles/run.invoker to $SA_EMAIL on project $PROJECT_ID"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"

if [ "$GRANT_RUN_ADMIN" = true ]; then
  echo "Granting roles/run.admin to $SA_EMAIL on project $PROJECT_ID (requested via --grant-run-admin)"
  echo "NOTE: Granting run.admin to the scheduler SA is not recommended unless required."
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"
fi

echo "(Optional) If you prefer to grant a narrower permission scoped to a specific job or service,
replace the project-level binding with a resource-specific binding using the job or service resource name."

echo "Completed. Scheduler service account: $SA_EMAIL"
echo "Add the following GitHub secret to your repository: SCHEDULER_SA_EMAIL=$SA_EMAIL"

echo "If you need the workflow service account to be able to create scheduler jobs, ensure the workflow SA has: roles/cloudscheduler.admin and roles/run.admin."

echo "Done."
