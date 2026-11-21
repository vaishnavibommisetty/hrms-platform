# HRMS Platform — Deployment Guide

## Stack
- **Frontend**: React + Vite → Vercel
- **Backend**: FastAPI → Render
- **Database**: PostgreSQL → Supabase

---

## Step 1 — GitHub Push (do this first!)

```bash
cd hrms-platform
git init && git add . && git commit -m "feat: Enterprise HRMS Platform"
git remote add origin https://TOKEN@github.com/thishitha06-sketch/hrms-platform.git
git push -u origin main
```

---

## Step 2 — Supabase (Database)

1. Go to **supabase.com** → New Project
   - Name: `hrms-platform`
   - Password: (save this!)
   - Region: Southeast Asia (Singapore)

2. Wait ~2 min for project to be ready

3. Go to **SQL Editor** → paste contents of `supabase_schema.sql` → **Run**

4. Go to **Settings → Database** → copy the **URI** (Connection String)
   - It looks like: `postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres`

---

## Step 3 — Render (Backend)

1. Go to **render.com** → New → **Web Service**
2. Connect your GitHub repo: `thishitha06-sketch/hrms-platform`
3. Settings:
   - Name: `hrms-backend`
   - Region: Singapore
   - Runtime: **Python 3**
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment Variables (click **Add Environment Variable**):
   ```
   DATABASE_URL = postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres
   JWT_SECRET_KEY = [any-long-random-string-32-chars]
   JWT_ALGORITHM = HS256
   ACCESS_TOKEN_EXPIRE_MINUTES = 480
   ENVIRONMENT = production
   CORS_ORIGINS = https://hrms-platform.vercel.app
   ```
5. Click **Create Web Service** → wait ~5 min to deploy
6. Copy the Render URL: `https://hrms-backend-xxxx.onrender.com`

---

## Step 4 — Vercel (Frontend)

1. Go to **vercel.com** → New Project
2. Import from GitHub: `thishitha06-sketch/hrms-platform`
3. Settings:
   - Root Directory: `frontend`
   - Framework: **Vite**
4. Environment Variables:
   ```
   VITE_API_URL = https://hrms-backend-xxxx.onrender.com
   ```
5. Click **Deploy** → wait ~3 min
6. Your app is live at: `https://hrms-platform.vercel.app`

---

## Step 5 — Update CORS on Render

After Vercel deploys, go back to Render → Environment:
- Update `CORS_ORIGINS` to your actual Vercel URL
- Render will auto-redeploy

---

## Demo Login Credentials

- Email: `admin@zerocodehr.com`
- Password: `Admin@123`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend 500 error | Check DATABASE_URL is correct in Render env vars |
| CORS error | Make sure CORS_ORIGINS matches exact Vercel URL |
| Login fails | Make sure SQL schema was run in Supabase |
| Render sleeps after 15min | Free tier spins down — first request takes ~30s |
