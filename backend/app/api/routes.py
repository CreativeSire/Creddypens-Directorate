from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.agents.prompts import system_prompt_for_agent
from app.db import get_db
from app.llm.litellm_client import LLMError, execute_via_litellm
from app.models import AgentCatalog, HiredAgent
from app.schemas import AgentDetailOut, AgentOut
from app.schemas_chat import ChatIn, ChatOut
from app.schemas_execute import ExecuteIn, ExecuteOut
from app.settings import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "llm_mock": settings.llm_mock}


@router.get("/v1/agents", response_model=list[AgentOut])
def list_agents(department: str | None = None, db: Session = Depends(get_db)) -> list[AgentOut]:
    stmt = select(AgentCatalog)
    if department:
        dept_map: dict[str, list[str]] = {
            "customer-experience": ["Customer Experience"],
            "sales-business-dev": ["Sales & Business Dev", "Sales & Business Development", "Sales"],
            "marketing-creative": ["Marketing & Creative", "Marketing"],
            "operations-admin": ["Operations & Admin", "Operations"],
            "technical-it": ["Technical & IT", "Technical", "IT"],
            "specialized-services": ["Specialized Services", "Directorate"],
        }
        names = dept_map.get(department, [department])
        stmt = stmt.where(AgentCatalog.department.in_(names))

    result = db.execute(stmt.order_by(AgentCatalog.code.asc()))
    agents = result.scalars().all()
    out: list[AgentOut] = []
    for agent in agents:
        llm_profile = agent.llm_profile or {}
        route = llm_profile.get("default")
        out.append(
            AgentOut(
                agent_id=agent.agent_id,
                code=agent.code,
                role=agent.name,
                description=agent.description,
                department=agent.department,
                price_cents=agent.price_cents,
                status=agent.status,
                llm_route=route,
                llm_provider=agent.llm_provider,
                llm_model=agent.llm_model,
                llm_profile=llm_profile,
                operational_rating=None,
            )
        )
    return out


@router.get("/v1/organizations/{org_id}/dashboard-stats")
def get_dashboard_stats(org_id: str, db: Session = Depends(get_db)) -> dict:
    """Get dashboard overview stats for an organization (v1)."""
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)
    since_1h = datetime.now(timezone.utc) - timedelta(hours=1)

    hired_count = db.execute(
        text("select count(*)::int from hired_agents where org_id = :org_id and status = 'active'"),
        {"org_id": org_id},
    ).scalar_one()

    tasks_this_week = db.execute(
        text("select count(*)::int from interaction_logs where org_id = :org_id and created_at >= :since"),
        {"org_id": org_id, "since": since_7d},
    ).scalar_one()

    avg_latency = db.execute(
        text("select coalesce(avg(latency_ms), 0)::float from interaction_logs where org_id = :org_id and created_at >= :since"),
        {"org_id": org_id, "since": since_7d},
    ).scalar_one()

    recent = db.execute(
        text(
            """
            select
              il.agent_code,
              ac.name as agent_name,
              il.message,
              il.created_at,
              il.latency_ms
            from interaction_logs il
            join agent_catalog ac on ac.code = il.agent_code
            where il.org_id = :org_id
            order by il.created_at desc
            limit 10;
            """
        ),
        {"org_id": org_id},
    ).mappings().all()

    def summarize(msg: str) -> str:
        s = (msg or "").strip().replace("\n", " ")
        if len(s) > 50:
            return s[:50] + "..."
        return s

    activities: list[dict] = []
    for r in recent:
        created_at = r["created_at"]
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        activities.append(
            {
                "agent_code": r["agent_code"],
                "agent_name": r["agent_name"],
                "task_summary": summarize(r["message"] or ""),
                "timestamp": created_at,
                "latency_ms": int(r["latency_ms"] or 0),
            }
        )

    active_agents_count = db.execute(
        text("select count(distinct agent_code)::int from interaction_logs where org_id = :org_id and created_at >= :since"),
        {"org_id": org_id, "since": since_1h},
    ).scalar_one()

    return {
        "hired_agents_count": int(hired_count or 0),
        "active_agents_count": int(active_agents_count or 0),
        "tasks_this_week": int(tasks_this_week or 0),
        "avg_response_time_ms": int(round(float(avg_latency or 0))),
        "recent_activities": activities,
    }


@router.get("/v1/agents/{agent_code}", response_model=AgentDetailOut)
def get_agent(agent_code: str, db: Session = Depends(get_db)) -> AgentDetailOut:
    from fastapi import HTTPException

    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    llm_profile = agent.llm_profile or {}
    route = llm_profile.get("default")
    return AgentDetailOut(
        agent_id=agent.agent_id,
        code=agent.code,
        role=agent.name,
        description=agent.description,
        department=agent.department,
        price_cents=agent.price_cents,
        status=agent.status,
        llm_route=route,
        llm_provider=agent.llm_provider,
        llm_model=agent.llm_model,
        llm_profile=llm_profile,
        operational_rating=None,
        system_prompt=agent.system_prompt or "",
    )


@router.post("/v1/agents/{code}/chat", response_model=ChatOut)
def chat_with_agent(code: str, payload: ChatIn, db: Session = Depends(get_db)) -> ChatOut:
    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == code)).scalars().first()
    if not agent:
        # Keep behavior simple for v1: 404 if unknown code.
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status != "active":
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="Agent is not active")

    llm_profile = agent.llm_profile or {}
    route = llm_profile.get("default")

    system = system_prompt_for_agent(code)
    try:
        # Legacy demo route; for production use the /execute endpoint which reads provider/model from DB.
        if not agent.llm_provider or not agent.llm_model:
            raise LLMError("Agent LLM provider/model is not configured.")
        result = execute_via_litellm(
            provider=agent.llm_provider,
            model=agent.llm_model,
            system=system,
            user=payload.message,
        )
    except LLMError as e:
        # Return a deterministic, testable error message without leaking internals.
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail=str(e)) from e

    return ChatOut(
        reply=result.get("response") or "",
        llm_provider=agent.llm_provider,
        llm_route=route,
        llm_model=agent.llm_model,
    )


@router.post("/v1/agents/{agent_code}/hire")
def hire_agent(
    agent_code: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    from fastapi import HTTPException
    import json
    import uuid

    org_id = x_org_id or "org_test"
    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != "active":
        raise HTTPException(status_code=409, detail="Agent is not active")

    # Ensure org exists (minimal v1)
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )

    # Upsert hired agent
    default_cfg = {"company_name": "", "tone": "", "additional": {}}
    db.execute(
        text(
            """
            insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
            values (:id, :org_id, :agent_code, 'active', cast(:cfg as jsonb))
            on conflict (org_id, agent_code) do update set status='active', updated_at=now();
            """
        ),
        {"id": str(uuid.uuid4()), "org_id": org_id, "agent_code": agent_code, "cfg": json.dumps(default_cfg)},
    )
    db.commit()

    return {"ok": True, "org_id": org_id, "agent_code": agent_code, "status": "active"}


@router.post("/v1/agents/{agent_code}/checkout")
def mock_checkout(
    agent_code: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    """
    Mock checkout endpoint - simulates Stripe without charging.
    In production this will be replaced by a real Stripe checkout + subscription flow.
    """
    from fastapi import HTTPException
    import json
    import uuid

    org_id = x_org_id or "org_test"

    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != "active":
        raise HTTPException(status_code=409, detail="Agent is not active")

    existing = (
        db.execute(
            select(HiredAgent)
            .where(HiredAgent.org_id == org_id)
            .where(HiredAgent.agent_code == agent_code)
            .where(HiredAgent.status == "active")
        )
        .scalars()
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Agent already hired")

    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )

    mock_sub_id = f"mock_sub_{uuid.uuid4().hex[:12]}"
    default_cfg = {"company_name": "", "tone": "", "additional": {"mock_subscription_id": mock_sub_id}}

    db.execute(
        text(
            """
            insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
            values (:id, :org_id, :agent_code, 'active', cast(:cfg as jsonb));
            """
        ),
        {"id": str(uuid.uuid4()), "org_id": org_id, "agent_code": agent_code, "cfg": json.dumps(default_cfg)},
    )
    db.commit()

    return {
        "success": True,
        "agent_code": agent_code,
        "message": "Agent hired successfully (mock checkout - no payment processed)",
        "stripe_subscription_id": mock_sub_id,
    }


@router.get("/v1/organizations/{org_id}/agents")
def list_org_agents(org_id: str, include_stats: bool = False, db: Session = Depends(get_db)) -> dict | list[dict]:
    """
    Default response (include_stats=0): legacy shape used by the v1 Command Center.
    include_stats=1: dashboard shape used by /dashboard/my-agents with per-agent today stats.
    """

    if not include_stats:
        rows = db.execute(
            text(
                """
                select
                  ha.agent_code,
                  ha.status as hire_status,
                  ha.configuration,
                  ac.name as role,
                  ac.department,
                  ac.price_cents
                from hired_agents ha
                join agent_catalog ac on ac.code = ha.agent_code
                where ha.org_id = :org_id
                order by ha.agent_code asc;
                """
            ),
            {"org_id": org_id},
        ).mappings().all()
        return {"org_id": org_id, "agents": [dict(r) for r in rows]}

    start_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    rows = db.execute(
        text(
            """
            select
              ha.hired_agent_id,
              ha.status,
              ha.created_at,
              ac.code as agent_code,
              ac.name as agent_name,
              ac.name as agent_role,
              ac.department,
              ac.llm_provider,
              ac.llm_model,
              coalesce(s.tasks_today, 0)::int as tasks_today,
              coalesce(s.avg_latency_ms, 0)::float as avg_latency_ms
            from hired_agents ha
            join agent_catalog ac on ac.code = ha.agent_code
            left join (
              select
                agent_code,
                count(*) as tasks_today,
                avg(latency_ms) as avg_latency_ms
              from interaction_logs
              where org_id = :org_id and created_at >= :start_today
              group by agent_code
            ) s on s.agent_code = ha.agent_code
            where ha.org_id = :org_id and ha.status = 'active'
            order by ha.created_at desc, ha.agent_code asc;
            """
        ),
        {"org_id": org_id, "start_today": start_today},
    ).mappings().all()

    out: list[dict] = []
    for r in rows:
        created_at = r["created_at"]
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        out.append(
            {
                "id": str(r["hired_agent_id"]),
                "agent": {
                    "agent_code": r["agent_code"],
                    "name": r["agent_name"],
                    "role": r["agent_role"],
                    "department": r["department"],
                    "llm_provider": r["llm_provider"],
                    "llm_model": r["llm_model"],
                },
                "stats": {
                    "tasks_today": int(r["tasks_today"] or 0),
                    "avg_latency_ms": int(round(float(r["avg_latency_ms"] or 0))),
                    "quality_score": 0,
                },
                "status": r["status"],
                "hired_at": created_at,
            }
        )

    return out


@router.post("/v1/auth/bootstrap")
def auth_bootstrap(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict:
    """
    Validates a Supabase access token (via Supabase Auth) and ensures local org + user records exist.
    Returns org_id used for X-Org-Id header on subsequent API calls.
    """
    from fastapi import HTTPException
    import requests

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured on the backend")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    access_token = authorization.split(" ", 1)[1].strip()
    try:
        r = requests.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail="Failed to reach Supabase") from e

    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    data = r.json()
    user_id = data.get("id") or ""
    email = data.get("email") or ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # One org per user for v1: deterministic org id
    org_id = f"org_{user_id}"

    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )
    db.execute(
        text(
            "insert into users (user_id, org_id, email) values (:user_id, :org_id, :email) "
            "on conflict (user_id) do update set org_id=excluded.org_id, email=excluded.email"
        ),
        {"user_id": user_id, "org_id": org_id, "email": email},
    )
    db.commit()
    return {"org_id": org_id, "user_id": user_id, "email": email}


@router.post("/v1/director/recommend")
def director_recommend(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    v1: In mock mode, uses heuristic matching over the agent catalog.
    When LLM_MOCK is off, this should route through LiteLLM with The Director system prompt.
    """
    from fastapi import HTTPException
    from app.settings import settings

    message = (payload.get("message") or "").strip()
    org_id = (payload.get("org_id") or "").strip() or "org_test"
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    agents = db.execute(select(AgentCatalog).order_by(AgentCatalog.code.asc())).scalars().all()
    text_lower = message.lower()

    def score(a: AgentCatalog) -> int:
        s = 0
        role = (a.name or "").lower()
        dept = (a.department or "").lower()
        desc = (a.description or "").lower()
        for w in [role, dept, desc]:
            if "support" in text_lower and "customer" in w:
                s += 3
            if "content" in text_lower and "content" in w:
                s += 3
            if "writer" in text_lower and "writer" in w:
                s += 3
            if "assistant" in text_lower and "assistant" in w:
                s += 3
            if any(k in text_lower for k in ["sales", "lead", "crm"]) and any(k in w for k in ["sales", "lead", "crm"]):
                s += 2
            if any(k in text_lower for k in ["book", "invoice", "expense"]) and any(
                k in w for k in ["book", "invoice", "expense"]
            ):
                s += 2
        if a.status == "active":
            s += 1
        return s

    ranked = sorted(agents, key=score, reverse=True)
    top = [a for a in ranked if score(a) > 0][:3] or ranked[:3]

    recs = []
    for a in top:
        recs.append(
            {
                "agent_code": a.code,
                "agent_name": a.name,
                "role": a.name,
                "reasoning": "Recommended based on your request and the Directorate catalog.",
                "price_monthly": a.price_cents,
                "department": a.department,
            }
        )

    return {
        "message": (
            "Based on your needs, here are the best assets to deploy first. "
            "If you tell me your industry and tone preference, I can refine the recommendation."
        ),
        "recommendations": recs,
        "org_id": org_id,
        "mock": settings.llm_mock,
    }


@router.post("/v1/agents/{agent_code}/execute", response_model=ExecuteOut)
def execute_agent(
    agent_code: str,
    payload: ExecuteIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> ExecuteOut:
    from fastapi import HTTPException
    import uuid

    org_id = x_org_id or "org_test"

    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate hired agent record for org (mock org_test in v1 dev)
    hired = (
        db.execute(
            select(HiredAgent)
            .where(HiredAgent.org_id == org_id)
            .where(HiredAgent.agent_code == agent_code)
            .where(HiredAgent.status == "active")
        )
        .scalars()
        .first()
    )
    if not hired:
        raise HTTPException(status_code=403, detail="Agent not hired for organization")

    if not agent.llm_provider or not agent.llm_model:
        raise HTTPException(status_code=503, detail="Agent model routing is not configured")

    system_prompt = (agent.system_prompt or "").strip() or system_prompt_for_agent(agent_code)
    context_lines: list[str] = []
    if payload.context.company_name:
        context_lines.append(f"Company: {payload.context.company_name}")
    if payload.context.tone:
        context_lines.append(f"Tone: {payload.context.tone}")
    if payload.context.additional:
        context_lines.append(f"Additional: {payload.context.additional}")
    if context_lines:
        system_prompt = system_prompt + "\n\nClient Context:\n" + "\n".join(context_lines)

    trace_id = str(uuid.uuid4())
    try:
        result = execute_via_litellm(
            provider=agent.llm_provider,
            model=agent.llm_model,
            system=system_prompt,
            user=payload.message,
            trace_id=trace_id,
        )
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    # Best-effort interaction log for dashboard stats / activity feed.
    try:
        db.execute(
            text(
                """
                insert into interaction_logs
                  (org_id, agent_code, session_id, message, response, model_used, latency_ms, trace_id)
                values
                  (:org_id, :agent_code, :session_id, :message, :response, :model_used, :latency_ms, :trace_id);
                """
            ),
            {
                "org_id": org_id,
                "agent_code": agent_code,
                "session_id": payload.session_id or "",
                "message": payload.message,
                "response": result.get("response") or "",
                "model_used": result.get("model_used") or "",
                "latency_ms": int(result.get("latency_ms") or 0),
                "trace_id": result.get("trace_id") or trace_id,
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return ExecuteOut(
        agent_code=agent_code,
        response=result.get("response") or "",
        model_used=result["model_used"],
        latency_ms=int(result["latency_ms"]),
        trace_id=result["trace_id"],
        session_id=payload.session_id,
    )
