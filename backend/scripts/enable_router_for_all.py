from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

# Allow running as `python scripts/enable_router_for_all.py`
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal


def main() -> int:
    with SessionLocal() as db:
        db.execute(
            text(
                """
                update agent_catalog
                set llm_provider = null,
                    llm_model = null
                where status = 'active';
                """
            )
        )
        db.commit()

        count = db.execute(
            text("select count(*) from agent_catalog where status = 'active' and llm_provider is null and llm_model is null;")
        ).scalar_one()

    print(f"Updated {int(count)} agents to use smart router")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

