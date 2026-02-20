# CreddyPens Runtime Production Patterns

This document captures the platform patterns implemented to mirror enterprise agent runtimes.

## 1) Long chat memory + safe compaction
- Session state tables:
  - `chat_sessions`
  - `chat_session_messages`
- Runtime manager: `backend/app/runtime/session_manager.py`
- Behavior:
  - Every request attaches recent session history + compacted summary.
  - When turn threshold is exceeded (`SESSION_COMPACTION_TURNS`), older messages are compacted into bounded summary text and removed.
  - Session limits are enforced per org (`SESSION_MAX_PARALLEL_PER_ORG`).

## 2) Live streaming responses
- Endpoint: `POST /v1/agents/{agent_code}/execute/stream`
- Emits SSE events:
  - `meta` (trace/session/model)
  - `token` (incremental partial text)
  - `done` (final payload and metadata)

## 3) Tool permissions + hooks
- Policy table: `org_tool_policies`
- Policy service: `backend/app/runtime/tool_policy.py`
- Hook bus + audit store: `backend/app/runtime/hooks.py`
- Tool registry: `backend/app/runtime/tool_registry.py`
- Endpoints:
  - `GET /v1/tools`
  - `POST /v1/tools/run`
  - `GET /v1/tool-policies`
  - `POST /v1/tool-policies`
- Every tool call emits `tool.pre_call` and `tool.post_call` events to `runtime_events`.

## 4) Session management at scale
- Endpoints:
  - `POST /v1/sessions`
  - `GET /v1/sessions`
  - `DELETE /v1/sessions/{session_id}`
- Session isolation is org-scoped by `X-Org-Id`.
- Session metadata includes turn counts, compaction counts, and activity timestamps.

## 5) Reusable custom tool architecture
- Registry-based tool execution (web/docs today, extensible for CRM/actions).
- Structured args + structured result envelope (`ok`, `data`/`error`).
- Centralized policy checks and runtime event hooks around each call.

## 6) BYOK/org model policy layer
- Policy table: `org_model_policies`
- Service: `backend/app/runtime/model_policy.py`
- Applied in `execute_via_litellm` before routing:
  - org-level preferred provider/model
  - optional per-agent override
- Endpoints:
  - `GET /v1/model-policies`
  - `POST /v1/model-policies`
- Router catalog endpoint:
  - `GET /v1/llm/router/catalog`

## 7) Operational telemetry + audit
- Event table: `runtime_events`
- Events emitted for:
  - request start/error/complete
  - tool pre/post call
- Endpoint:
  - `GET /v1/runtime/events`

## 8) Safe deployment/operations checklist
1. Enable per-org limits (`SESSION_MAX_PARALLEL_PER_ORG`) for abuse control.
2. Enable compaction (`SESSION_COMPACTION_ENABLED`) for bounded context.
3. Restrict high-risk tools with `org_tool_policies` default-deny.
4. Persist and review `runtime_events` for audit trails.
5. Use org-scoped model policies for cost/performance control.
6. Run with sticky sessions or shared DB-backed session store for horizontal scaling.
7. Add distributed locking if multiple workers may execute the same recurring workflow/session concurrently.
8. Monitor:
   - session counts
   - compaction frequency
   - tool deny rates
   - model/provider latency and error rates

