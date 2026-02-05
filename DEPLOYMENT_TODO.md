# Deployment Checklist

## 1. Fix "Root Directory" Error
- [ ] **Render Settings**: Go to your Service Settings > General.
- [ ] **Root Directory**: Change to `scaffold/backend`.
      **CRITICAL:** You currently have a typo: `srcscaffold/backend`. Delete the `src` prefix.
- [ ] **Build Command**: Ensure it is `npm install`.
- [ ] **Start Command**: Ensure it is `npm start`.

## 2. Fix Crash on Startup (Sequelize Error)
- [x] **Critical Code Fix**: Updated `scaffold/backend/models/index.js` to handle `DATABASE_URL` correctly and fix the `sqlite::memory:` crash.
- [x] **Node Version**: Pinned to `20.x` in `package.json` to avoid unstable v25 builds.

## 3. Environment Variables (Security & Database)
Add these in the "Environment" tab of your deployment service (Render/Vercel):

- [ ] `NODE_ENV`: Set to `production`.
- [ ] `JWT_SECRET`: Set to a long random string (e.g., generated via `openssl rand -hex 32`).
- [ ] `DATABASE_URL`: (Optional but recommended) Connection string for PostgreSQL. 
      *Note: Without this, the app uses temporary memory storage and will lose users on restart.*
- [ ] **Database Driver**: If using PostgreSQL (Render's default), ensure `pg` is in `package.json` (Added in latest update).

## 4. Vercel Specifics (If deploying Frontend there)
- [ ] Ensure `vercel.json` is present in the root (already added).
- [ ] In Vercel Project Settings > Root Directory, select `scaffold/frontend` if deploying the UI, or leave default if using the `vercel.json` for backend.

## 5. Frontend Connection
- [ ] Once the backend is live (e.g., `https://model-ai-backend.onrender.com`), you must update your Frontend.
- [ ] If deploying Frontend to Vercel: Add an Environment Variable `VITE_API_URL` (or similar, check your frontend code) with the value of your Render Backend URL.

## 6. Verification
- [ ] Push these changes to GitHub.
- [ ] Check deployment logs for "Build Successful".
- [ ] Visit the deployed URL + `/api/health` to confirm the backend is running (should return `{"status":"ok"}`).