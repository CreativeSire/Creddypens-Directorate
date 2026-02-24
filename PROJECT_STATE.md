# CreddyPens Directorate — Living Build Document

Last updated: 2026-02-20
Owner: Engineering (Codex + team)  
Purpose: single source of truth for what is built, what is running, and what changed.

---

## 1) Product in one sentence
CreddyPens is an AI workforce platform where organizations hire role-based AI agents, run work through chat, and monitor quality/performance from one command dashboard.

---

## 2) What is built right now

## 2.1 Backend (FastAPI)
- Core API is live under:
  - `GET /health`
  - `GET /v1/agents`
  - `GET /v1/agents/{agent_code}`
  - `POST /v1/agents/{agent_code}/execute`
  - `POST /v1/agents/{agent_code}/checkout`
  - `POST /v1/agents/{agent_code}/hire`
  - `GET /v1/organizations/{org_id}/dashboard-stats`
  - `GET /v1/organizations/{org_id}/agents/{agent_code}/stats`
  - Academy routes under `/v1/academy/*`
  - Router stats: `GET /v1/llm/router/stats`
  - Skill marketplace routes under `/v1/skills/*` and `/v1/organizations/{org_id}/skills/*`

- Agent execution flow:
  1. Validate org + hired agent.
  2. Build system context for role.
  3. Inject domain boundary block (domain_tags, related_agents, out_of_scope_examples) into system prompt.
  4. Inject installed skill pack `prompt_injection` blocks into system prompt (org-wide + agent-specific).
  5. Send request through `execute_via_litellm`.
  6. Smart router selects provider/model.
  7. Parse response for `[REFER:CODE]` referral tag.
  8. Resolve referred agent, check hire status, return SuggestedAgent payload.
  9. Log interaction to `interaction_logs`.

- Multi-LLM routing:
  - Smart routing exists and is integrated.
  - Providers implemented in router layer (Anthropic/Gemini/OpenAI/Ollama/Groq support path).
  - Response cache + cost tracking are implemented.
  - Stats endpoint exposes calls, cache hit rate, and estimated savings.

- Academy / training:
  - Scenario generation pipeline exists.
  - Synthetic trainer exists (`backend/app/academy/synthetic.py`).
  - Batch trainer exists (`backend/app/academy/trainer.py`).
  - Full-run script exists (`backend/scripts/train_all_agents.py`).
  - Evaluator exists and now uses router-configured judge defaults:
    - `ACADEMY_JUDGE_PROVIDER` (default: `groq`)
    - `ACADEMY_JUDGE_MODEL` (default: `llama-3.3-70b-versatile`)

## 2.2 Frontend (Next.js)
- Landing + dashboard app structure exists.
- Dashboard pages implemented:
  - Main dashboard
  - Departments
  - Agent dossier
  - My Agents
  - Academy
  - Skills Marketplace
  - Settings (baseline)
- My Agents flow implemented:
  - Hired-agent list
  - Open chat modal
  - Execute task against backend endpoint
- Checkout/hire flow:
  - Mock checkout path exists.
  - Stripe-ready path scaffolding exists in backend.
- Styling:
  - Dark theme with cyan/amber branding across major pages.
  - Ongoing polish work includes transitions/loading/empty states.

---

## 3) Data model and operational entities
- Agent catalog table (role definition, pricing, status, prompts, premium profile fields).
- Hired agents table (org-to-agent deployment).
- Interaction logs table (message/response/latency/tokens/quality/traces).
- Training/evaluation tables (sessions, scenarios, results, prompt versions).

---

## 4) Current known capability boundaries
- Strong today:
  - Role-based execution
  - Multi-provider routing
  - Org-scoped deployment and logs
  - Synthetic training + scoring loop
- Not fully complete yet:
  - Long-term conversational memory injection per session
  - Rich external tool execution layer (web/files/third-party actions) in production path
  - Advanced observability automation (alert routing, SLO dashboards, on-call runbooks)
  - Frontend referral card UI (SuggestedAgent payload returned but not yet rendered)
  - One-shot purchase flow for referred agents not yet hired

---

## 5) Latest major completed milestones

## 2026-02-20 (Skills Marketplace)
- Skill Marketplace system built end-to-end:
  - Added `skill_catalog` + `skill_installations` DB tables to `backend/app/schema.py`
    - Partial unique indexes support both agent-specific and org-wide installs.
  - Created `backend/app/api/skills.py` with full marketplace API:
    - `GET /v1/skills` — browse all active skills (optional `?category=` filter)
    - `GET /v1/skills/{skill_id}` — skill detail
    - `GET /v1/organizations/{org_id}/skills` — all installed for org
    - `GET /v1/organizations/{org_id}/agents/{agent_code}/skills` — agent-specific + org-wide
    - `POST/DELETE /v1/organizations/{org_id}/skills/{skill_id}` — org-wide install/uninstall
    - `POST/DELETE /v1/organizations/{org_id}/agents/{agent_code}/skills/{skill_id}` — per-agent install/uninstall
  - Created `backend/scripts/seed_skills.py` with 40 skill packs across 8 categories:
    - Marketing & Creative (8), Sales & Business Dev (5), Operations & Admin (6), Technical & IT (6)
    - Customer Experience (4), Specialized Services (8), Product & Design (2), Learning & Development (1)
    - Mix of free and paid ($7.99–$19.99/mo) packs
  - Injected installed skill `prompt_injection` text into the execute system prompt at runtime
    (`backend/app/api/routes.py` — non-fatal, graceful fallback if tables not migrated)
  - Registered skills router in `backend/app/main.py`
  - Built `frontend/src/app/dashboard/skills/page.tsx` — full marketplace UI:
    - Category filter tabs, skill cards with domain tags, price badges
    - One-click install/uninstall with live feedback
    - Install count display, author attribution
    - Paid skills show "COMING SOON" (Stripe billing in next release)
  - Added "Skills" nav item to sidebar (`frontend/src/components/navigation/sidebar.tsx`)
  - Seeded 40 skills into the database via `python scripts/seed_skills.py`

## 2026-02-20
- Week 4 Day 25-26 completed (enhanced analytics):
  - Added backend analytics query layer:
    - `backend/app/analytics/queries.py`
    - overview KPIs, department cost estimates, activity timeseries.
  - Added analytics API endpoints:
    - `GET /v1/organizations/{org_id}/analytics/overview`
    - `GET /v1/organizations/{org_id}/analytics/costs`
    - `GET /v1/organizations/{org_id}/analytics/activity`
  - Added frontend analytics page and navigation:
    - `frontend/src/app/dashboard/analytics/page.tsx`
    - `frontend/src/components/analytics/dashboard.tsx`
    - linked from sidebar + mobile nav.
  - Validation:
    - backend compile pass
    - frontend lint pass
    - live endpoint checks returned 200 + data.

- Week 4 Day 27-28 prep completed (cutover tooling/docs):
  - Added predeploy env validation script:
    - `backend/scripts/predeploy_check.py`
  - Added staging/production smoke script with analytics + export checks:
    - `backend/scripts/smoke_test_staging.py`
  - Added frontend env template:
    - `frontend/.env.example`
  - Added production cutover runbook:
    - `PRODUCTION_CUTOVER_RUNBOOK.md`
  - Updated deploy checklist with analytics + smoke-test-staging steps:
    - `DEPLOY_READY_CHECKLIST.md`
  - Landing page refactor pass finalized:
    - `frontend/src/components/landing.tsx` cleaned up and aligned to current UX/content structure.

- Week 3 Day 18-19 completion (production hardening baseline):
  - Added global API error handling middleware:
    - `backend/app/middleware/error_handler.py`
    - structured 500s now include `error_id` for support correlation.
  - Added API rate limiting middleware with org/IP scoping:
    - `backend/app/middleware/rate_limit.py`
    - execute endpoints now enforce 20 requests/minute (configurable).
  - Hardened app boot wiring in `backend/app/main.py`:
    - Sentry FastAPI integration enabled when `SENTRY_DSN` is set.
    - runtime environment tagging via `ENVIRONMENT`.
    - global handlers + rate limiter registered for all routes.
  - Added environment controls in `backend/app/settings.py` and `backend/.env.example`:
    - `ENVIRONMENT`
    - `RATE_LIMIT_ENABLED`
    - `EXECUTE_RATE_LIMIT_PER_MINUTE`
    - `DEFAULT_RATE_LIMIT_PER_MINUTE`
  - Validation executed:
    - `python -m compileall backend/app backend/scripts -q` (pass)
    - `python -c "from app.main import app"` import check (pass)
    - `npm run -s lint` in frontend (pass)
  - Day 20-21 test automation additions:
    - Added comprehensive smoke script: `backend/scripts/smoke_test_complete.py`
      - Covers health, agent catalog, router stats, memory CRUD, file endpoints, workflow validation, execute path.
    - Added load test scenario: `backend/scripts/load_test.py` (Locust user model).
    - Validation status:
      - Script compile checks pass.
      - Runtime smoke pass is currently blocked by local API timeouts on `localhost:8010`; needs a stable backend process + DB before final pass/fail signoff.

- Week 3 Day 15-17 completion (org-wide task inbox):
  - Added `task_inbox` table + indexes in `backend/app/schema.py`.
  - Added task inbox API endpoints:
    - `GET /v1/organizations/{org_id}/inbox`
    - `POST /v1/organizations/{org_id}/inbox`
    - `PUT /v1/inbox/tasks/{task_id}/status`
    - `PUT /v1/inbox/tasks/{task_id}/assign`
  - Added task board UI with Kanban-style columns and drag-drop status updates:
    - `frontend/src/components/inbox/task-board.tsx`
    - `frontend/src/app/dashboard/inbox/page.tsx`
  - Added inbox navigation links:
    - `frontend/src/components/navigation/sidebar.tsx`
    - `frontend/src/components/layout/mobile-nav.tsx`

- Week 2 Day 13-14 completion (generic webhooks):
  - Added webhook integration service with retry + exponential backoff:
    - `backend/app/integrations/webhook.py`
  - Added direct webhook test endpoint:
    - `POST /v1/webhooks/test`
  - Added webhook integration test path on stored integrations:
    - `POST /v1/integrations/{integration_id}/test` now supports `integration_type=webhook`
  - Added workflow webhook action support:
    - Workflow steps can now use `action=webhook` + `integration_id` + `action_config.payload`
  - Added webhook config UI in settings:
    - `frontend/src/components/settings/integrations.tsx`

- Week 2 Day 11-12 completion (Slack + Email integrations):
  - Added `integration_configs` table in `backend/app/schema.py`.
  - Added integration service modules:
    - `backend/app/integrations/slack.py`
    - `backend/app/integrations/email.py`
  - Added integration API endpoints:
    - `POST /v1/organizations/{org_id}/integrations`
    - `GET /v1/organizations/{org_id}/integrations`
    - `DELETE /v1/integrations/{integration_id}`
    - `POST /v1/integrations/{integration_id}/test`
  - Workflow actions support added:
    - Steps now support `action`, `integration_id`, and `action_config`.
    - Engine can execute Slack and Email actions as workflow steps.
  - Added integrations UI in settings:
    - `frontend/src/components/settings/integrations.tsx`
    - Wired into `frontend/src/app/dashboard/settings/page.tsx`

- Week 2 Day 8-10 completion (workflow system enhancement):
  - Added workflow execution engine at `backend/app/workflows/engine.py` with:
    - Definition validation
    - Variable resolution (`{{var}}`)
    - Conditional branching (`if/true/false`)
    - Dynamic next-step routing
  - Added workflow validation endpoint:
    - `POST /v1/workflows/validate`
  - Extended workflow API/models to support:
    - Step IDs, conditions, set-var, explicit next links
    - Persisted `workflow_definition` on templates
  - Upgraded workflow builder UI:
    - Step ID editing
    - Condition editor (if/true/false)
    - Variable capture field
    - Step reorder controls (up/down)

- Week 1 completion pass (feature build plan):
  - Memory system completed:
    - Added durable `agent_memories` table + indexes in `backend/app/schema.py`.
    - Added memory CRUD + auto-extract APIs:
      - `GET /v1/organizations/{org_id}/memories`
      - `POST /v1/organizations/{org_id}/memories`
      - `PUT /v1/memories/{memory_id}`
      - `DELETE /v1/memories/{memory_id}`
      - `POST /v1/organizations/{org_id}/memories/extract`
    - Added `MemoryExtractor` (`backend/app/memory/extractor.py`) with structured extraction + heuristic fallback.
    - Added memory injection into LLM execution path (`inject_memories` in `backend/app/llm/litellm_client.py`).
    - Added settings UI for memory management (`frontend/src/components/settings/memory-manager.tsx`, wired in dashboard settings page).
  - File handling completed:
    - Added `uploaded_files` table + indexes in `backend/app/schema.py`.
    - Added file upload/list/get/delete API router (`backend/app/api/files.py`):
      - `POST /v1/files/upload`
      - `GET /v1/files/{file_id}`
      - `DELETE /v1/files/{file_id}`
      - `GET /v1/organizations/{org_id}/files`
    - Added file extraction stack (`backend/app/files/extractors.py`) for PDF/DOCX/XLSX/CSV/text/images.
    - Added file context injection into execution (`inject_file_context` in `backend/app/llm/litellm_client.py`).
    - Added `file_ids` support to execute payload schema.
  - Frontend streaming/chat completion:
    - Added `StreamingResponse` SSE renderer (`frontend/src/components/agents/streaming-response.tsx`).
    - Added upload button with drag-drop and file selection UI (`frontend/src/components/agents/file-upload.tsx`).
    - Integrated both into agent chat modal with cancel support and `file_ids` forwarding.
- Validation executed:
  - Backend compile: `python -m compileall backend/app backend/scripts -q` (pass)
  - Frontend lint: `npm run -s lint` (pass)
  - Extractor module checks (memory extraction + CSV extraction) (pass)

- Workflow automation layer expanded:
  - Added workflow template persistence (`workflow_templates`) and endpoints to save/list/run templates.
  - Added recurring workflow schedules (`workflow_schedules`) with cron expression support and next-run calculation.
  - Added schedule execution endpoints (`run now` and `run due`) and run logging (`workflow_runs`).
  - My Agents workflow runner UI now supports:
    - Save workflow template
    - Create recurring workflow schedule (cron-ready)
    - Trigger scheduled runs from UI
- Web search stack completed:
  - Added `backend/app/tools/web_search.py` (Serper integration) and `backend/app/llm/search_detector.py`.
  - Integrated search into `execute_via_litellm` with `search_used` response flag.
  - Removed duplicate route-level Serper injection; routing now uses one search path in LLM client.
  - Added validation script `backend/scripts/test_web_search.py` (tool test + detector test + integrated execution test).
  - Search detection false positives fixed (`"is "` indicator removed; targeted `is ... still` regex added).
- Day 20 document retrieval completed:
  - Added `knowledge_base` table + FTS indexes in `backend/app/schema.py`.
  - Added internal document search tool `backend/app/tools/document_search.py` with FTS + keyword fallback.
  - Added seed script `backend/scripts/seed_knowledge_base.py` (7 baseline docs).
  - Integrated retrieval into `execute_via_litellm` with `docs_used` response flag.
  - Added test script `backend/scripts/test_document_search.py` and validated integrated retrieval.
- Runtime parity layer added (Copilot-style primitives):
  - Session store + memory compaction primitives (`chat_sessions`, `chat_session_messages` + `SessionManager`).
  - SSE response streaming endpoint (`POST /v1/agents/{agent_code}/execute/stream`).
  - Tool policy + reusable tool registry + pre/post tool hooks (`org_tool_policies`, `runtime_events`).
  - Org/agent model preference policy for BYOK routing (`org_model_policies`).
  - Session API endpoints (`POST/GET/DELETE /v1/sessions`) and runtime telemetry endpoint (`GET /v1/runtime/events`).
  - Production operations guidance doc added: `PRODUCTION_PATTERNS.md`.
- Domain specialisation system implemented end-to-end:
  - `domain_tags`, `related_agents`, `out_of_scope_examples` added to `agent_catalog` DB table (3 new JSONB columns).
  - Seed script (`seed_agents.py`) now carries curated domain data for all 44 agents — each with 3 specific colleague referrals.
  - `inject_domain_block()` added to prompt builder: injects domain boundaries + referral protocol at runtime (not baked into stored prompt).
  - `[REFER:CODE]` referral detection added to execute route: strips tag from visible response, resolves referred agent from DB, checks org hire status, returns `SuggestedAgent` payload with `is_hired` flag and `handoff_context`.
  - `ExecuteOut` schema extended with `referral_triggered: bool` and `suggested_agent: SuggestedAgent | None`.
- Smart router restored for all 44 agents (`enable_router_for_all.py` re-run after seed).
- Both servers confirmed running locally (backend PID 51364 on :8010, frontend PID 59156 on :3000).

## 2026-02-19
- Multi-LLM router integrated into execution path.
- Router stats endpoint added (`/v1/llm/router/stats`).
- All active agents switched to router mode.
- Synthetic training run completed for all 44 agents (25 conversations each).
- Evaluator corrected to route judge calls (removed hard Anthropic dependence in default path).
- Training defaults aligned to safer batch wait (`--wait` default now 60s).
- Week 3 Day 15 completed: bottom-performer analysis script added with CSV export (`backend/scripts/analyze_performance.py`).
- Week 3 Day 16 started: prompt patch set created and applied for 6 underperforming agents (`Author-01`, `DATA-02`, `ONBOARD-01`, `DEVOPS-01`, `QUALIFIER-01`, `SOCIAL-01`).
- Week 3 Day 16 validation tooling added: targeted re-train script with score delta CSV output (`backend/scripts/retrain_selected_agents.py`).
- Week 3 Day 16 follow-up: `QUALIFIER-01` prompt patched to v2 and re-tested (latest 25-scenario synthetic score: 89.8).
- Chat capability expansion (MVP): attachment action menu, voice input, web-search/deep-research toggles, output format selector, and referral handoff UI (`frontend/src/components/agents/agent-chat-modal.tsx` + execute context extensions).
- Execution context expanded to carry output format and attachment metadata; backend now injects these instructions into runtime prompt and can suggest specialist colleagues when inferred topic is outside current agent department.
- Web search integration (SERPER) added to execution context pipeline when `web_search=true` and `SERPER_API_KEY` is configured.
- Multi-turn memory enabled in execute path: agents now receive recent same-session history from `interaction_logs` (`MULTI_TURN_MEMORY_ENABLED`, `MULTI_TURN_MEMORY_TURNS`).
- Workflow chaining added: new endpoint `POST /v1/workflows/execute` executes hired agents sequentially with handoff context and per-step logging.
- My Agents UI now includes a Workflow Runner panel for multi-agent chains (step builder, context flags, and per-step results) wired to `POST /v1/workflows/execute`.

---

## 6) Most recent verified run (local)
- Training command:
  - `python scripts/train_all_agents.py --conversations 25 --batch-size 5`
- Result snapshot:
  - 44 agents trained
  - 1,100 conversations
  - Real non-neutral quality scores after evaluator fix
  - Some transient provider connection resets observed, run still completed

---

## 7) Deployment status
- Local environment: functional.
- Vercel one-project setup doc exists: `ONE_PROJECT_VERCEL_SETUP.md`.
- Deployment checklist exists: `DEPLOY_READY_CHECKLIST.md`.
- Production cutover still requires final env validation + smoke tests on deployed URLs.

---

## 8) How this document must be updated going forward
Update this file on every meaningful build change. For each update:
1. Change `Last updated` date.
2. Add a new dated bullet block under **Latest major completed milestones**.
3. If behavior changed, update **What is built right now** and **Known capability boundaries**.
4. If testing was run, update **Most recent verified run**.

Rule: no merge to `main` without reflecting major behavior changes here.
