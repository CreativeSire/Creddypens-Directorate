# CreddyPens Production Cutover Runbook (Week 4 Day 27-28)

## 1) Pre-cutover prerequisites
- Backend + frontend code merged to `main`.
- Local smoke checks green:
  - `python -m compileall backend/app backend/scripts -q`
  - `cd frontend && npm run -s lint`
  - `python backend/scripts/smoke_test_complete.py`
- Deployment env validated:
  - `python backend/scripts/predeploy_check.py --backend-env backend/.env --frontend-env frontend/.env.local`

## 2) Key rotation checklist
- Rotate and update:
  - `ANTHROPIC_API_KEY`
  - `GEMINI_API_KEY` / `GOOGLE_API_KEY`
  - `OPENAI_API_KEY` (if used)
  - `GROQ_API_KEY` (if used)
  - `SERPER_API_KEY` (if used)
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` (if used)
  - `SENTRY_DSN` (if used)
- Do not commit secrets to git.

## 3) Vercel configuration (single project)
- Import repo root.
- Set env vars in Vercel Project Settings:
  - Backend: `DATABASE_URL`, `ALLOWED_ORIGINS`, `LLM_MOCK=0`, provider keys, `RATE_LIMIT_ENABLED=1`
  - Frontend: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, optional `NEXT_PUBLIC_API_URL`
- Confirm root `vercel.json` routes:
  - `/health` and `/v1/*` -> backend function
  - all other routes -> frontend

## 4) Database migration
- Confirm production DB has latest schema:
  - Run `ensure_schema()` against production DB once.
- Verify key tables exist:
  - `agent_catalog`, `interaction_logs`, `agent_memories`, `uploaded_files`
  - `workflow_templates`, `workflow_schedules`, `task_inbox`, `knowledge_base`

## 5) Cutover sequence
1. Deploy `main` to Vercel Production.
2. Validate `/health` and `/v1/agents`.
3. Run staging/prod smoke matrix:
   - `python backend/scripts/smoke_test_staging.py --base-url https://<domain> --org-id org_smoke`
4. Manually verify critical UI flows:
   - login, browse agents, hire, chat, workflow run, analytics page.

## 6) Monitoring and rollback
- Confirm Sentry receives backend and frontend errors.
- Watch rate limit and error logs for first hour.
- Rollback trigger:
  - repeated 5xx on `/v1/agents/*/execute`
  - login/auth flow outage
  - smoke matrix pass rate < 90%
- Rollback action:
  - promote previous stable Vercel deployment.

## 7) Done criteria
- Smoke matrix all pass.
- Core user journey pass.
- No critical Sentry alerts for 30+ minutes after cutover.
