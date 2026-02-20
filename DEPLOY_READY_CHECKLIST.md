# CreddyPens Deploy-Ready Checklist

## Validation Status (Local)
- [x] Backend compile check passes (`python -m compileall app -q`)
- [x] Backend smoke test passes (`backend/scripts/smoke_test.ps1`)
- [x] Frontend lint passes (`npm run lint`)
- [x] Frontend production build passes (`npm run build`)
- [x] Full smoke matrix passes (`python backend/scripts/smoke_test_complete.py`)
- [x] Predeploy env validator added (`python backend/scripts/predeploy_check.py`)

## Pre-Deploy (Vercel)
- [ ] Add backend env vars in Vercel (`DATABASE_URL`, `SUPABASE_*`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `ALLOWED_ORIGINS`, `SENTRY_DSN`)
- [ ] Set `LLM_MOCK=0` in production
- [ ] Deploy backend (`backend/vercel.json` present)
- [ ] Set frontend env vars (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`)
- [ ] Deploy frontend
- [ ] Run predeploy check against staging env files

## Post-Deploy Production Smoke
- [ ] `GET /health` returns 200
- [ ] `GET /v1/agents` returns all active agents
- [ ] `GET /v1/organizations/{org_id}/analytics/*` returns 200
- [ ] Signup/login + org bootstrap works
- [ ] Hire flow works from dossier
- [ ] My Agents chat executes and returns real LLM output
- [ ] Dashboard stats and Academy status load
- [ ] Run `python backend/scripts/smoke_test_staging.py --base-url https://<domain> --org-id org_smoke`

## DNS & Monitoring
- [ ] Add `creddypens.com` and `www.creddypens.com` in Vercel domains
- [ ] Configure DNS records at registrar
- [ ] Confirm HTTPS certificate active
- [ ] Verify Sentry receives frontend + backend errors
