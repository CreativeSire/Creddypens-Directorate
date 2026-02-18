# One-Project Vercel Setup (Frontend + Backend)

This repo supports deploying both Next.js frontend and FastAPI backend in a **single Vercel project**.

## Required Vercel settings

1. Create one project from `CreativeSire/Creddypens-Directorate`.
2. In project settings:
   - **Framework Preset**: `Other`
   - **Root Directory**: `./` (repo root)
3. Add environment variables:
   - `DATABASE_URL`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `ANTHROPIC_API_KEY`
   - `GEMINI_API_KEY`
   - `LLM_MOCK=0`
   - `ALLOWED_ORIGINS=https://<your-domain>,https://www.<your-domain>`
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` (optional; leave empty to use same-origin routing)

## Routing behavior

- Frontend routes are served by Next.js build from `frontend/`.
- Backend API is served by Python function at:
  - `/health`
  - `/v1/*`

Configured in root `vercel.json`.

## Verify after deploy

- `https://<your-domain>/health` returns 200 JSON.
- `https://<your-domain>/v1/agents` returns agent list.
- `https://<your-domain>/` loads landing page.
