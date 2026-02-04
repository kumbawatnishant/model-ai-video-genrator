# Simple Makefile to build, push, create Cloud Run job and schedule it.
# Configure these variables via environment or override on the command line.
PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
REGION ?= us-central1
IMAGE ?= gcr.io/$(PROJECT_ID)/ai-orchestrator:latest
JOB_NAME ?= ai-orchestrator-job
SCHED_NAME ?= ai-orchestrator-schedule
SERVICE_ACCOUNT ?= $(shell gcloud iam service-accounts list --format='value(email)' --limit=1 2>/dev/null)

.PHONY: build push job-create job-execute job-delete scheduler-create scheduler-delete all

build:
	docker build -t $(IMAGE) .

push: build
	docker push $(IMAGE)

job-create: push
	# Create or replace the Cloud Run job
	gcloud beta run jobs describe $(JOB_NAME) --region $(REGION) >/dev/null 2>&1 || \
		gcloud beta run jobs create $(JOB_NAME) --image $(IMAGE) --region $(REGION) || true
	gcloud beta run jobs update $(JOB_NAME) --image $(IMAGE) --region $(REGION) || true

job-execute:
	gcloud beta run jobs execute $(JOB_NAME) --region $(REGION)

job-delete:
	gcloud beta run jobs delete $(JOB_NAME) --region $(REGION) --quiet || true

scheduler-create:
	# Create a Cloud Scheduler job that calls the Run Jobs API with OIDC
	gcloud scheduler jobs create http $(SCHED_NAME) --schedule="0 9 * * *" \
	  --uri="https://run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/$(JOB_NAME):run" \
	  --http-method=POST --oidc-service-account-email=$(SERVICE_ACCOUNT) --location=$(REGION) || true

scheduler-delete:
	gcloud scheduler jobs delete $(SCHED_NAME) --location=$(REGION) --quiet || true

all: job-create scheduler-create
