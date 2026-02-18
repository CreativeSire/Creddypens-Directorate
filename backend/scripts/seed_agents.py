from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import bindparam, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import engine
from app.schema import ensure_schema


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "agent_dossiers.json"

DEPARTMENT_MAP = {
    "CUSTOMER EXPERIENCE": "Customer Experience",
    "SALES & BUSINESS DEVELOPMENT": "Sales & Business Development",
    "MARKETING & CREATIVE": "Marketing & Creative",
    "OPERATIONS & ADMIN": "Operations & Admin",
    "TECHNICAL & IT": "Technical & IT",
    "SPECIALIZED SERVICES": "Specialized Services",
}

LEGACY_CODE_MAP = {
    "AUTHOR-01": "Author-01",
    "ASSISTANT-01": "Assistant-01",
    "ASSIST-01": "Assistant-01",
    "GREETER-01": "Greeter-01",
}


def canonical_code(code: str) -> str:
    raw = (code or "").strip()
    if not raw:
        return raw
    upper = raw.upper()
    if upper in LEGACY_CODE_MAP:
        return LEGACY_CODE_MAP[upper]
    if "-" not in raw:
        return upper
    prefix, suffix = raw.rsplit("-", 1)
    return f"{prefix.upper()}-{suffix}"


ACTIVE_ROUTES = {
    "Author-01": {
        "llm_profile": {"default": "claude_opus"},
        "llm_provider": "anthropic",
        "llm_model": "claude-opus-4-5-20251101",
        "system_prompt": (
            "You are Author-01, a specialized Content Writer deployed by The CreddyPens Directorate. "
            "Your function is to produce high-quality written content including blog posts, YouTube scripts, ad copy, "
            "email sequences, and video sales letters. You write in the client's brand voice as defined in their "
            "configuration profile. You always produce well-researched, structured, and engaging content. You do not "
            "produce content that is misleading, defamatory, or violates copyright. When asked to write on a topic you "
            "do not have sufficient information about, you ask one clarifying question before proceeding."
        ),
    },
    "Assistant-01": {
        "llm_profile": {"default": "claude_sonnet"},
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-5-20250929",
        "system_prompt": (
            "You are Assistant-01, a Virtual Assistant deployed by The CreddyPens Directorate. Your function is to help "
            "with email drafting, meeting scheduling, task organization, research summarization, and general operational "
            "support. You are efficient, precise, and professional. You do not make commitments on behalf of the client "
            "without explicit instruction. You do not access external systems unless the client has configured an "
            "integration. When a task is outside your capability, you say so clearly and suggest what the client should "
            "do instead."
        ),
    },
    "Greeter-01": {
        "llm_profile": {"default": "claude_sonnet"},
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-5-20250929",
        "system_prompt": (
            "You are Greeter-01, an AI Receptionist deployed by The CreddyPens Directorate on behalf of the client "
            "company specified in your configuration. Your function is to handle inbound customer inquiries "
            "professionally and warmly. You answer common questions using the company information provided in your "
            "configuration. You collect the customer's name and the purpose of their inquiry. You route complex or "
            "sensitive issues by informing the customer that a team member will follow up. You never fabricate "
            "information about the company. You never discuss pricing, contracts, or legal matters unless the client "
            "has explicitly provided that information in your configuration."
        ),
    },
}

DEFAULT_ROUTE = {
    "llm_profile": {"default": "claude_sonnet"},
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-4-5-20250929",
}


def build_default_system_prompt(item: dict, code: str) -> str:
    human_name = (item.get("human_name") or "").strip() or code
    role = (item.get("role") or "").strip() or "specialized AI professional"
    department = DEPARTMENT_MAP.get(str(item.get("department", "")).strip(), str(item.get("department", "")).strip() or "Directorate")
    description = (item.get("description") or "").strip()
    capabilities = item.get("capabilities") or []
    cap_lines = []
    for capability in capabilities[:8]:
        text_value = str(capability).strip()
        if text_value:
            cap_lines.append(f"- {text_value}")
    caps_text = "\n".join(cap_lines) if cap_lines else "- Execute assigned tasks accurately and professionally."

    return (
        f"You are {code} ({human_name}), a {role} in {department} at The CreddyPens Directorate.\n"
        "Operate as an elite AI employee: clear, professional, outcome-driven, and aligned to the client context.\n\n"
        f"Mission:\n{description}\n\n"
        f"Core capabilities:\n{caps_text}\n\n"
        "Safety boundaries:\n"
        "- Do not provide definitive legal advice, financial advice, or medical diagnosis.\n"
        "- Do not fabricate facts, policies, or pricing details that were not provided by the client.\n"
        "- If asked to act outside your scope, state the limitation clearly and suggest the right escalation path.\n"
    ).strip()


def load_dossiers() -> list[dict]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dossier data file not found: {DATA_PATH}")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Dossier data is empty or invalid")
    return data


def to_seed_row(item: dict) -> dict:
    code = canonical_code(str(item.get("code", "")).strip())
    route = ACTIVE_ROUTES.get(code, DEFAULT_ROUTE)
    system_prompt = route.get("system_prompt") or build_default_system_prompt(item, code)
    return {
        "agent_id": code.lower(),
        "code": code,
        "name": str(item.get("role", "")).strip() or code,
        "human_name": str(item.get("human_name", "")).strip() or None,
        "tagline": str(item.get("tagline", "")).strip() or None,
        "description": str(item.get("description", "")).strip() or "",
        "profile": str(item.get("profile", "")).strip() or "",
        "capabilities": item.get("capabilities") or [],
        "operational_sections": item.get("operational_sections") or [],
        "ideal_for": str(item.get("ideal_for", "")).strip() or None,
        "personality": str(item.get("personality", "")).strip() or None,
        "communication_style": str(item.get("communication_style", "")).strip() or None,
        "department": DEPARTMENT_MAP.get(str(item.get("department", "")).strip(), str(item.get("department", "")).strip()),
        "price_cents": int(item.get("price_cents") or 0),
        "status": "active",
        "llm_profile": route["llm_profile"],
        "llm_provider": route["llm_provider"],
        "llm_model": route["llm_model"],
        "system_prompt": system_prompt,
    }


def main() -> None:
    ensure_schema(engine)
    dossiers = load_dossiers()
    rows = [to_seed_row(item) for item in dossiers]
    expected_agent_ids = [row["agent_id"] for row in rows]

    ensure_columns_sql = text(
        """
        alter table if exists agent_catalog add column if not exists human_name text;
        alter table if exists agent_catalog add column if not exists tagline text;
        alter table if exists agent_catalog add column if not exists profile text not null default '';
        alter table if exists agent_catalog add column if not exists capabilities jsonb not null default '[]'::jsonb;
        alter table if exists agent_catalog add column if not exists operational_sections jsonb not null default '[]'::jsonb;
        alter table if exists agent_catalog add column if not exists ideal_for text;
        alter table if exists agent_catalog add column if not exists personality text;
        alter table if exists agent_catalog add column if not exists communication_style text;
        """
    )
    delete_stale_agents_sql = text("delete from agent_catalog where agent_id not in :agent_ids").bindparams(
        bindparam("agent_ids", expanding=True)
    )

    upsert_agent_sql = text(
        """
        insert into agent_catalog
          (
            agent_id, code, name, human_name, tagline, description, profile, capabilities, operational_sections,
            ideal_for, personality, communication_style, department, price_cents, status,
            llm_profile, llm_provider, llm_model, system_prompt
          )
        values
          (
            :agent_id, :code, :name, :human_name, :tagline, :description, :profile,
            cast(:capabilities as jsonb), cast(:operational_sections as jsonb),
            :ideal_for, :personality, :communication_style, :department, :price_cents, :status,
            cast(:llm_profile as jsonb), :llm_provider, :llm_model, :system_prompt
          )
        on conflict (agent_id) do update set
          code = excluded.code,
          name = excluded.name,
          human_name = excluded.human_name,
          tagline = excluded.tagline,
          description = excluded.description,
          profile = excluded.profile,
          capabilities = excluded.capabilities,
          operational_sections = excluded.operational_sections,
          ideal_for = excluded.ideal_for,
          personality = excluded.personality,
          communication_style = excluded.communication_style,
          department = excluded.department,
          price_cents = excluded.price_cents,
          status = excluded.status,
          llm_profile = excluded.llm_profile,
          llm_provider = excluded.llm_provider,
          llm_model = excluded.llm_model,
          system_prompt = excluded.system_prompt,
          updated_at = now();
        """
    )

    upsert_org_sql = text(
        """
        insert into organizations (org_id, name)
        values (:org_id, :name)
        on conflict (org_id) do update set
          name = excluded.name;
        """
    )

    upsert_hired_sql = text(
        """
        insert into hired_agents (hired_agent_id, org_id, agent_code, status, configuration)
        values (:hired_agent_id, :org_id, :agent_code, :status, cast(:configuration as jsonb))
        on conflict (org_id, agent_code) do update set
          status = excluded.status,
          configuration = excluded.configuration,
          updated_at = now();
        """
    )

    upsert_user_sql = text(
        """
        insert into users (user_id, org_id, email)
        values (:user_id, :org_id, :email)
        on conflict (user_id) do update set
          org_id = excluded.org_id,
          email = excluded.email;
        """
    )

    with engine.begin() as conn:
        conn.execute(ensure_columns_sql)
        conn.execute(delete_stale_agents_sql, {"agent_ids": expected_agent_ids})
        for row in rows:
            payload = {
                **row,
                "capabilities": json.dumps(row["capabilities"]),
                "operational_sections": json.dumps(row["operational_sections"]),
                "llm_profile": json.dumps(row["llm_profile"]),
            }
            conn.execute(upsert_agent_sql, payload)

        # Dev org + hires (v1 launch trio)
        conn.execute(upsert_org_sql, {"org_id": "org_test", "name": "Test Organization"})
        conn.execute(upsert_user_sql, {"user_id": "user_test", "org_id": "org_test", "email": "test@example.com"})
        for code in ["Author-01", "Assistant-01", "Greeter-01"]:
            conn.execute(
                upsert_hired_sql,
                {
                    "hired_agent_id": str(uuid.uuid4()),
                    "org_id": "org_test",
                    "agent_code": code,
                    "status": "active",
                    "configuration": json.dumps(
                        {
                            "company_name": "TestCo",
                            "tone": "professional",
                            "additional": {},
                        }
                    ),
                },
            )

    print(f"Seeded {len(rows)} agents from {DATA_PATH.name}")


if __name__ == "__main__":
    main()
