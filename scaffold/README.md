# Scaffold for AI Orchestrator Prototype

This folder contains a minimal backend (Express) and frontend (Vite + React) scaffold to start the SaaS prototype. It's intentionally tiny to help you iterate quickly.

Backend:
- location: `scaffold/backend`
- start: `cd scaffold/backend && npm install && npm run dev`

Frontend:
- location: `scaffold/frontend`
- start: `cd scaffold/frontend && npm install && npm run dev`

Notes:
- The backend uses an in-memory store for users and jobs — for prototyping only. Replace with MySQL and Redis/BullMQ for production.
- The frontend proxies requests to `/api/*`; in development you can configure Vite to proxy to the backend.
- An OpenAPI file is provided at `scaffold/backend/openapi.yaml` as a starting point for API design.
