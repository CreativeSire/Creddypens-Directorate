from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.agents.prompts import system_prompt_for_agent
from app.db import get_db
from app.llm.litellm_client import LLMError, execute_via_litellm
from app.llm.multi_router import get_multi_llm_router
from app.models import AgentCatalog, HiredAgent
from app.schemas import AgentDetailOut, AgentOut
from app.schemas_chat import ChatIn, ChatOut
from app.schemas_execute import ExecuteIn, ExecuteOut
from app.settings import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "llm_mock": settings.llm_mock}


@router.get("/v1/llm/router/stats")
def llm_router_stats() -> dict:
    return get_multi_llm_router().cost_summary()


@router.get("/v1/agents", response_model=list[AgentOut])
def list_agents(department: str | None = None, db: Session = Depends(get_db)) -> list[AgentOut]:
    stmt = select(AgentCatalog)
    if department:
        dept_map: dict[str, list[str]] = {
            "customer-experience": ["Customer Experience", "CUSTOMER EXPERIENCE"],
            "sales-business-dev": ["Sales & Business Dev", "Sales & Business Development", "SALES & BUSINESS DEVELOPMENT", "Sales"],
            "marketing-creative": ["Marketing & Creative", "MARKETING & CREATIVE", "Marketing"],
            "operations-admin": ["Operations & Admin", "OPERATIONS & ADMIN", "Operations"],
            "technical-it": ["Technical & IT", "TECHNICAL & IT", "Technical", "IT"],
            "specialized-services": ["Specialized Services", "SPECIALIZED SERVICES", "Directorate"],
        }
        names = dept_map.get(department, [department])
        stmt = stmt.where(AgentCatalog.department.in_(names))

    result = db.execute(stmt.order_by(AgentCatalog.code.asc()))
    agents = result.scalars().all()
    out: list[AgentOut] = []
    for agent in agents:
        out.append(
            AgentOut(
                agent_id=agent.agent_id,
                code=agent.code,
                role=agent.name,
                human_name=agent.human_name,
                tagline=agent.tagline,
                description=agent.description,
                capabilities=list(agent.capabilities or []),
                ideal_for=agent.ideal_for,
                personality=agent.personality,
                communication_style=agent.communication_style,
                department=agent.department,
                price_cents=agent.price_cents,
                status=agent.status,
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
    avg_quality = db.execute(
        text("select coalesce(avg(quality_score), 0)::float from interaction_logs where org_id = :org_id and created_at >= :since"),
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
        "avg_quality_score": round(float(avg_quality or 0), 2),
        "recent_activities": activities,
    }


@router.get("/v1/agents/{agent_code}", response_model=AgentDetailOut)
def get_agent(agent_code: str, db: Session = Depends(get_db)) -> AgentDetailOut:
    from fastapi import HTTPException

    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentDetailOut(
        agent_id=agent.agent_id,
        code=agent.code,
        role=agent.name,
        human_name=agent.human_name,
        tagline=agent.tagline,
        description=agent.description,
        capabilities=list(agent.capabilities or []),
        ideal_for=agent.ideal_for,
        personality=agent.personality,
        communication_style=agent.communication_style,
        profile=agent.profile or "",
        operational_sections=list(agent.operational_sections or []),
        department=agent.department,
        price_cents=agent.price_cents,
        status=agent.status,
        operational_rating=None,
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

    system = system_prompt_for_agent(code)
    try:
        # Legacy demo route; for production use the /execute endpoint which reads provider/model from DB.
        if (not agent.llm_provider or not agent.llm_model) and not settings.multi_llm_router_enabled:
            raise LLMError("Agent LLM provider/model is not configured.")
        result = execute_via_litellm(
            provider=agent.llm_provider or "",
            model=agent.llm_model or "",
            system=system,
            user=payload.message,
        )
    except LLMError as e:
        # Return a deterministic, testable error message without leaking internals.
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail=str(e)) from e

    return ChatOut(reply=result.get("response") or result.get("content") or result.get("text") or "")


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
def create_checkout(
    agent_code: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    origin: str | None = Header(default=None, alias="Origin"),
) -> dict:
    """
    Checkout endpoint.
    - If STRIPE_SECRET_KEY is configured, creates a Stripe Checkout Session.
    - Otherwise falls back to mock checkout and activates immediately.
    """
    from fastapi import HTTPException
    import json
    import uuid
    import requests

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

    # Create org if needed.
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )

    frontend_origin = (origin or "").strip().rstrip("/")
    if not frontend_origin:
        if settings.checkout_success_url:
            frontend_origin = settings.checkout_success_url.split("/dashboard")[0].rstrip("/")
        elif settings.allowed_origins:
            frontend_origin = settings.allowed_origins.split(",")[0].strip().rstrip("/")

    success_url = (
        settings.checkout_success_url
        or f"{frontend_origin}/dashboard/my-agents?checkout=success"
        or "http://localhost:3000/dashboard/my-agents?checkout=success"
    )
    cancel_url = (
        settings.checkout_cancel_url
        or f"{frontend_origin}/dashboard/agents/{agent_code}?checkout=cancelled"
        or f"http://localhost:3000/dashboard/agents/{agent_code}?checkout=cancelled"
    )

    # Stripe-enabled path (real checkout session) with automatic fallback to mock on failure.
    if settings.stripe_secret_key:
        try:
            stripe_payload = {
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "client_reference_id": f"{org_id}:{agent_code}",
                "metadata[org_id]": org_id,
                "metadata[agent_code]": agent_code,
                "line_items[0][price_data][currency]": "usd",
                "line_items[0][price_data][unit_amount]": str(int(agent.price_cents)),
                "line_items[0][price_data][product_data][name]": f"{agent.code} — {agent.name}",
                "line_items[0][price_data][product_data][description]": (
                    (agent.tagline or agent.description or "CreddyPens agent subscription")[:450]
                ),
                "line_items[0][price_data][recurring][interval]": "month",
                "line_items[0][quantity]": "1",
            }
            resp = requests.post(
                "https://api.stripe.com/v1/checkout/sessions",
                headers={"Authorization": f"Bearer {settings.stripe_secret_key}"},
                data=stripe_payload,
                timeout=20,
            )
            if resp.status_code >= 400:
                detail = f"Stripe checkout creation failed ({resp.status_code})"
                try:
                    stripe_err = resp.json().get("error", {}).get("message")
                    if stripe_err:
                        detail = f"{detail}: {stripe_err}"
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail=detail)

            session = resp.json()
            checkout_session_id = session.get("id", "")
            checkout_url = session.get("url", "")

            cfg = {
                "company_name": "",
                "tone": "",
                "additional": {"stripe_checkout_session_id": checkout_session_id, "checkout_mode": "stripe"},
            }
            db.execute(
                text(
                    """
                    insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
                    values (:id, :org_id, :agent_code, 'active', cast(:cfg as jsonb));
                    """
                ),
                {"id": str(uuid.uuid4()), "org_id": org_id, "agent_code": agent_code, "cfg": json.dumps(cfg)},
            )
            db.commit()

            return {
                "success": True,
                "mode": "stripe",
                "agent_code": agent_code,
                "message": "Checkout session created.",
                "checkout_session_id": checkout_session_id,
                "checkout_url": checkout_url,
            }
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"Stripe checkout failed: {exc.__class__.__name__}") from exc

    # Mock fallback path.
    mock_sub_id = f"mock_sub_{uuid.uuid4().hex[:12]}"
    cfg = {"company_name": "", "tone": "", "additional": {"mock_subscription_id": mock_sub_id, "checkout_mode": "mock"}}
    db.execute(
        text(
            """
            insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
            values (:id, :org_id, :agent_code, 'active', cast(:cfg as jsonb));
            """
        ),
        {"id": str(uuid.uuid4()), "org_id": org_id, "agent_code": agent_code, "cfg": json.dumps(cfg)},
    )
    db.commit()

    return {
        "success": True,
        "mode": "mock",
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
              coalesce(ac.human_name, ac.name) as agent_name,
              ac.name as agent_role,
              ac.department,
              coalesce(s.tasks_today, 0)::int as tasks_today,
              coalesce(s.avg_latency_ms, 0)::float as avg_latency_ms,
              coalesce(s.avg_quality_score, 0)::float as avg_quality_score
            from hired_agents ha
            join agent_catalog ac on ac.code = ha.agent_code
            left join (
              select
                agent_code,
                count(*) as tasks_today,
                avg(latency_ms) as avg_latency_ms,
                avg(quality_score) as avg_quality_score
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
                },
                "stats": {
                    "tasks_today": int(r["tasks_today"] or 0),
                    "avg_latency_ms": int(round(float(r["avg_latency_ms"] or 0))),
                    "quality_score": round(float(r["avg_quality_score"] or 0), 2),
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

    if settings.llm_mock:
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
            "mock": True,
        }

    fallback_lookup = {a.code: a for a in top}
    catalog_brief = [
        {
            "agent_code": a.code,
            "role": a.name,
            "department": a.department,
            "price_monthly": a.price_cents,
            "tagline": a.tagline or "",
        }
        for a in top
    ]
    system_prompt = (
        "You are The Director of The CreddyPens Directorate. Analyze the user's need and recommend up to 3 best-fit "
        "agents from the provided catalog. Respond as strict JSON only with keys: message, recommendations. "
        "recommendations must be an array of objects with keys: agent_code, role, reasoning."
    )
    user_prompt = json.dumps({"user_message": message, "catalog": catalog_brief})
    try:
        result = execute_via_litellm(
            provider="anthropic",
            model=settings.anthropic_sonnet_model or "claude-sonnet-4-5-20250929",
            system=system_prompt,
            user=user_prompt,
        )
        raw_text = (result.get("response") or "").strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json\n", "", 1).strip()
        parsed = json.loads(raw_text)
        recs = []
        for rec in parsed.get("recommendations", [])[:3]:
            code = (rec.get("agent_code") or "").strip()
            agent = fallback_lookup.get(code)
            if not agent:
                continue
            recs.append(
                {
                    "agent_code": agent.code,
                    "agent_name": agent.name,
                    "role": rec.get("role") or agent.name,
                    "reasoning": rec.get("reasoning") or "Recommended based on intent match.",
                    "price_monthly": agent.price_cents,
                    "department": agent.department,
                }
            )
        if not recs:
            raise ValueError("empty recommendation set")
        return {
            "message": parsed.get("message")
            or "Here are the strongest fits from the Directorate based on your request.",
            "recommendations": recs,
            "org_id": org_id,
            "mock": False,
        }
    except Exception:
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
            "message": "I mapped your request to the closest operational assets.",
            "recommendations": recs,
            "org_id": org_id,
            "mock": False,
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

    if (not agent.llm_provider or not agent.llm_model) and not settings.multi_llm_router_enabled:
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
    quality_score = 0.85
    try:
        result = execute_via_litellm(
            provider=agent.llm_provider or "",
            model=agent.llm_model or "",
            system=system_prompt,
            user=payload.message,
            trace_id=trace_id,
        )
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    response_text = result.get("response") or result.get("content") or result.get("text") or ""
    tokens_used = int(result.get("tokens_used") or 0)

    interaction_id: str | None = None

    # Best-effort interaction log for dashboard stats / activity feed.
    try:
        params = {
            "org_id": org_id,
            "agent_code": agent_code,
            "session_id": payload.session_id or "",
            "message": payload.message,
            "response": response_text,
            "model_used": result.get("model_used") or "",
            "latency_ms": int(result.get("latency_ms") or 0),
            "tokens_used": tokens_used,
            "quality_score": quality_score,
            "trace_id": result.get("trace_id") or trace_id,
        }

        # Prefer RETURNING when supported so the frontend can attach feedback.
        row = db.execute(
            text(
                """
                insert into interaction_logs
                  (org_id, agent_code, session_id, message, response, model_used, latency_ms, tokens_used, quality_score, trace_id)
                values
                  (:org_id, :agent_code, :session_id, :message, :response, :model_used, :latency_ms, :tokens_used, :quality_score, :trace_id)
                returning interaction_id;
                """
            ),
            params,
        ).mappings().first()

        if row and row.get("interaction_id"):
            interaction_id = str(row["interaction_id"])
        db.commit()
    except Exception:
        db.rollback()

    return ExecuteOut(
        agent_code=agent_code,
        response=response_text,
        model_used=result["model_used"],
        latency_ms=int(result["latency_ms"]),
        tokens_used=tokens_used,
        interaction_id=interaction_id,
        trace_id=result["trace_id"],
        session_id=payload.session_id,
    )


@router.get("/v1/organizations/{org_id}/agents/{agent_code}/stats")
def get_agent_stats(org_id: str, agent_code: str, period: str = "today", db: Session = Depends(get_db)) -> dict:
    from fastapi import HTTPException

    if period == "today":
        since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        since = datetime.now(timezone.utc) - timedelta(days=7)
    else:
        raise HTTPException(status_code=400, detail="Unsupported period. Use today|week")

    row = db.execute(
        text(
            """
            select
              count(*)::int as tasks_count,
              coalesce(avg(latency_ms), 0)::float as avg_latency_ms,
              coalesce(avg(quality_score), 0)::float as avg_quality_score,
              coalesce(sum(tokens_used), 0)::int as tokens_used
            from interaction_logs
            where org_id = :org_id and agent_code = :agent_code and created_at >= :since;
            """
        ),
        {"org_id": org_id, "agent_code": agent_code, "since": since},
    ).mappings().first()

    online = db.execute(
        text(
            """
            select count(*)::int
            from interaction_logs
            where org_id = :org_id and agent_code = :agent_code and created_at >= :since;
            """
        ),
        {"org_id": org_id, "agent_code": agent_code, "since": datetime.now(timezone.utc) - timedelta(hours=1)},
    ).scalar_one()

    return {
        "agent_code": agent_code,
        "tasks_count": int((row or {}).get("tasks_count") or 0),
        "avg_latency_ms": int(round(float((row or {}).get("avg_latency_ms") or 0))),
        "avg_quality_score": round(float((row or {}).get("avg_quality_score") or 0), 2),
        "tokens_used": int((row or {}).get("tokens_used") or 0),
        "status": "online" if int(online or 0) > 0 else "idle",
    }


@router.get("/v1/organizations/{org_id}/academy-status")
def academy_status(org_id: str, db: Session = Depends(get_db)) -> dict:
    recent_runs = db.execute(
        text(
            """
            select
              tr.agent_code,
              coalesce(ac.human_name, ac.name) as trainer_id,
              tr.avg_quality_score as score,
              tr.passed,
              tr.completed_at
            from training_runs tr
            left join agent_catalog ac on ac.code = tr.agent_code
            where tr.org_id is null or tr.org_id = :org_id
            order by tr.started_at desc
            limit 10;
            """
        ),
        {"org_id": org_id},
    ).mappings().all()

    in_progress = db.execute(
        text(
            "select count(*)::int from training_runs where (org_id is null or org_id = :org_id) and status = 'running';"
        ),
        {"org_id": org_id},
    ).scalar_one()

    avg_quality = db.execute(
        text(
            """
            select coalesce(avg(avg_quality_score), 0)::float
            from training_runs
            where (org_id is null or org_id = :org_id) and avg_quality_score is not null;
            """
        ),
        {"org_id": org_id},
    ).scalar_one()

    trend = db.execute(
        text(
            """
            with latest as (
              select coalesce(avg(s.avg_quality_score), 0)::float as val
              from (
                select avg_quality_score
                from training_runs
                where (org_id is null or org_id = :org_id) and avg_quality_score is not null
                order by started_at desc
                limit 5
              ) s
            ), prev as (
              select coalesce(avg(s.avg_quality_score), 0)::float as val
              from (
                select avg_quality_score
                from training_runs
                where (org_id is null or org_id = :org_id) and avg_quality_score is not null
                order by started_at desc
                offset 5
                limit 5
              ) s
            )
            select (select val from latest) - (select val from prev) as diff;
            """
        ),
        {"org_id": org_id},
    ).scalar_one()

    sessions = []
    for item in recent_runs:
        completed_at = item["completed_at"]
        if hasattr(completed_at, "isoformat"):
            completed_at = completed_at.isoformat()
        sessions.append(
            {
                "agent_code": item["agent_code"],
                "trainer_id": item["trainer_id"] or "TRAINER-CORE",
                "score": round(float(item["score"] or 0), 2),
                "passed": bool(item["passed"]),
                "completed_at": completed_at,
            }
        )

    trend_value = round(float(trend or 0), 2)
    return {
        "agents_in_training": int(in_progress or 0),
        "avg_quality_score": round(float(avg_quality or 0), 2),
        "quality_trend": f"{trend_value:+.2f}",
        "next_cycle_hours": 14,
        "recent_sessions": sessions,
    }


@router.post("/v1/academy/evaluate")
def academy_evaluate(payload: dict, db: Session = Depends(get_db)) -> dict:
    from fastapi import HTTPException

    org_id = (payload.get("org_id") or "").strip() or "org_test"
    interaction_id = (payload.get("interaction_log_id") or "").strip()
    agent_code = (payload.get("agent_code") or "").strip()
    if not agent_code:
        raise HTTPException(status_code=400, detail="agent_code is required")
    quality_score = float(payload.get("quality_score") or 0)
    criteria = payload.get("criteria") or {}
    notes = (payload.get("notes") or "").strip() or None
    evaluated_by = (payload.get("evaluated_by") or "auto").strip() or "auto"

    row = db.execute(
        text(
            """
            insert into response_evaluations (interaction_id, org_id, agent_code, quality_score, evaluation_criteria, evaluated_by, notes)
            values (nullif(:interaction_id, '')::uuid, :org_id, :agent_code, :quality_score, cast(:criteria as jsonb), :evaluated_by, :notes)
            returning evaluation_id, evaluated_at;
            """
        ),
        {
            "interaction_id": interaction_id,
            "org_id": org_id,
            "agent_code": agent_code,
            "quality_score": quality_score,
            "criteria": json.dumps(criteria),
            "evaluated_by": evaluated_by,
            "notes": notes,
        },
    ).mappings().first()
    db.commit()

    return {"ok": True, "evaluation_id": str(row["evaluation_id"]), "evaluated_at": row["evaluated_at"].isoformat()}


@router.post("/v1/academy/train/{agent_code}")
def academy_train(agent_code: str, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or {}
    org_id = (payload.get("org_id") or "").strip() or "org_test"
    run_type = (payload.get("run_type") or "synthetic").strip() or "synthetic"
    scenario_count = int(payload.get("scenario_count") or 100)

    avg_quality_score = 0.82
    improvements = {
        "focus": ["response precision", "tone consistency", "faster first-sentence clarity"],
        "next_actions": ["add edge-case scenarios", "tighten escalation phrasing"],
    }
    row = db.execute(
        text(
            """
            insert into training_runs
              (org_id, agent_code, run_type, status, scenarios_tested, avg_quality_score, improvements_identified, passed, completed_at)
            values
              (:org_id, :agent_code, :run_type, 'completed', :scenarios_tested, :avg_quality_score, cast(:improvements as jsonb), :passed, now())
            returning training_run_id, started_at, completed_at;
            """
        ),
        {
            "org_id": org_id,
            "agent_code": agent_code,
            "run_type": run_type,
            "scenarios_tested": scenario_count,
            "avg_quality_score": avg_quality_score,
            "improvements": json.dumps(improvements),
            "passed": avg_quality_score >= 0.75,
        },
    ).mappings().first()
    db.commit()

    return {
        "ok": True,
        "training_run_id": str(row["training_run_id"]),
        "agent_code": agent_code,
        "run_type": run_type,
        "status": "completed",
        "scenarios_tested": scenario_count,
        "avg_quality_score": avg_quality_score,
        "started_at": row["started_at"].isoformat(),
        "completed_at": row["completed_at"].isoformat(),
    }


@router.get("/v1/academy/progress/{agent_code}")
def academy_progress(agent_code: str, org_id: str = "org_test", db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        text(
            """
            select training_run_id, run_type, status, scenarios_tested, avg_quality_score, started_at, completed_at
            from training_runs
            where agent_code = :agent_code and (org_id = :org_id or org_id is null)
            order by started_at desc
            limit 20;
            """
        ),
        {"agent_code": agent_code, "org_id": org_id},
    ).mappings().all()

    runs = []
    for row in rows:
        runs.append(
            {
                "training_run_id": str(row["training_run_id"]),
                "run_type": row["run_type"],
                "status": row["status"],
                "scenarios_tested": int(row["scenarios_tested"] or 0),
                "avg_quality_score": round(float(row["avg_quality_score"] or 0), 2),
                "started_at": row["started_at"].isoformat() if hasattr(row["started_at"], "isoformat") else row["started_at"],
                "completed_at": row["completed_at"].isoformat() if hasattr(row["completed_at"], "isoformat") else row["completed_at"],
            }
        )

    return {"agent_code": agent_code, "runs": runs, "latest": runs[0] if runs else None}


@router.post("/v1/academy/optimize-prompt/{agent_code}")
def academy_optimize_prompt(agent_code: str, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or {}
    summary = (payload.get("changes_description") or "Automated weekly quality optimization").strip()
    agent = db.execute(select(AgentCatalog).where(AgentCatalog.code == agent_code)).scalars().first()
    if not agent:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Agent not found")

    next_version = db.execute(
        text("select coalesce(max(version), 0)::int + 1 from agent_prompt_versions where agent_code = :agent_code"),
        {"agent_code": agent_code},
    ).scalar_one()

    optimized_prompt = (agent.system_prompt or "").strip()
    if optimized_prompt:
        optimized_prompt += "\n\nOptimization note: Keep responses concise, structured, and action-oriented."
    else:
        optimized_prompt = f"You are {agent.code}. Deliver concise, actionable responses with clear next steps."

    db.execute(
        text(
            """
            insert into agent_prompt_versions (agent_code, version, system_prompt, changes_description, performance_metrics)
            values (:agent_code, :version, :system_prompt, :changes_description, cast(:performance_metrics as jsonb));
            """
        ),
        {
            "agent_code": agent_code,
            "version": int(next_version),
            "system_prompt": optimized_prompt,
            "changes_description": summary,
            "performance_metrics": json.dumps({"baseline_quality": 0.82, "target_quality": 0.87}),
        },
    )
    db.execute(
        text("update agent_catalog set system_prompt = :system_prompt, updated_at = now() where code = :agent_code"),
        {"system_prompt": optimized_prompt, "agent_code": agent_code},
    )
    db.commit()

    return {
        "ok": True,
        "agent_code": agent_code,
        "version": int(next_version),
        "changes_description": summary,
        "expected_improvement": "Higher consistency and faster, clearer answers in common scenarios.",
    }
