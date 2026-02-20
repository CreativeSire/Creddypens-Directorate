from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from sqlalchemy import text

# Allow running as `python scripts/analyze_performance.py`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import SessionLocal
from app.schema import ensure_schema


def _safe_subscores(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def analyze_bottom_performers(threshold: float = 89.0) -> list[dict]:
    with SessionLocal() as db:
        ensure_schema(db.get_bind())
        agents = (
            db.execute(
                text(
                    """
                    with latest as (
                      select
                        ts.id as session_id,
                        ts.agent_code,
                        ts.avg_quality_score,
                        row_number() over(partition by ts.agent_code order by ts.started_at desc) as rn
                      from training_sessions ts
                      where ts.session_type = 'synthetic'
                        and ts.status = 'completed'
                    )
                    select
                      ac.code as agent_code,
                      coalesce(ac.human_name, ac.name) as human_name,
                      ac.name as role,
                      ac.system_prompt,
                      l.avg_quality_score,
                      l.session_id
                    from latest l
                    join agent_catalog ac on ac.code = l.agent_code
                    where l.rn = 1
                      and l.avg_quality_score < :threshold
                    order by l.avg_quality_score asc, ac.code asc;
                    """
                ),
                {"threshold": threshold},
            )
            .mappings()
            .all()
        )

        print(f"Found {len(agents)} agents below {threshold}")
        print("\n" + "=" * 60)

        for agent in agents:
            print(f"\nAgent: {agent['human_name']} ({agent['agent_code']})")
            print(f"Score: {float(agent['avg_quality_score'] or 0):.2f}")
            print(f"Role: {agent['role']}")

            evals = (
                db.execute(
                    text(
                        """
                        select
                          user_message,
                          agent_response,
                          quality_score,
                          subscores
                        from evaluation_results
                        where training_session_id = :session_id
                        order by quality_score asc, evaluated_at asc
                        limit 5;
                        """
                    ),
                    {"session_id": str(agent["session_id"])},
                )
                .mappings()
                .all()
            )

            print("\n  Worst 5 Responses:")
            for i, ev in enumerate(evals, 1):
                user = (ev.get("user_message") or "").replace("\n", " ").strip()
                resp = (ev.get("agent_response") or "").replace("\n", " ").strip()
                subs = _safe_subscores(ev.get("subscores"))
                print(f"\n  {i}. Quality: {float(ev.get('quality_score') or 0):.1f}")
                print(f"     User: {user[:120]}{'...' if len(user) > 120 else ''}")
                print(f"     Agent: {resp[:120]}{'...' if len(resp) > 120 else ''}")
                print(
                    "     Subscores: "
                    f"H:{float(subs.get('helpfulness', 0)):.0f} "
                    f"A:{float(subs.get('accuracy', 0)):.0f} "
                    f"P:{float(subs.get('professionalism', 0)):.0f} "
                    f"C:{float(subs.get('completeness', 0)):.0f} "
                    f"Cl:{float(subs.get('clarity', 0)):.0f}"
                )

            print("\n" + "-" * 60)

        return [dict(a) for a in agents]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze bottom-performing agents from latest synthetic training.")
    parser.add_argument("--threshold", type=float, default=89.0, help="Include agents scoring below this value (default: 89.0)")
    parser.add_argument(
        "--csv",
        type=str,
        default="",
        help="Optional CSV output path (e.g. reports/bottom_performers.csv)",
    )
    args = parser.parse_args()

    rows = analyze_bottom_performers(threshold=args.threshold)

    if args.csv:
        out_path = Path(args.csv)
        if not out_path.is_absolute():
            out_path = BACKEND_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with SessionLocal() as db:
            ensure_schema(db.get_bind())
            with out_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "agent_code",
                        "human_name",
                        "role",
                        "avg_quality_score",
                        "session_id",
                        "rank_within_agent_worst5",
                        "quality_score",
                        "helpfulness",
                        "accuracy",
                        "professionalism",
                        "completeness",
                        "clarity",
                        "user_message",
                        "agent_response",
                    ]
                )

                for agent in rows:
                    evals = (
                        db.execute(
                            text(
                                """
                                select user_message, agent_response, quality_score, subscores
                                from evaluation_results
                                where training_session_id = :session_id
                                order by quality_score asc, evaluated_at asc
                                limit 5;
                                """
                            ),
                            {"session_id": str(agent["session_id"])},
                        )
                        .mappings()
                        .all()
                    )
                    for idx, ev in enumerate(evals, start=1):
                        subs = _safe_subscores(ev.get("subscores"))
                        writer.writerow(
                            [
                                agent.get("agent_code"),
                                agent.get("human_name"),
                                agent.get("role"),
                                float(agent.get("avg_quality_score") or 0),
                                str(agent.get("session_id")),
                                idx,
                                float(ev.get("quality_score") or 0),
                                float(subs.get("helpfulness", 0) or 0),
                                float(subs.get("accuracy", 0) or 0),
                                float(subs.get("professionalism", 0) or 0),
                                float(subs.get("completeness", 0) or 0),
                                float(subs.get("clarity", 0) or 0),
                                (ev.get("user_message") or "").replace("\n", " ").strip(),
                                (ev.get("agent_response") or "").replace("\n", " ").strip(),
                            ]
                        )

        print(f"\nCSV written: {out_path}")
