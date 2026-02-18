from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.academy.scenarios import ScenarioGenerator
from app.db import SessionLocal
from app.models import AgentCatalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic test scenarios for all agents.")
    parser.add_argument("--count", type=int, default=25, help="Scenarios per agent (default: 25)")
    parser.add_argument("--only", type=str, default="", help="Only this agent code (optional)")
    args = parser.parse_args()

    gen = ScenarioGenerator()

    with SessionLocal() as db:
        stmt = select(AgentCatalog)
        if args.only:
            stmt = stmt.where(AgentCatalog.code == args.only)
        agents = db.execute(stmt.order_by(AgentCatalog.code.asc())).scalars().all()
        now = datetime.now(timezone.utc)

        created = 0
        for a in agents:
            scenarios = gen.generate(role=a.name, count=args.count)
            for s in scenarios:
                db.execute(
                    text(
                        """
                        insert into test_scenarios (agent_code, scenario_type, difficulty, user_message, expected_qualities, created_at, is_active)
                        values (:agent_code, :scenario_type, :difficulty, :user_message, :expected_qualities, :created_at, true);
                        """
                    ),
                    {
                        "agent_code": a.code,
                        "scenario_type": s.scenario_type,
                        "difficulty": s.difficulty,
                        "user_message": s.user_message,
                        "expected_qualities": s.expected_qualities,
                        "created_at": now,
                    },
                )
                created += 1

        db.commit()

    print(f"Created {created} scenarios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

