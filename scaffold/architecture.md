## AI Orchestrator — Architecture Overview

This document describes the components for the SaaS prototype and how they interact. It's intentionally compact so you can use it as a guide while building the prototype.

Diagram (ASCII)

  +-----------+         +-------------+        +------------+
  |  Frontend | <---->  |  Backend    | <----> |  MySQL     |
  | (React)   |  HTTPS  | (Node API)  |  SQL   | (Users,    |
  +-----------+         +-------------+        |  Jobs, etc)|
                             |  ^  
                             |  |  
                             v  |  
                         +--------+       +------------+
                         | Redis  | <-->  |  Workers   |
                         | (Queue)|       | (Python)   |
                         +--------+       +------------+
                                              |
                                              v
                                          +--------+
                                          |  S3    |
                                          | (Media)|
                                          +--------+

Components
- Frontend (React): SPA with onboarding, job submission, job list and billing UI. Communicates with backend over HTTPS and listens for progress via SSE or WebSocket.
- Backend (Node/Express): Auth, user/profile management, job submission endpoints, billing/Whop webhook handlers, and short-lived token issuance for uploads. Enqueues jobs into Redis.
- Redis (BullMQ or Redis lists): Job queue and pub/sub for real-time progress. Used to rate-limit and coordinate workers.
- Workers (Python containers): Stateless workers run your existing `src/` orchestrator logic. Workers pop jobs from Redis, execute the multi-step workflow (concept -> image -> video -> upload) and store outputs to S3. Workers emit job progress events back to Redis pub/sub.
- MySQL: Persistent store for users, subscriptions, job metadata, and audit logs.
- S3-compatible object storage: Store final media and large artifacts; deliver via signed URLs or CDN.
- Whop (Billing): Use Whop API and webhooks to gate access and enforce quotas.

Key design notes
- Decouple orchestration logic into workers to scale rendering and avoid blocking the API.
- Keep secrets encrypted at rest (DB or secret store) and never log them.
- Use idempotency keys and checkpointing so jobs can be resumed or retried safely.
- Expose minimal surface area in the backend; heavy lifting runs inside worker containers.

How this maps to the scaffold
- `scaffold/backend` — minimal API to create jobs and enqueue to Redis if `REDIS_URL` is set.
- `scaffold/worker` — a lightweight Python worker that BLPOP's `ai_jobs` and runs `python -m src.main` for each job (dry-run by default).
- `src/` — contains the existing Python orchestrator that can be run from worker containers with minor environment configuration.

Next steps
- Expand the API (OpenAPI) for user keys, billing, and upload tokens.
- Add a BullMQ-based job system for visibility, retries, and rate-limiting.
- Harden worker checkpointing and add a dead-letter queue for permanent failures.
