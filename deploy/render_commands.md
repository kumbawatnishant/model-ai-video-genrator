# Quick Render CLI commands

These are short examples you can run locally to create services, set secrets, and deploy via Render's CLI. Replace placeholders (USER, REPO, <values>) with your own.

1) Login to Render (interactive)

```bash
render login
```

2) Create secrets (example)

```bash
render secrets create REDIS_URL "redis://:<pw>@something.upstash.io:6379"
render secrets create DATABASE_URL "mysql://user:pass@host/dbname"
render secrets create JWT_SECRET "your-jwt-secret"
```

3) Create the backend web service (Dockerfile-based)

```bash
render services create \
  --name model-ai-backend \
  --repo https://github.com/USER/REPO \
  --branch main \
  --service-type web \
  --env docker \
  --dockerfile-path deploy/render-backend.Dockerfile
```

4) Create the worker (background job) using the repo root Dockerfile

```bash
render services create \
  --name model-ai-worker \
  --repo https://github.com/USER/REPO \
  --branch main \
  --service-type worker \
  --env docker \
  --dockerfile-path Dockerfile \
  --start-cmd "./scripts/start-worker.sh"
```

5) Attach secrets to a service

```bash
render services update model-ai-backend --secrets REDIS_URL,DATABASE_URL,JWT_SECRET
render services update model-ai-worker --secrets REDIS_URL,DATABASE_URL,JWT_SECRET
```

6) Deploy from a branch (trigger a manual deploy)

```bash
render deploy model-ai-backend --branch main
render deploy model-ai-worker --branch main
```

Notes
- The exact CLI flags may change with Render CLI versions — the UI is the alternative.
- You can manage secrets in the Render dashboard or via `render secrets create` for automation/CI.
