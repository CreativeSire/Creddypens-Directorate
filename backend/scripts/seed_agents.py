from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import engine


SEED = [
    {
        "agent_id": "author-01",
        "code": "Author-01",
        "name": "Content Writer",
        "description": "Writes blog posts, social captions, newsletters, and landing-page copy in your brand voice.",
        "department": "Marketing & Creative",
        "price_cents": 24900,
        "status": "active",
        "llm_profile": {"default": "claude_sonnet"},
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
    {
        "agent_id": "assistant-01",
        "code": "Assistant-01",
        "name": "Virtual Assistant",
        "description": "Handles admin tasks, drafting, research, checklists, and day-to-day operational support.",
        "department": "Operations & Admin",
        "price_cents": 14900,
        "status": "active",
        "llm_profile": {"default": "grok_fast"},
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
    {
        "agent_id": "greeter-01",
        "code": "Greeter-01",
        "name": "AI Receptionist",
        "description": "Text-based customer intake for your site and dashboard: FAQs, triage, and escalation routing.",
        "department": "Customer Experience",
        "price_cents": 14900,
        "status": "active",
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
]

DEPARTMENTS = [
    "Customer Experience",
    "Sales & Business Dev",
    "Marketing & Creative",
    "Operations & Admin",
    "Technical & IT",
    "Specialized Services",
]

COMING_SOON_PLACEHOLDERS = [
    {
        "agent_id": f"coming-{i:02d}",
        "code": f"Clearance-{i:02d}",
        "name": "Clearance Pending",
        "description": "This asset is not yet cleared for deployment.",
        "department": DEPARTMENTS[(i - 1) % len(DEPARTMENTS)],
        "price_cents": 0,
        "status": "coming_soon",
        "llm_profile": {"default": "tbd"},
        "llm_provider": None,
        "llm_model": None,
        "system_prompt": "",
    }
    for i in range(1, 40)
]


def main() -> None:
    upsert_agent_sql = text(
        """
        insert into agent_catalog
          (agent_id, code, name, description, department, price_cents, status, llm_profile, llm_provider, llm_model, system_prompt)
        values
          (:agent_id, :code, :name, :description, :department, :price_cents, :status,
           cast(:llm_profile as jsonb), :llm_provider, :llm_model, :system_prompt)
        on conflict (agent_id) do update set
          code = excluded.code,
          name = excluded.name,
          description = excluded.description,
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
        for row in [*SEED, *COMING_SOON_PLACEHOLDERS]:
            payload = {
                **row,
                "llm_profile": json.dumps(row.get("llm_profile") or {}),
            }
            conn.execute(upsert_agent_sql, payload)

        # Dev org + hires (mocked validation structure for v1)
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


if __name__ == "__main__":
    main()
