from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import text

# Allow running as `python scripts/retrain_selected_agents.py`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.academy.synthetic import SyntheticTrainer
from app.db import SessionLocal
from app.schema import ensure_schema


DEFAULT_AGENTS = [
    "Author-01",
    "DATA-02",
    "ONBOARD-01",
    "DEVOPS-01",
    "QUALIFIER-01",
    "SOCIAL-01",
]


def _latest_scores(agent_codes: list[str]) -> dict[str, float]:
    with SessionLocal() as db:
        ensure_schema(db.get_bind())
        rows = (
            db.execute(
                text(
                    """
                    with latest as (
                      select
                        ts.agent_code,
                        ts.avg_quality_score,
                        row_number() over(partition by ts.agent_code order by ts.started_at desc) as rn
                      from training_sessions ts
                      where ts.session_type = 'synthetic'
                        and ts.status = 'completed'
                        and ts.agent_code = any(:codes)
                    )
                    select agent_code, avg_quality_score
                    from latest
                    where rn = 1;
                    """
                ),
                {"codes": agent_codes},
            )
            .mappings()
            .all()
        )
    return {str(r["agent_code"]): float(r["avg_quality_score"] or 0) for r in rows}


def _agent_names(agent_codes: list[str]) -> dict[str, str]:
    with SessionLocal() as db:
        ensure_schema(db.get_bind())
        rows = (
            db.execute(
                text(
                    """
                    select code as agent_code, coalesce(human_name, name) as human_name
                    from agent_catalog
                    where code = any(:codes);
                    """
                ),
                {"codes": agent_codes},
            )
            .mappings()
            .all()
        )
    return {str(r["agent_code"]): str(r["human_name"] or r["agent_code"]) for r in rows}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Targeted synthetic re-training for selected agents.")
    parser.add_argument(
        "--agents",
        type=str,
        default=",".join(DEFAULT_AGENTS),
        help="Comma-separated agent codes",
    )
    parser.add_argument("--conversations", type=int, default=25, help="Conversations per agent")
    parser.add_argument(
        "--csv",
        type=str,
        default="reports/retrain_deltas.csv",
        help="CSV output path",
    )
    args = parser.parse_args()

    agent_codes = [a.strip() for a in args.agents.split(",") if a.strip()]
    trainer = SyntheticTrainer()

    before = _latest_scores(agent_codes)
    names = _agent_names(agent_codes)

    print(f"Re-training {len(agent_codes)} agents with {args.conversations} conversations each")
    print("Agents:", ", ".join(agent_codes))
    print("\nBaseline scores:")
    for code in agent_codes:
        print(f" - {code}: {before.get(code, 0):.2f}")

    results = []
    for code in agent_codes:
        result = await trainer.train_agent(agent_code=code, conversation_count=args.conversations)
        after_score = float(result.get("avg_quality_score") or 0)
        delta = after_score - float(before.get(code, 0))
        results.append(
            {
                "agent_code": code,
                "human_name": names.get(code, code),
                "before_score": float(before.get(code, 0)),
                "after_score": after_score,
                "delta": round(delta, 2),
                "conversations": int(result.get("conversations") or 0),
                "high_scores": int(result.get("high_scores") or 0),
                "low_scores": int(result.get("low_scores") or 0),
                "session_id": str(result.get("session_id") or ""),
            }
        )
        print(
            f"[OK] {code}: {before.get(code, 0):.2f} -> {after_score:.2f} "
            f"(d {delta:+.2f})"
        )

    out = Path(args.csv)
    if not out.is_absolute():
        out = BACKEND_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "agent_code",
                "human_name",
                "before_score",
                "after_score",
                "delta",
                "conversations",
                "high_scores",
                "low_scores",
                "session_id",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDelta report written: {out}")

    improved = [r for r in results if r["delta"] > 0]
    print(f"Improved agents: {len(improved)}/{len(results)}")
    for r in sorted(results, key=lambda x: x["delta"]):
        print(f" - {r['agent_code']}: {r['before_score']:.2f} -> {r['after_score']:.2f} (d {r['delta']:+.2f})")


if __name__ == "__main__":
    asyncio.run(main())
