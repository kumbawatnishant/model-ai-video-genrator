# Deployment Checklist

## 1. Fix "Root Directory" Error
- [ ] **Render Settings**: Go to your Service Settings > General.
- [ ] **Root Directory**: Change to `scaffold/backend`. (Check for typos! Error `srcscaffold` means you typed it wrong).
- [ ] **Build Command**: Ensure it is `npm install`.
- [ ] **Start Command**: Ensure it is `npm start`.

## 2. Environment Variables (Security & Database)
Add these in the "Environment" tab of your deployment service (Render/Vercel):

- [ ] `NODE_ENV`: Set to `production`.
- [ ] `JWT_SECRET`: Set to a long random string (e.g., generated via `openssl rand -hex 32`).
- [ ] `DATABASE_URL`: (Optional but recommended) Connection string for PostgreSQL. 
      *Note: Without this, the app uses temporary memory storage and will lose users on restart.*

## 3. Vercel Specifics (If deploying Frontend there)
- [ ] Ensure `vercel.json` is present in the root (already added).
- [ ] In Vercel Project Settings > Root Directory, select `scaffold/frontend` if deploying the UI, or leave default if using the `vercel.json` for backend.

## 4. Verification
- [ ] Push these changes to GitHub.
- [ ] Check deployment logs for "Build Successful".
- [ ] Visit the deployed URL + `/api/health` to confirm the backend is running (should return `{"status":"ok"}`).