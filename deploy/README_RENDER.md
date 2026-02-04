# Deploying the scaffold backend & worker to Render

This document describes a recommended deployment pattern for the scaffold:

- Frontend: deploy `scaffold/frontend` to Vercel (static site)
- Backend: deploy `scaffold/backend` to Render as a Web Service using the included Dockerfile
- Worker: deploy the Python worker as a separate Render Worker or Background Job using the project's top-level Dockerfile (which includes ffmpeg)
- Redis: use a managed Redis provider (Upstash, Redis Cloud) and set `REDIS_URL` in both backend and worker

Why Render for the backend & worker
- Allows installing system binaries (ffmpeg) and running long-running/background jobs without serverless timeouts.
- Simple Docker deployment via GitHub integration.

Files added
- `deploy/render-backend.Dockerfile` — Dockerfile for `scaffold/backend` (installs ffmpeg and runs the Express app)

Render setup (Backend web service)
1. In Render dashboard create a new **Web Service** and select your GitHub repository.
2. For the service settings:
   - Name: `model-ai-backend`
   - Branch: main (or your chosen branch)
   - Root Directory: leave empty (we use Dockerfile at `deploy/render-backend.Dockerfile`)
   - Environment: Docker
   - Dockerfile Path: `deploy/render-backend.Dockerfile`
   - Build Command: (not needed for Docker)
   - Start Command: (not needed — Dockerfile's CMD will run)
3. Environment variables (Render dashboard -> Environment):
   - PORT=4000
   - NODE_ENV=production
   - DATABASE_URL=<your_mysql_or_sqlite_url>
   - REDIS_URL=<your_redis_url>
   - JWT_SECRET=<your_jwt_secret>
   - WHOP_PRODUCT_URL=<your_whop_checkout_url>
   - YOUTUBE_CLIENT_SECRETS_FILE (if you plan to run YouTube uploads) — see notes below

Render setup (Worker background service)
1. Create a new **Background Worker** (or a second Web Service) in Render.
2. Use the project's top-level Dockerfile (it installs Python and ffmpeg) by setting Dockerfile Path to `Dockerfile` (at repo root).
3. Environment variables:
   - REDIS_URL=<your_redis_url>
   - Any API keys used by `src/` (e.g., OPENROUTER_API_KEY, STABILITY_API_KEY, YOUTUBE credentials paths or secrets)

Notes about storage and credentials
- Filesystem on Render instances is ephemeral; don't rely on local sqlite for durable storage in production. Use MySQL/PlanetScale/Ionos and set `DATABASE_URL` accordingly.
- If you want to persist credentials for YouTube (the OAuth flow writes `youtube_token.json`), consider storing that in a safe external store or enable a persistent filesystem on Render (limited) or use a Cloud Storage bucket and adapt `src/youtube_poster.py` to read/write from it.

Redis recommendations
- Upstash (free-tier) or Redis Cloud provide hosted Redis and are straightforward to connect. Copy the Redis URL to `REDIS_URL` in both the backend and worker.

Vercel frontend
1. In Vercel, import the repo and set Project Root to `scaffold/frontend`.
2. Build Command: `npm run build` (or `pnpm build` if using pnpm). Output Directory: `dist`.
3. Set an environment variable in Vercel for the API base URL (example):
   - VITE_API_BASE_URL=https://<your-render-backend>.onrender.com

Whop / OAuth notes
- Create your Whop Product and set the checkout redirect back to your Vercel frontend (e.g., `https://your-site.vercel.app/_auth/whop/callback`).
- Add any Whop client secrets to Vercel environment variables as required.

Quick checklist before deploy
- [ ] Create managed Redis and copy URL
- [ ] Create MySQL (or use PlanetScale / managed DB) and copy DATABASE_URL
- [ ] Add env vars to Render services and Vercel frontend
- [ ] Deploy backend on Render and confirm `/api/health`
- [ ] Deploy frontend on Vercel and configure `VITE_API_BASE_URL`

If you'd like, I can add a `render` section to the repo's README with exact Render UI screenshots and the minimal set of env vars to set.
