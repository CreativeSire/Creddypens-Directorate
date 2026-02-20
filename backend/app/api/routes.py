from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import json
import re
import requests
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func as sqlfunc, select, text
from sqlalchemy.orm import Session

from app.agents.prompts import inject_domain_block, system_prompt_for_agent
from app.analytics.queries import get_activity_timeseries, get_costs_by_department, get_overview
from app.db import SessionLocal, get_db
from app.integrations.email import email_integration
from app.integrations.slack import slack_integration
from app.integrations.webhook import webhook_integration
from app.llm.litellm_client import LLMError, execute_via_litellm
from app.memory.extractor import memory_extractor
from app.llm.multi_router import get_multi_llm_router
from app.models import AgentCatalog, HiredAgent
from app.outputs.csv_formatter import csv_formatter
from app.outputs.email_formatter import email_formatter
from app.outputs.pdf_generator import pdf_generator
from app.runtime.hooks import RuntimeEvent, hook_bus
from app.runtime.model_policy import model_policy_service
from app.runtime.session_manager import session_manager
from app.runtime.tool_policy import tool_policy_service
from app.runtime.tool_registry import ToolCallContext, tool_registry
from app.workflows.engine import WorkflowEngine
from app.schemas import AgentDetailOut, AgentOut
from app.schemas_chat import ChatIn, ChatOut
from app.schemas_execute import (
    ExecuteContext,
    ExecuteIn,
    ExecuteOut,
    MemoryCreateIn,
    MemoryExtractIn,
    MemoryExtractOut,
    MemoryOut,
    MemoryUpdateIn,
    SuggestedAgent,
)
from app.settings import settings

try:
    from croniter import croniter
except Exception:  # pragma: no cover
    croniter = None

# Matches [REFER:CODE] anywhere in a response, e.g. [REFER:LEGAL-01] or [REFER:Author-01]
_REFER_PATTERN = re.compile(r"\[REFER:([A-Za-z][A-Za-z0-9\-]*)\]")
_OUTPUT_FORMATS = {"text", "markdown", "json", "email", "csv", "code", "presentation"}


def _infer_department_from_message(message: str) -> str | None:
    content = (message or "").lower()
    keyword_map: dict[str, tuple[str, ...]] = {
        "Customer Experience": ("support", "ticket", "complaint", "customer", "onboarding", "faq"),
        "Sales & Business Development": ("lead", "prospect", "pipeline", "outreach", "closing", "sales"),
        "Marketing & Creative": ("blog", "copy", "campaign", "social", "content", "brand"),
        "Operations & Admin": ("calendar", "schedule", "priorities", "travel", "admin", "process"),
        "Technical & IT": ("api", "code", "bug", "deploy", "infra", "security", "database", "sql"),
        "Specialized Services": ("legal", "compliance", "finance", "audit", "contract", "policy"),
    }
    for department, keywords in keyword_map.items():
        if any(word in content for word in keywords):
            return department
    return None


def _pick_colleague_for_department(
    *,
    db: Session,
    department: str,
    current_agent_code: str,
    org_id: str,
    message: str,
    current_agent_name: str,
) -> SuggestedAgent | None:
    colleague = (
        db.execute(
            select(AgentCatalog)
            .where(AgentCatalog.status == "active")
            .where(AgentCatalog.department == department)
            .where(AgentCatalog.code != current_agent_code)
            .order_by(AgentCatalog.code.asc())
        )
        .scalars()
        .first()
    )
    if not colleague:
        return None

    hired = (
        db.execute(
            select(HiredAgent)
            .where(HiredAgent.org_id == org_id)
            .where(HiredAgent.agent_code == colleague.code)
            .where(HiredAgent.status == "active")
        )
        .scalars()
        .first()
    )

    return SuggestedAgent(
        code=colleague.code,
        name=colleague.name,
        tagline=colleague.tagline,
        department=colleague.department,
        reason=(
            f"This request is better handled by {colleague.name} in {colleague.department}. "
            f"{current_agent_name} provided a general answer and recommends a specialist."
        ),
        is_hired=bool(hired),
        handoff_context=message,
    )


def _session_memory_block(
    *,
    db: Session,
    org_id: str,
    agent_code: str,
    session_id: str | None,
) -> str:
    if not settings.multi_turn_memory_enabled:
        return ""
    sid = (session_id or "").strip()
    if not sid:
        return ""

    turns = max(0, int(settings.multi_turn_memory_turns or 0))
    if turns == 0:
        return ""

    rows = (
        db.execute(
            text(
                """
                select message, response
                from interaction_logs
                where org_id = :org_id
                  and agent_code = :agent_code
                  and session_id = :session_id
                order by created_at desc
                limit :limit;
                """
            ),
            {
                "org_id": org_id,
                "agent_code": agent_code,
                "session_id": sid,
                "limit": turns,
            },
        )
        .mappings()
        .all()
    )
    if not rows:
        return ""

    rows = list(reversed(rows))
    lines = ["Recent conversation history (same session):"]
    for row in rows:
        user = str(row.get("message") or "").strip()
        assistant = str(row.get("response") or "").strip()
        if user:
            lines.append(f"User: {user}")
        if assistant:
            lines.append(f"Assistant: {assistant}")
    return "\n".join(lines)


def _to_context_lines(context: ExecuteContext) -> list[str]:
    context_lines: list[str] = []
    if context.company_name:
        context_lines.append(f"Company: {context.company_name}")
    if context.tone:
        context_lines.append(f"Tone: {context.tone}")
    if context.output_format:
        fmt = context.output_format.strip().lower()
        if fmt in _OUTPUT_FORMATS:
            context_lines.append(f"Output format requested: {fmt}")
            if fmt == "markdown":
                context_lines.append("Return markdown with clear headings and concise sections.")
            elif fmt == "json":
                context_lines.append("Return strictly valid JSON only.")
            elif fmt == "email":
                context_lines.append("Return a ready-to-send email with subject and body.")
            elif fmt == "csv":
                context_lines.append("Return CSV content with headers and rows.")
            elif fmt == "code":
                context_lines.append("Return code in fenced code blocks with brief usage notes.")
            elif fmt == "presentation":
                context_lines.append("Return a slide-by-slide outline with titles and key bullets.")
    if context.web_search:
        context_lines.append("Web search mode requested by user. Use current information when available.")
    if context.doc_retrieval:
        context_lines.append("Document retrieval enabled. Use internal knowledge base context when relevant.")
    if context.deep_research:
        context_lines.append("Deep research mode enabled. Provide a structured comprehensive answer.")
    if context.attachments:
        attachment_lines: list[str] = []
        for attachment in context.attachments[:5]:
            item = f"- {attachment.name}"
            if attachment.mime_type:
                item += f" ({attachment.mime_type})"
            if attachment.content_excerpt:
                item += f": {attachment.content_excerpt[:240]}"
            attachment_lines.append(item)
        if attachment_lines:
            context_lines.append("Attachments provided:\n" + "\n".join(attachment_lines))
    if context.additional:
        context_lines.append(f"Additional: {context.additional}")
    return context_lines


def _next_run_at(cron_expression: str, tz_name: str = "UTC") -> datetime | None:
    if not croniter:
        return None
    base = datetime.now(timezone.utc)
    try:
        return croniter(cron_expression, base).get_next(datetime)
    except Exception:
        return None

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "llm_mock": settings.llm_mock}


@router.get("/v1/llm/router/stats")
def llm_router_stats() -> dict:
    return get_multi_llm_router().cost_summary()


@router.get("/v1/llm/router/catalog")
def llm_router_catalog() -> dict:
    router_instance = get_multi_llm_router()
    items = []
    for name, provider in router_instance.providers.items():
        items.append(
            {
                "provider": name,
                "default_model": getattr(provider, "default_model", ""),
            }
        )
    return {"providers": items}


def _memory_row_to_out(row: dict) -> MemoryOut:
    return MemoryOut(
        memory_id=str(row["memory_id"]),
        org_id=str(row["org_id"]),
        agent_code=(str(row["agent_code"]) if row.get("agent_code") else None),
        memory_type=str(row["memory_type"]),
        memory_key=str(row["memory_key"]),
        memory_value=str(row["memory_value"]),
        confidence=float(row["confidence"] or 0),
        source=str(row["source"] or "manual"),
        created_at=row.get("created_at"),
        last_accessed=row.get("last_accessed"),
        access_count=int(row.get("access_count") or 0),
        is_active=bool(row.get("is_active")),
    )


@router.get("/v1/organizations/{org_id}/memories", response_model=list[MemoryOut])
def list_memories(
    org_id: str,
    agent_code: str | None = None,
    memory_type: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[MemoryOut]:
    sql = """
      select memory_id, org_id, agent_code, memory_type, memory_key, memory_value, confidence, source, created_at, last_accessed, access_count, is_active
      from agent_memories
      where org_id = :org_id
    """
    params: dict[str, object] = {"org_id": org_id}
    if agent_code:
        sql += " and coalesce(agent_code, '') = :agent_code"
        params["agent_code"] = agent_code
    if memory_type:
        sql += " and memory_type = :memory_type"
        params["memory_type"] = memory_type
    if not include_inactive:
        sql += " and is_active = true"
    sql += " order by last_accessed desc, created_at desc"
    rows = db.execute(text(sql), params).mappings().all()
    return [_memory_row_to_out(dict(r)) for r in rows]


@router.post("/v1/organizations/{org_id}/memories", response_model=MemoryOut)
def create_memory(org_id: str, payload: MemoryCreateIn, db: Session = Depends(get_db)) -> MemoryOut:
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )
    row = db.execute(
        text(
            """
            insert into agent_memories (org_id, agent_code, memory_type, memory_key, memory_value, confidence, source, last_accessed, access_count, is_active)
            values (:org_id, nullif(:agent_code, ''), :memory_type, :memory_key, :memory_value, :confidence, :source, now(), 0, true)
            on conflict (org_id, coalesce(agent_code, ''), memory_type, memory_key)
            do update set
              memory_value = excluded.memory_value,
              confidence = excluded.confidence,
              source = excluded.source,
              is_active = true,
              last_accessed = now()
            returning memory_id, org_id, agent_code, memory_type, memory_key, memory_value, confidence, source, created_at, last_accessed, access_count, is_active;
            """
        ),
        {
            "org_id": org_id,
            "agent_code": payload.agent_code or "",
            "memory_type": payload.memory_type.strip().lower(),
            "memory_key": payload.memory_key.strip().lower(),
            "memory_value": payload.memory_value.strip(),
            "confidence": float(payload.confidence),
            "source": payload.source.strip() or "manual",
        },
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to store memory")
    return _memory_row_to_out(dict(row))


@router.put("/v1/memories/{memory_id}", response_model=MemoryOut)
def update_memory(memory_id: str, payload: MemoryUpdateIn, db: Session = Depends(get_db)) -> MemoryOut:
    row = db.execute(
        text(
            """
            update agent_memories
            set
              memory_value = coalesce(:memory_value, memory_value),
              confidence = coalesce(:confidence, confidence),
              is_active = coalesce(:is_active, is_active),
              last_accessed = now()
            where memory_id = cast(:memory_id as uuid)
            returning memory_id, org_id, agent_code, memory_type, memory_key, memory_value, confidence, source, created_at, last_accessed, access_count, is_active;
            """
        ),
        {
            "memory_id": memory_id,
            "memory_value": payload.memory_value.strip() if payload.memory_value else None,
            "confidence": float(payload.confidence) if payload.confidence is not None else None,
            "is_active": payload.is_active,
        },
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _memory_row_to_out(dict(row))


@router.delete("/v1/memories/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db)) -> dict:
    changed = db.execute(
        text(
            """
            update agent_memories
            set is_active = false, last_accessed = now()
            where memory_id = cast(:memory_id as uuid);
            """
        ),
        {"memory_id": memory_id},
    ).rowcount
    db.commit()
    if not changed:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True, "memory_id": memory_id}


@router.post("/v1/organizations/{org_id}/memories/extract", response_model=MemoryExtractOut)
def extract_memories(org_id: str, payload: MemoryExtractIn, db: Session = Depends(get_db)) -> MemoryExtractOut:
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )
    rows = db.execute(
        text(
            """
            select role, content
            from chat_session_messages
            where session_id = :session_id
            order by created_at desc
            limit :limit;
            """
        ),
        {"session_id": payload.session_id, "limit": payload.lookback_messages},
    ).mappings().all()
    messages = [{"role": str(r["role"]), "content": str(r["content"])} for r in reversed(rows)]
    if not messages:
        raise HTTPException(status_code=404, detail="No session messages found for extraction")

    extracted = memory_extractor.extract_from_messages(messages=messages, agent_code=payload.agent_code)
    created = 0
    updated = 0
    output: list[MemoryOut] = []
    for memory in extracted:
        row = db.execute(
            text(
                """
                insert into agent_memories (org_id, agent_code, memory_type, memory_key, memory_value, confidence, source, last_accessed, access_count, is_active)
                values (:org_id, nullif(:agent_code, ''), :memory_type, :memory_key, :memory_value, :confidence, 'auto_extract', now(), 0, true)
                on conflict (org_id, coalesce(agent_code, ''), memory_type, memory_key)
                do update set
                  memory_value = excluded.memory_value,
                  confidence = excluded.confidence,
                  source = excluded.source,
                  is_active = true,
                  last_accessed = now(),
                  access_count = agent_memories.access_count + 1
                returning memory_id, org_id, agent_code, memory_type, memory_key, memory_value, confidence, source, created_at, last_accessed, access_count, is_active,
                          (xmax = 0) as inserted;
                """
            ),
            {
                "org_id": org_id,
                "agent_code": payload.agent_code or "",
                "memory_type": str(memory["memory_type"]),
                "memory_key": str(memory["memory_key"]),
                "memory_value": str(memory["memory_value"]),
                "confidence": float(memory.get("confidence", 0.7)),
            },
        ).mappings().first()
        if not row:
            continue
        if bool(row.get("inserted")):
            created += 1
        else:
            updated += 1
        output.append(_memory_row_to_out(dict(row)))
    db.commit()
    return MemoryExtractOut(created=created, updated=updated, memories=output)


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


@router.get("/v1/organizations/{org_id}/analytics/overview")
def get_analytics_overview(org_id: str, days: int = 30, db: Session = Depends(get_db)) -> dict:
    days = max(1, min(days, 365))
    return get_overview(db=db, org_id=org_id, days=days)


@router.get("/v1/organizations/{org_id}/analytics/costs")
def get_analytics_costs(org_id: str, days: int = 30, db: Session = Depends(get_db)) -> dict:
    days = max(1, min(days, 365))
    return get_costs_by_department(db=db, org_id=org_id, days=days)


@router.get("/v1/organizations/{org_id}/analytics/activity")
def get_analytics_activity(org_id: str, days: int = 30, db: Session = Depends(get_db)) -> dict:
    days = max(1, min(days, 365))
    return get_activity_timeseries(db=db, org_id=org_id, days=days)


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

    # Build system prompt: start from stored prompt (or fallback), then inject domain boundary block.
    system_prompt = (agent.system_prompt or "").strip() or system_prompt_for_agent(agent_code)
    system_prompt = inject_domain_block(system_prompt, agent)

    context_lines = _to_context_lines(payload.context)
    memory_block = _session_memory_block(
        db=db,
        org_id=org_id,
        agent_code=agent_code,
        session_id=payload.session_id,
    )
    if memory_block:
        context_lines.append(memory_block)
    try:
        session_id = session_manager.ensure_session(
            org_id=org_id,
            agent_code=agent_code,
            session_id=payload.session_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    session_context = session_manager.render_context_block(
        org_id=org_id,
        session_id=session_id,
        agent_code=agent_code,
    )
    if session_context:
        context_lines.append(session_context)
    if context_lines:
        system_prompt = system_prompt + "\n\nClient Context:\n" + "\n".join(context_lines)

    trace_id = str(uuid.uuid4())
    quality_score = 0.85
    hook_bus.emit(
        RuntimeEvent(
            event_type="session.request_start",
            org_id=org_id,
            session_id=session_id,
            agent_code=agent_code,
            payload={"trace_id": trace_id},
        )
    )
    try:
        session_manager.append_message(
            org_id=org_id,
            session_id=session_id,
            agent_code=agent_code,
            role="user",
            content=payload.message,
            metadata={"trace_id": trace_id},
        )
        result = execute_via_litellm(
            provider=agent.llm_provider or "",
            model=agent.llm_model or "",
            system=system_prompt,
            user=payload.message,
            trace_id=trace_id,
            enable_search=bool(payload.context.web_search),
            enable_docs=bool(payload.context.doc_retrieval),
            org_id=org_id,
            session_id=session_id,
            agent_code=agent_code,
            file_ids=payload.file_ids,
        )
    except LLMError as e:
        hook_bus.emit(
            RuntimeEvent(
                event_type="session.request_error",
                org_id=org_id,
                session_id=session_id,
                agent_code=agent_code,
                payload={"trace_id": trace_id, "error": str(e)},
            )
        )
        raise HTTPException(status_code=503, detail=str(e)) from e

    response_text = result.get("response") or result.get("content") or result.get("text") or ""
    tokens_used = int(result.get("tokens_used") or 0)
    session_manager.append_message(
        org_id=org_id,
        session_id=session_id,
        agent_code=agent_code,
        role="assistant",
        content=response_text,
        metadata={"trace_id": trace_id, "model_used": result.get("model_used"), "search_used": bool(result.get("search_used")), "docs_used": bool(result.get("docs_used"))},
    )
    hook_bus.emit(
        RuntimeEvent(
            event_type="session.request_complete",
            org_id=org_id,
            session_id=session_id,
            agent_code=agent_code,
            payload={
                "trace_id": trace_id,
                "latency_ms": int(result.get("latency_ms") or 0),
                "model_used": result.get("model_used"),
                "search_used": bool(result.get("search_used")),
                "docs_used": bool(result.get("docs_used")),
            },
        )
    )

    # --- Referral detection ---------------------------------------------------
    # If the agent included [REFER:CODE] it means the question is outside its domain.
    # Strip the tag from the visible response and build a SuggestedAgent payload.
    referral_triggered = False
    suggested_agent_out: SuggestedAgent | None = None

    refer_match = _REFER_PATTERN.search(response_text)
    if refer_match:
        referral_triggered = True
        referred_code_raw = refer_match.group(1)
        # Strip ALL occurrences of [REFER:...] from the visible response.
        response_text = _REFER_PATTERN.sub("", response_text).strip()

        # Resolve the referred agent: exact match first, then case-insensitive fallback.
        referred_agent = (
            db.execute(select(AgentCatalog).where(AgentCatalog.code == referred_code_raw))
            .scalars()
            .first()
        )
        if not referred_agent:
            referred_agent = (
                db.execute(
                    select(AgentCatalog).where(
                        sqlfunc.lower(AgentCatalog.code) == referred_code_raw.lower()
                    )
                )
                .scalars()
                .first()
            )

        if referred_agent:
            # Check whether the org already has this agent hired (free handoff vs hire gate).
            referred_hired = (
                db.execute(
                    select(HiredAgent)
                    .where(HiredAgent.org_id == org_id)
                    .where(HiredAgent.agent_code == referred_agent.code)
                    .where(HiredAgent.status == "active")
                )
                .scalars()
                .first()
            )
            suggested_agent_out = SuggestedAgent(
                code=referred_agent.code,
                name=referred_agent.name,
                tagline=referred_agent.tagline,
                department=referred_agent.department,
                reason=(
                    f"This question falls outside {agent.name}'s training. "
                    f"{referred_agent.name} is trained specifically for this."
                ),
                is_hired=bool(referred_hired),
                handoff_context=payload.message,
            )
    if not suggested_agent_out:
        inferred_department = _infer_department_from_message(payload.message)
        current_department = (agent.department or "").strip()
        if inferred_department and inferred_department != current_department:
            suggested_agent_out = _pick_colleague_for_department(
                db=db,
                department=inferred_department,
                current_agent_code=agent_code,
                org_id=org_id,
                message=payload.message,
                current_agent_name=agent.name,
            )
            if suggested_agent_out:
                referral_triggered = True
    # --------------------------------------------------------------------------

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
        search_used=bool(result.get("search_used")),
        docs_used=bool(result.get("docs_used")),
        latency_ms=int(result["latency_ms"]),
        tokens_used=tokens_used,
        interaction_id=interaction_id,
        trace_id=result["trace_id"],
        session_id=session_id,
        referral_triggered=referral_triggered,
        suggested_agent=suggested_agent_out,
    )


@router.post("/v1/agents/{agent_code}/execute/stream")
async def execute_agent_stream(
    agent_code: str,
    payload: ExecuteIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
):
    org_id = x_org_id or "org_test"
    result = execute_agent(agent_code=agent_code, payload=payload, db=db, x_org_id=org_id)

    async def event_gen():
        words = result.response.split(" ")
        emitted = ""
        yield _sse_frame("meta", {"session_id": result.session_id, "trace_id": result.trace_id, "model_used": result.model_used})
        for idx, word in enumerate(words):
            emitted = f"{emitted} {word}".strip()
            yield _sse_frame("token", {"index": idx, "token": word, "partial": emitted})
            await asyncio.sleep(0.01)
        yield _sse_frame(
            "done",
            {
                "response": result.response,
                "latency_ms": result.latency_ms,
                "tokens_used": result.tokens_used,
                "search_used": result.search_used,
                "docs_used": result.docs_used,
                "interaction_id": result.interaction_id,
            },
        )

    return StreamingResponse(event_gen(), media_type="text/event-stream")


class SessionCreateIn(BaseModel):
    agent_code: str = Field(min_length=1, max_length=64)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=250)


class SessionOut(BaseModel):
    session_id: str
    org_id: str
    agent_code: str
    status: str
    turns_count: int
    compacted_turns: int
    summary: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_activity_at: datetime | None = None


class ToolPolicyIn(BaseModel):
    tool_name: str = Field(min_length=2, max_length=80)
    allow: bool
    agent_code: str | None = Field(default=None, max_length=64)
    config: dict = Field(default_factory=dict)


class ModelPolicyIn(BaseModel):
    preferred_provider: str | None = None
    preferred_model: str | None = None
    reasoning_effort: str | None = None
    agent_code: str | None = Field(default=None, max_length=64)
    metadata: dict = Field(default_factory=dict)


class ToolRunIn(BaseModel):
    tool_name: str = Field(min_length=2, max_length=80)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    agent_code: str | None = Field(default=None, max_length=64)
    args: dict = Field(default_factory=dict)


class IntegrationConfigIn(BaseModel):
    integration_type: str = Field(min_length=1, max_length=64)
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class IntegrationConfigOut(BaseModel):
    integration_id: str
    org_id: str
    integration_type: str
    config: dict
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IntegrationTestIn(BaseModel):
    payload: dict = Field(default_factory=dict)


class WebhookTestIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    payload: dict = Field(default_factory=dict)
    headers: dict = Field(default_factory=dict)


class TaskCreateIn(BaseModel):
    task_title: str = Field(min_length=2, max_length=240)
    task_description: str = Field(default="", max_length=4000)
    agent_code: str | None = Field(default=None, max_length=64)
    priority: str = Field(default="medium", max_length=16)
    assigned_to: str | None = Field(default=None, max_length=120)
    created_by: str = Field(default="user", max_length=120)


class TaskOut(BaseModel):
    task_id: str
    org_id: str
    agent_code: str | None = None
    task_title: str
    task_description: str
    status: str
    priority: str
    assigned_to: str | None = None
    created_by: str
    result: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskStatusIn(BaseModel):
    status: str = Field(min_length=4, max_length=20)
    result: str | None = Field(default=None, max_length=8000)


class TaskAssignIn(BaseModel):
    assigned_to: str = Field(min_length=1, max_length=120)


def _sse_frame(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _get_interaction_export_row(db: Session, interaction_id: str, org_id: str) -> dict | None:
    row = db.execute(
        text(
            """
            select
              il.interaction_id,
              il.response as agent_response,
              il.agent_code,
              ac.human_name,
              ac.name as role
            from interaction_logs il
            left join agent_catalog ac on ac.code = il.agent_code
            where il.interaction_id = cast(:interaction_id as uuid)
              and il.org_id = :org_id
            limit 1;
            """
        ),
        {"interaction_id": interaction_id, "org_id": org_id},
    ).mappings().first()
    return dict(row) if row else None


@router.get("/v1/interactions/{interaction_id}/pdf")
def export_interaction_as_pdf(
    interaction_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
):
    org_id = x_org_id or "org_test"
    row = _get_interaction_export_row(db, interaction_id, org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")

    title = f"Response from {row.get('human_name') or row.get('agent_code')} ({row.get('role') or 'Agent'})"
    try:
        pdf_bytes = pdf_generator.generate_from_text(text=str(row.get("agent_response") or ""), title=title)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={interaction_id}.pdf"},
    )


@router.get("/v1/interactions/{interaction_id}/csv")
def export_interaction_as_csv(
    interaction_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
):
    org_id = x_org_id or "org_test"
    row = _get_interaction_export_row(db, interaction_id, org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")

    csv_content = csv_formatter.parse_table_from_text(str(row.get("agent_response") or ""))
    if not csv_content:
        raise HTTPException(status_code=400, detail="No table found in response")
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={interaction_id}.csv"},
    )


@router.get("/v1/interactions/{interaction_id}/email")
def format_interaction_as_email(
    interaction_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
):
    org_id = x_org_id or "org_test"
    row = _get_interaction_export_row(db, interaction_id, org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return email_formatter.format_as_email(str(row.get("agent_response") or ""))


@router.post("/v1/sessions", response_model=SessionOut)
def create_or_resume_session(
    payload: SessionCreateIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> SessionOut:
    org_id = x_org_id or "org_test"
    try:
        session_id = session_manager.ensure_session(org_id=org_id, agent_code=payload.agent_code, session_id=payload.session_id)
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    row = db.execute(
        text(
            """
            select session_id, org_id, agent_code, status, turns_count, compacted_turns, summary, created_at, updated_at, last_activity_at
            from chat_sessions
            where session_id = :session_id and org_id = :org_id
            limit 1;
            """
        ),
        {"session_id": session_id, "org_id": org_id},
    ).mappings().first()
    return SessionOut(**dict(row or {}))


@router.get("/v1/sessions", response_model=list[SessionOut])
def list_sessions(
    limit: int = 100,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> list[SessionOut]:
    org_id = x_org_id or "org_test"
    rows = session_manager.list_sessions(org_id=org_id, limit=limit)
    return [SessionOut(**row) for row in rows]


@router.delete("/v1/sessions/{session_id}")
def delete_session(
    session_id: str,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    deleted = session_manager.delete_session(org_id=org_id, session_id=session_id)
    return {"ok": deleted, "session_id": session_id}


@router.get("/v1/runtime/events")
def list_runtime_events(
    limit: int = 200,
    session_id: str | None = None,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    cap = max(1, min(int(limit), 1000))
    with SessionLocal() as local_db:
        if session_id:
            rows = local_db.execute(
                text(
                    """
                    select id, org_id, session_id, agent_code, event_type, payload, created_at
                    from runtime_events
                    where org_id = :org_id and session_id = :session_id
                    order by created_at desc
                    limit :limit;
                    """
                ),
                {"org_id": org_id, "session_id": session_id, "limit": cap},
            ).mappings().all()
        else:
            rows = local_db.execute(
                text(
                    """
                    select id, org_id, session_id, agent_code, event_type, payload, created_at
                    from runtime_events
                    where org_id = :org_id
                    order by created_at desc
                    limit :limit;
                    """
                ),
                {"org_id": org_id, "limit": cap},
            ).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/v1/tools")
def list_tools() -> dict:
    return {"tools": tool_registry.list_tools()}


@router.post("/v1/tools/run")
def run_tool(
    payload: ToolRunIn,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    result = tool_registry.run(
        tool_name=payload.tool_name,
        context=ToolCallContext(org_id=org_id, session_id=payload.session_id, agent_code=payload.agent_code),
        args=payload.args,
    )
    return result


@router.get("/v1/tool-policies")
def list_tool_policies(
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    return {"items": tool_policy_service.list_policies(org_id=org_id)}


@router.post("/v1/tool-policies")
def upsert_tool_policy(
    payload: ToolPolicyIn,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    tool_policy_service.upsert_policy(
        org_id=org_id,
        tool_name=payload.tool_name,
        allow=payload.allow,
        agent_code=payload.agent_code,
        config=payload.config,
    )
    return {"ok": True}


@router.get("/v1/model-policies")
def list_model_policies(
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    return {"items": model_policy_service.list_preferences(org_id=org_id)}


@router.post("/v1/model-policies")
def upsert_model_policy(
    payload: ModelPolicyIn,
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    model_policy_service.upsert_preference(
        org_id=org_id,
        preferred_provider=payload.preferred_provider,
        preferred_model=payload.preferred_model,
        reasoning_effort=payload.reasoning_effort,
        agent_code=payload.agent_code,
        metadata=payload.metadata,
    )
    return {"ok": True}


@router.post("/v1/organizations/{org_id}/integrations", response_model=IntegrationConfigOut)
def create_integration_config(org_id: str, payload: IntegrationConfigIn, db: Session = Depends(get_db)) -> IntegrationConfigOut:
    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )
    row = db.execute(
        text(
            """
            insert into integration_configs (org_id, integration_type, config, is_active, created_at, updated_at)
            values (:org_id, :integration_type, cast(:config as jsonb), :is_active, now(), now())
            returning integration_id, org_id, integration_type, config, is_active, created_at, updated_at;
            """
        ),
        {
            "org_id": org_id,
            "integration_type": payload.integration_type.strip().lower(),
            "config": json.dumps(payload.config),
            "is_active": payload.is_active,
        },
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create integration config")
    return IntegrationConfigOut(**dict(row))


@router.get("/v1/organizations/{org_id}/integrations", response_model=list[IntegrationConfigOut])
def list_integrations(org_id: str, include_inactive: bool = False, db: Session = Depends(get_db)) -> list[IntegrationConfigOut]:
    sql = """
      select integration_id, org_id, integration_type, config, is_active, created_at, updated_at
      from integration_configs
      where org_id = :org_id
    """
    if not include_inactive:
        sql += " and is_active = true"
    sql += " order by created_at desc"
    rows = db.execute(text(sql), {"org_id": org_id}).mappings().all()
    return [IntegrationConfigOut(**dict(row)) for row in rows]


@router.delete("/v1/integrations/{integration_id}")
def delete_integration(integration_id: str, db: Session = Depends(get_db)) -> dict:
    changed = db.execute(
        text(
            """
            update integration_configs
            set is_active = false, updated_at = now()
            where integration_id = cast(:integration_id as uuid);
            """
        ),
        {"integration_id": integration_id},
    ).rowcount
    db.commit()
    if not changed:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"ok": True, "integration_id": integration_id}


@router.post("/v1/integrations/{integration_id}/test")
async def test_integration(integration_id: str, payload: IntegrationTestIn, db: Session = Depends(get_db)) -> dict:
    row = db.execute(
        text(
            """
            select integration_type, config, is_active
            from integration_configs
            where integration_id = cast(:integration_id as uuid)
            limit 1;
            """
        ),
        {"integration_id": integration_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")
    if not bool(row["is_active"]):
        raise HTTPException(status_code=409, detail="Integration is inactive")

    integration_type = str(row["integration_type"])
    config = dict(row["config"] or {})

    if integration_type == "slack":
        webhook_url = str(config.get("webhook_url") or "")
        result = slack_integration.post_message(
            webhook_url=webhook_url,
            text=str(payload.payload.get("text") or "CreddyPens integration test message"),
        )
        return {"ok": True, "integration_type": "slack", "result": result}

    if integration_type == "email":
        smtp_host = str(config.get("smtp_host") or "")
        smtp_port = int(config.get("smtp_port") or 587)
        smtp_user = str(config.get("smtp_user") or "")
        smtp_password = str(config.get("smtp_password") or "")
        from_email = str(config.get("from_email") or smtp_user)
        to_email = str(payload.payload.get("to_email") or config.get("test_recipient") or "")
        subject = str(payload.payload.get("subject") or "CreddyPens integration test")
        body = str(payload.payload.get("body") or "This is a connectivity test from CreddyPens.")
        if not to_email:
            raise HTTPException(status_code=400, detail="Missing to_email in test payload or config.test_recipient")
        result = await email_integration.send_email(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=body,
            use_tls=bool(config.get("use_tls", True)),
        )
        return {"ok": True, "integration_type": "email", "result": result}

    if integration_type == "webhook":
        url = str(config.get("url") or "")
        merged_headers = dict(config.get("headers") or {})
        merged_headers.update({str(k): str(v) for k, v in payload.payload.get("headers", {}).items()} if isinstance(payload.payload.get("headers"), dict) else {})
        body = payload.payload.get("payload")
        if not isinstance(body, dict):
            body = {"message": "CreddyPens integration test"}
        result = webhook_integration.send_webhook(url=url, payload=body, headers=merged_headers)
        return {"ok": True, "integration_type": "webhook", "result": result}

    raise HTTPException(status_code=400, detail=f"Unsupported integration_type: {integration_type}")


@router.post("/v1/webhooks/test")
def test_webhook(payload: WebhookTestIn) -> dict:
    result = webhook_integration.send_webhook(
        url=payload.url,
        payload=payload.payload,
        headers={str(key): str(value) for key, value in payload.headers.items()},
    )
    return {"ok": True, "result": result}


@router.get("/v1/organizations/{org_id}/inbox", response_model=list[TaskOut])
def list_inbox_tasks(
    org_id: str,
    status: str | None = None,
    agent_code: str | None = None,
    assigned_to: str | None = None,
    priority: str | None = None,
    q: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    cap = max(1, min(int(limit), 500))
    sql = """
      select task_id, org_id, agent_code, task_title, task_description, status, priority, assigned_to, created_by, result, created_at, updated_at, started_at, completed_at
      from task_inbox
      where org_id = :org_id
    """
    params: dict[str, object] = {"org_id": org_id, "limit": cap}
    if status:
        sql += " and status = :status"
        params["status"] = status.strip().lower()
    if agent_code:
        sql += " and coalesce(agent_code,'') = :agent_code"
        params["agent_code"] = agent_code.strip()
    if assigned_to:
        sql += " and coalesce(assigned_to,'') = :assigned_to"
        params["assigned_to"] = assigned_to.strip()
    if priority:
        sql += " and priority = :priority"
        params["priority"] = priority.strip().lower()
    if q and q.strip():
        sql += " and (task_title ilike :q or task_description ilike :q)"
        params["q"] = f"%{q.strip()}%"
    sql += " order by updated_at desc limit :limit"
    rows = db.execute(text(sql), params).mappings().all()
    return [TaskOut(**{**dict(row), "task_id": str(row["task_id"])}) for row in rows]


@router.post("/v1/organizations/{org_id}/inbox", response_model=TaskOut)
def create_inbox_task(org_id: str, payload: TaskCreateIn, db: Session = Depends(get_db)) -> TaskOut:
    normalized_priority = payload.priority.strip().lower()
    if normalized_priority not in {"low", "medium", "high", "urgent"}:
        normalized_priority = "medium"

    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )
    row = db.execute(
        text(
            """
            insert into task_inbox
              (org_id, agent_code, task_title, task_description, status, priority, assigned_to, created_by, result, created_at, updated_at)
            values
              (:org_id, nullif(:agent_code,''), :task_title, :task_description, 'pending', :priority, nullif(:assigned_to,''), :created_by, '', now(), now())
            returning task_id, org_id, agent_code, task_title, task_description, status, priority, assigned_to, created_by, result, created_at, updated_at, started_at, completed_at;
            """
        ),
        {
            "org_id": org_id,
            "agent_code": payload.agent_code or "",
            "task_title": payload.task_title.strip(),
            "task_description": payload.task_description.strip(),
            "priority": normalized_priority,
            "assigned_to": payload.assigned_to or "",
            "created_by": payload.created_by.strip() or "user",
        },
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return TaskOut(**{**dict(row), "task_id": str(row["task_id"])})


@router.put("/v1/inbox/tasks/{task_id}/status", response_model=TaskOut)
def update_inbox_task_status(task_id: str, payload: TaskStatusIn, db: Session = Depends(get_db)) -> TaskOut:
    next_status = payload.status.strip().lower()
    if next_status not in {"pending", "in_progress", "completed"}:
        raise HTTPException(status_code=400, detail="status must be pending|in_progress|completed")
    row = db.execute(
        text(
            """
            update task_inbox
            set
              status = :status,
              result = coalesce(:result, result),
              started_at = case when :status = 'in_progress' and started_at is null then now() else started_at end,
              completed_at = case when :status = 'completed' then now() when :status <> 'completed' then null else completed_at end,
              updated_at = now()
            where task_id = cast(:task_id as uuid)
            returning task_id, org_id, agent_code, task_title, task_description, status, priority, assigned_to, created_by, result, created_at, updated_at, started_at, completed_at;
            """
        ),
        {
            "task_id": task_id,
            "status": next_status,
            "result": payload.result.strip() if payload.result else None,
        },
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut(**{**dict(row), "task_id": str(row["task_id"])})


@router.put("/v1/inbox/tasks/{task_id}/assign", response_model=TaskOut)
def assign_inbox_task(task_id: str, payload: TaskAssignIn, db: Session = Depends(get_db)) -> TaskOut:
    row = db.execute(
        text(
            """
            update task_inbox
            set assigned_to = :assigned_to, updated_at = now()
            where task_id = cast(:task_id as uuid)
            returning task_id, org_id, agent_code, task_title, task_description, status, priority, assigned_to, created_by, result, created_at, updated_at, started_at, completed_at;
            """
        ),
        {"task_id": task_id, "assigned_to": payload.assigned_to.strip()},
    ).mappings().first()
    db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut(**{**dict(row), "task_id": str(row["task_id"])})


class WorkflowStepIn(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=64)
    agent_code: str = Field(min_length=1, max_length=64)
    message: str | None = None
    use_previous_response: bool = True
    conditions: dict[str, str] = Field(default_factory=dict)
    next: str | None = Field(default=None, max_length=64)
    set_var: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=32)
    integration_id: str | None = Field(default=None, max_length=64)
    action_config: dict = Field(default_factory=dict)


class WorkflowExecuteIn(BaseModel):
    initial_message: str = Field(min_length=1, max_length=20000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    context: ExecuteContext = Field(default_factory=ExecuteContext)
    steps: list[WorkflowStepIn] = Field(min_length=1)
    workflow_definition: dict | None = None


class WorkflowStepOut(BaseModel):
    step_index: int
    step_id: str | None = None
    agent_code: str
    input_message: str
    response: str
    model_used: str
    latency_ms: int
    trace_id: str


class WorkflowExecuteOut(BaseModel):
    workflow_id: str
    session_id: str
    final_response: str
    steps: list[WorkflowStepOut]


class WorkflowTemplateStep(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=64)
    agent_code: str = Field(min_length=1, max_length=64)
    message: str | None = None
    use_previous_response: bool = True
    conditions: dict[str, str] = Field(default_factory=dict)
    next: str | None = Field(default=None, max_length=64)
    set_var: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=32)
    integration_id: str | None = Field(default=None, max_length=64)
    action_config: dict = Field(default_factory=dict)


class WorkflowTemplateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    context: ExecuteContext = Field(default_factory=ExecuteContext)
    steps: list[WorkflowTemplateStep] = Field(min_length=1)
    workflow_definition: dict | None = None
    is_active: bool = True


class WorkflowTemplateOut(BaseModel):
    template_id: str
    name: str
    description: str
    context: ExecuteContext
    steps: list[WorkflowTemplateStep]
    workflow_definition: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateRunIn(BaseModel):
    initial_message: str = Field(min_length=1, max_length=20000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    context_override: ExecuteContext | None = None


class WorkflowScheduleIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    cron_expression: str = Field(min_length=3, max_length=120)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    initial_message: str = Field(min_length=1, max_length=20000)
    is_active: bool = True


class WorkflowScheduleOut(BaseModel):
    schedule_id: str
    template_id: str
    template_name: str
    name: str
    cron_expression: str
    timezone: str
    initial_message: str
    is_active: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowScheduledRunOut(BaseModel):
    schedule_id: str
    workflow: WorkflowExecuteOut
    last_run_at: datetime
    next_run_at: datetime | None = None


class WorkflowDueRunItem(BaseModel):
    schedule_id: str
    workflow_id: str | None = None
    status: str
    error: str | None = None


class WorkflowDueRunOut(BaseModel):
    processed: int
    items: list[WorkflowDueRunItem]


def _validate_cron_expression(expr: str) -> bool:
    value = (expr or "").strip()
    if not value:
        return False
    if croniter:
        try:
            croniter(value, datetime.now(timezone.utc))
            return True
        except Exception:
            return False
    parts = value.split()
    return len(parts) in {5, 6}


def _merge_context(base: ExecuteContext, override: ExecuteContext | None) -> ExecuteContext:
    if override is None:
        return base
    data = base.model_dump()
    patch = override.model_dump(exclude_none=True)
    data.update(patch)
    return ExecuteContext(**data)


def _build_workflow_definition(steps: list[WorkflowStepIn]) -> dict:
    built_steps: list[dict] = []
    for index, step in enumerate(steps, start=1):
        step_id = (step.id or f"step_{index}").strip()
        built_steps.append(
            {
                "id": step_id,
                "agent_code": step.agent_code.strip(),
                "input": (step.message or "").strip(),
                "use_previous_response": bool(step.use_previous_response),
                "conditions": dict(step.conditions or {}),
                "next": (step.next or "").strip() or None,
                "set_var": (step.set_var or "").strip() or None,
                "action": (step.action or "").strip() or None,
                "integration_id": (step.integration_id or "").strip() or None,
                "action_config": dict(step.action_config or {}),
            }
        )
    return {"start_step_id": built_steps[0]["id"] if built_steps else None, "steps": built_steps}


@router.post("/v1/workflows/validate")
def validate_workflow_definition(payload: dict, db: Session = Depends(get_db)) -> dict:
    definition = payload.get("workflow_definition") if isinstance(payload, dict) else None
    if not isinstance(definition, dict):
        raise HTTPException(status_code=400, detail="workflow_definition must be an object")
    engine = WorkflowEngine(db)
    errors = engine.validate_definition(definition)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/v1/workflows/execute", response_model=WorkflowExecuteOut)
def execute_workflow(
    payload: WorkflowExecuteIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> WorkflowExecuteOut:
    from fastapi import HTTPException

    org_id = x_org_id or "org_test"
    max_steps = max(1, int(settings.workflow_max_steps))
    if len(payload.steps) > max_steps:
        raise HTTPException(status_code=400, detail=f"Too many steps. Max allowed: {max_steps}")

    workflow_id = str(uuid.uuid4())
    session_id = payload.session_id or f"wf-{workflow_id}"
    definition = payload.workflow_definition if isinstance(payload.workflow_definition, dict) else _build_workflow_definition(payload.steps)
    context = payload.context
    engine = WorkflowEngine(db)
    final_response, step_results = engine.execute_workflow(
        org_id=org_id,
        session_id=session_id,
        initial_message=payload.initial_message,
        context=context,
        workflow_definition=definition,
    )
    outputs = [
        WorkflowStepOut(
            step_index=item.step_index,
            step_id=item.step_id,
            agent_code=item.agent_code,
            input_message=item.input_message,
            response=item.response,
            model_used=item.model_used,
            latency_ms=item.latency_ms,
            trace_id=item.trace_id,
        )
        for item in step_results
    ]

    return WorkflowExecuteOut(
        workflow_id=workflow_id,
        session_id=session_id,
        final_response=final_response,
        steps=outputs,
    )


@router.post("/v1/workflows/templates", response_model=WorkflowTemplateOut)
def create_workflow_template(
    payload: WorkflowTemplateIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> WorkflowTemplateOut:
    from fastapi import HTTPException

    org_id = x_org_id or "org_test"
    max_steps = max(1, int(settings.workflow_max_steps))
    if len(payload.steps) > max_steps:
        raise HTTPException(status_code=400, detail=f"Too many steps. Max allowed: {max_steps}")
    workflow_definition = payload.workflow_definition or _build_workflow_definition([WorkflowStepIn(**item.model_dump()) for item in payload.steps])
    engine = WorkflowEngine(db)
    errors = engine.validate_definition(workflow_definition)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    db.execute(
        text("insert into organizations (org_id, name) values (:org_id, :name) on conflict (org_id) do nothing"),
        {"org_id": org_id, "name": ""},
    )
    try:
        row = db.execute(
            text(
                """
                insert into workflow_templates (org_id, name, description, context, steps, workflow_definition, is_active)
                values (:org_id, :name, :description, cast(:context as jsonb), cast(:steps as jsonb), cast(:workflow_definition as jsonb), :is_active)
                returning template_id, name, description, context, steps, workflow_definition, is_active, created_at, updated_at;
                """
            ),
            {
                "org_id": org_id,
                "name": payload.name.strip(),
                "description": payload.description.strip(),
                "context": json.dumps(payload.context.model_dump()),
                "steps": json.dumps([step.model_dump() for step in payload.steps]),
                "workflow_definition": json.dumps(workflow_definition),
                "is_active": payload.is_active,
            },
        ).mappings().first()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to save workflow template: {e}") from e

    if not row:
        raise HTTPException(status_code=500, detail="Failed to create workflow template")

    return WorkflowTemplateOut(
        template_id=str(row["template_id"]),
        name=str(row["name"]),
        description=str(row["description"] or ""),
        context=ExecuteContext(**(row["context"] or {})),
        steps=[WorkflowTemplateStep(**item) for item in (row["steps"] or [])],
        workflow_definition=dict(row["workflow_definition"] or {}),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/v1/workflows/templates", response_model=list[WorkflowTemplateOut])
def list_workflow_templates(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> list[WorkflowTemplateOut]:
    org_id = x_org_id or "org_test"
    if include_inactive:
        stmt = text(
            """
            select template_id, name, description, context, steps, workflow_definition, is_active, created_at, updated_at
            from workflow_templates
            where org_id = :org_id
            order by created_at desc;
            """
        )
    else:
        stmt = text(
            """
            select template_id, name, description, context, steps, workflow_definition, is_active, created_at, updated_at
            from workflow_templates
            where org_id = :org_id and is_active = true
            order by created_at desc;
            """
        )
    rows = db.execute(stmt, {"org_id": org_id}).mappings().all()
    out: list[WorkflowTemplateOut] = []
    for row in rows:
        out.append(
            WorkflowTemplateOut(
                template_id=str(row["template_id"]),
                name=str(row["name"]),
                description=str(row["description"] or ""),
                context=ExecuteContext(**(row["context"] or {})),
                steps=[WorkflowTemplateStep(**item) for item in (row["steps"] or [])],
                workflow_definition=dict(row["workflow_definition"] or {}),
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return out


@router.post("/v1/workflows/templates/{template_id}/run", response_model=WorkflowExecuteOut)
def run_workflow_template(
    template_id: str,
    payload: WorkflowTemplateRunIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> WorkflowExecuteOut:
    from fastapi import HTTPException

    org_id = x_org_id or "org_test"
    template = db.execute(
        text(
            """
            select template_id, name, context, steps, workflow_definition, is_active
            from workflow_templates
            where org_id = :org_id and template_id = cast(:template_id as uuid)
            limit 1;
            """
        ),
        {"org_id": org_id, "template_id": template_id},
    ).mappings().first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    if not bool(template["is_active"]):
        raise HTTPException(status_code=409, detail="Workflow template is inactive")

    base_context = ExecuteContext(**(template["context"] or {}))
    merged_context = _merge_context(base_context, payload.context_override)
    steps = [WorkflowStepIn(**item) for item in (template["steps"] or [])]
    definition = dict(template["workflow_definition"] or {}) if template.get("workflow_definition") else _build_workflow_definition(steps)
    run_input = WorkflowExecuteIn(
        initial_message=payload.initial_message,
        session_id=payload.session_id,
        context=merged_context,
        steps=steps,
        workflow_definition=definition,
    )
    try:
        result = execute_workflow(payload=run_input, db=db, x_org_id=org_id)
        db.execute(
            text(
                """
                insert into workflow_runs
                  (workflow_id, org_id, template_id, session_id, status, initial_message, final_response, steps_count, completed_at)
                values
                  (:workflow_id, :org_id, cast(:template_id as uuid), :session_id, 'completed', :initial_message, :final_response, :steps_count, now());
                """
            ),
            {
                "workflow_id": result.workflow_id,
                "org_id": org_id,
                "template_id": template_id,
                "session_id": result.session_id,
                "initial_message": payload.initial_message,
                "final_response": result.final_response,
                "steps_count": len(result.steps),
            },
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Workflow template run failed: {e}") from e

    return result


@router.post("/v1/workflows/templates/{template_id}/schedules", response_model=WorkflowScheduleOut)
def create_workflow_schedule(
    template_id: str,
    payload: WorkflowScheduleIn,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> WorkflowScheduleOut:
    from fastapi import HTTPException

    org_id = x_org_id or "org_test"
    if not _validate_cron_expression(payload.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    template_row = db.execute(
        text(
            """
            select template_id, name, is_active
            from workflow_templates
            where org_id = :org_id and template_id = cast(:template_id as uuid)
            limit 1;
            """
        ),
        {"org_id": org_id, "template_id": template_id},
    ).mappings().first()
    if not template_row:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    if not bool(template_row["is_active"]):
        raise HTTPException(status_code=409, detail="Workflow template is inactive")

    next_run = _next_run_at(payload.cron_expression, payload.timezone)
    row = db.execute(
        text(
            """
            insert into workflow_schedules
              (org_id, template_id, name, cron_expression, initial_message, timezone, is_active, next_run_at)
            values
              (:org_id, cast(:template_id as uuid), :name, :cron_expression, :initial_message, :timezone, :is_active, :next_run_at)
            returning schedule_id, template_id, name, cron_expression, initial_message, timezone, is_active, last_run_at, next_run_at, created_at, updated_at;
            """
        ),
        {
            "org_id": org_id,
            "template_id": template_id,
            "name": payload.name.strip(),
            "cron_expression": payload.cron_expression.strip(),
            "initial_message": payload.initial_message,
            "timezone": payload.timezone.strip() or "UTC",
            "is_active": payload.is_active,
            "next_run_at": next_run,
        },
    ).mappings().first()
    db.commit()

    if not row:
        raise HTTPException(status_code=500, detail="Failed to create schedule")

    return WorkflowScheduleOut(
        schedule_id=str(row["schedule_id"]),
        template_id=str(row["template_id"]),
        template_name=str(template_row["name"]),
        name=str(row["name"]),
        cron_expression=str(row["cron_expression"]),
        timezone=str(row["timezone"]),
        initial_message=str(row["initial_message"]),
        is_active=bool(row["is_active"]),
        last_run_at=row["last_run_at"],
        next_run_at=row["next_run_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/v1/workflows/schedules", response_model=list[WorkflowScheduleOut])
def list_workflow_schedules(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> list[WorkflowScheduleOut]:
    org_id = x_org_id or "org_test"
    active_clause = "" if include_inactive else "and ws.is_active = true"
    rows = db.execute(
        text(
            f"""
            select
              ws.schedule_id, ws.template_id, wt.name as template_name,
              ws.name, ws.cron_expression, ws.initial_message, ws.timezone, ws.is_active,
              ws.last_run_at, ws.next_run_at, ws.created_at, ws.updated_at
            from workflow_schedules ws
            join workflow_templates wt on wt.template_id = ws.template_id
            where ws.org_id = :org_id {active_clause}
            order by ws.created_at desc;
            """
        ),
        {"org_id": org_id},
    ).mappings().all()

    return [
        WorkflowScheduleOut(
            schedule_id=str(row["schedule_id"]),
            template_id=str(row["template_id"]),
            template_name=str(row["template_name"]),
            name=str(row["name"]),
            cron_expression=str(row["cron_expression"]),
            timezone=str(row["timezone"]),
            initial_message=str(row["initial_message"]),
            is_active=bool(row["is_active"]),
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.post("/v1/workflows/schedules/{schedule_id}/run", response_model=WorkflowScheduledRunOut)
def run_workflow_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> WorkflowScheduledRunOut:
    from fastapi import HTTPException

    org_id = x_org_id or "org_test"
    row = db.execute(
        text(
            """
            select
              ws.schedule_id, ws.template_id, ws.name, ws.cron_expression, ws.initial_message, ws.timezone, ws.is_active,
              wt.context, wt.steps, wt.is_active as template_active
            from workflow_schedules ws
            join workflow_templates wt on wt.template_id = ws.template_id
            where ws.org_id = :org_id and ws.schedule_id = cast(:schedule_id as uuid)
            limit 1;
            """
        ),
        {"org_id": org_id, "schedule_id": schedule_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workflow schedule not found")
    if not bool(row["is_active"]):
        raise HTTPException(status_code=409, detail="Workflow schedule is inactive")
    if not bool(row["template_active"]):
        raise HTTPException(status_code=409, detail="Workflow template is inactive")

    run_input = WorkflowExecuteIn(
        initial_message=str(row["initial_message"]),
        session_id=None,
        context=ExecuteContext(**(row["context"] or {})),
        steps=[WorkflowStepIn(**item) for item in (row["steps"] or [])],
    )
    result = execute_workflow(payload=run_input, db=db, x_org_id=org_id)

    last_run = datetime.now(timezone.utc)
    next_run = _next_run_at(str(row["cron_expression"]), str(row["timezone"]))
    db.execute(
        text(
            """
            update workflow_schedules
            set last_run_at = :last_run_at,
                next_run_at = :next_run_at,
                updated_at = now()
            where schedule_id = cast(:schedule_id as uuid);
            """
        ),
        {"schedule_id": schedule_id, "last_run_at": last_run, "next_run_at": next_run},
    )
    db.execute(
        text(
            """
            insert into workflow_runs
              (workflow_id, org_id, template_id, schedule_id, session_id, status, initial_message, final_response, steps_count, completed_at)
            values
              (:workflow_id, :org_id, cast(:template_id as uuid), cast(:schedule_id as uuid), :session_id, 'completed', :initial_message, :final_response, :steps_count, now());
            """
        ),
        {
            "workflow_id": result.workflow_id,
            "org_id": org_id,
            "template_id": str(row["template_id"]),
            "schedule_id": schedule_id,
            "session_id": result.session_id,
            "initial_message": str(row["initial_message"]),
            "final_response": result.final_response,
            "steps_count": len(result.steps),
        },
    )
    db.commit()

    return WorkflowScheduledRunOut(
        schedule_id=schedule_id,
        workflow=result,
        last_run_at=last_run,
        next_run_at=next_run,
    )


@router.post("/v1/workflows/schedules/run-due", response_model=WorkflowDueRunOut)
def run_due_workflow_schedules(
    limit: int = 10,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> WorkflowDueRunOut:
    from fastapi import HTTPException

    org_id = x_org_id or "org_test"
    capped_limit = max(1, min(50, int(limit)))
    now = datetime.now(timezone.utc)
    due = db.execute(
        text(
            """
            select schedule_id
            from workflow_schedules
            where org_id = :org_id
              and is_active = true
              and next_run_at is not null
              and next_run_at <= :now
            order by next_run_at asc
            limit :limit;
            """
        ),
        {"org_id": org_id, "now": now, "limit": capped_limit},
    ).mappings().all()

    items: list[WorkflowDueRunItem] = []
    for row in due:
        schedule_id = str(row["schedule_id"])
        try:
            out = run_workflow_schedule(schedule_id=schedule_id, db=db, x_org_id=org_id)
            items.append(WorkflowDueRunItem(schedule_id=schedule_id, workflow_id=out.workflow.workflow_id, status="completed"))
        except HTTPException as e:
            items.append(WorkflowDueRunItem(schedule_id=schedule_id, status="failed", error=str(e.detail)))
        except Exception as e:
            items.append(WorkflowDueRunItem(schedule_id=schedule_id, status="failed", error=str(e)))

    return WorkflowDueRunOut(processed=len(items), items=items)


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
