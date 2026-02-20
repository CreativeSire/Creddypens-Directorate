from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal
from app.schema import ensure_schema
from app.db import engine

SAMPLE_DOCS = [
    {
        "title": "CreddyPens Hours of Operation",
        "content": """
        CreddyPens operates Monday through Friday, 9:00 AM to 6:00 PM EST.
        Weekend support is available by appointment only.
        Emergency support: Contact your account manager.
        """,
        "category": "company_info",
        "tags": ["hours", "schedule", "availability", "support"],
    },
    {
        "title": "Agent Pricing Structure",
        "content": """
        AI agents are priced per agent per month based on role complexity:
        - Receptionist, Assistant agents: $99/month
        - Support, Sales agents: $199/month
        - Technical, Creative agents: $299/month
        - Enterprise plans: Volume discounts available for 10+ agents
        - All plans include unlimited conversations and 24/7 availability
        """,
        "category": "pricing",
        "tags": ["pricing", "plans", "cost", "billing"],
    },
    {
        "title": "New Customer Onboarding Process",
        "content": """
        Getting started with CreddyPens:
        1. Sign up for an account at creddypens.com
        2. Browse the agent catalog and select roles that fit your needs
        3. Complete checkout (credit card or invoice billing available)
        4. Agents are immediately available in your dashboard
        5. Start delegating work through the chat interface
        Training and support are included with all plans.
        """,
        "category": "onboarding",
        "tags": ["setup", "getting started", "new customers", "tutorial"],
    },
    {
        "title": "Agent Specializations and Departments",
        "content": """
        CreddyPens offers 44 specialized AI agents across 6 departments:
        - Customer Service: Receptionists, Support Specialists, Success Managers
        - Sales: Business Development, Qualification, Closing
        - Technical: Engineers, DevOps, QA, API Integration
        - Creative: Content Writers, Designers, Social Media Managers
        - Operations: Project Managers, Analysts, Coordinators
        - HR: Recruiters, Trainers, Onboarding Specialists
        Each agent has domain expertise and can collaborate with other agents.
        """,
        "category": "product_info",
        "tags": ["agents", "departments", "roles", "capabilities"],
    },
    {
        "title": "Data Security and Privacy",
        "content": """
        CreddyPens takes data security seriously:
        - All data encrypted in transit (TLS 1.3) and at rest (AES-256)
        - SOC 2 Type II compliant infrastructure
        - GDPR and CCPA compliant
        - Conversations are isolated per organization
        - No training on customer data without explicit consent
        - Enterprise customers can request on-premise deployment
        """,
        "category": "security",
        "tags": ["security", "privacy", "compliance", "data protection"],
    },
    {
        "title": "Integration Capabilities",
        "content": """
        CreddyPens integrates with popular business tools:
        - CRM: Salesforce, HubSpot, Pipedrive
        - Communication: Slack, Microsoft Teams, Email
        - Project Management: Asana, Jira, Monday.com
        - Documentation: Notion, Confluence, Google Docs
        - Custom integrations available via REST API and webhooks
        """,
        "category": "integrations",
        "tags": ["integrations", "api", "tools", "connectivity"],
    },
    {
        "title": "Cancellation and Refund Policy",
        "content": """
        - Month-to-month plans: Cancel anytime, no long-term commitment
        - Cancellation takes effect at end of current billing period
        - Unused time is not refundable
        - 7-day money-back guarantee for new customers
        - Enterprise contracts: Contact your account manager
        - Agents can be paused (not billed) without cancellation
        """,
        "category": "billing",
        "tags": ["cancellation", "refund", "billing", "policy"],
    },
]


def main() -> None:
    ensure_schema(engine)
    print("Seeding knowledge base...")
    inserted = 0
    updated = 0
    with SessionLocal() as db:
        for doc in SAMPLE_DOCS:
            existing = db.execute(
                text("select id from knowledge_base where title = :title limit 1;"),
                {"title": doc["title"]},
            ).mappings().first()
            if existing:
                db.execute(
                    text(
                        """
                        update knowledge_base
                        set content = :content,
                            category = :category,
                            tags = :tags,
                            created_by = 'seed_script',
                            is_active = true,
                            updated_at = now()
                        where id = :id;
                        """
                    ),
                    {
                        "id": existing["id"],
                        "content": doc["content"].strip(),
                        "category": doc["category"],
                        "tags": doc["tags"],
                    },
                )
                updated += 1
                print(f"~ Updated: {doc['title']}")
            else:
                db.execute(
                    text(
                        """
                        insert into knowledge_base (title, content, category, tags, created_by, is_active)
                        values (:title, :content, :category, :tags, 'seed_script', true);
                        """
                    ),
                    {
                        "title": doc["title"],
                        "content": doc["content"].strip(),
                        "category": doc["category"],
                        "tags": doc["tags"],
                    },
                )
                inserted += 1
                print(f"+ Added: {doc['title']}")
        db.commit()
        total = db.execute(
            text("select count(*)::int from knowledge_base where is_active = true;")
        ).scalar_one()
    print(f"\nInserted: {inserted}, Updated: {updated}, Total active documents: {int(total or 0)}")


if __name__ == "__main__":
    main()

