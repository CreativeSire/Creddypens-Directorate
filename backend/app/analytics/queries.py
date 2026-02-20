from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(1, days))


def get_overview(db: Session, org_id: str, days: int = 30) -> dict:
    since = _since(days)
    row = db.execute(
        text(
            """
            select
              coalesce(count(*), 0)::int as total_interactions,
              coalesce(count(distinct agent_code), 0)::int as active_agents,
              coalesce(avg(latency_ms), 0)::float as avg_latency_ms,
              coalesce(avg(quality_score), 0)::float as avg_quality_score,
              coalesce(sum(tokens_used), 0)::bigint as total_tokens
            from interaction_logs
            where org_id = :org_id and created_at >= :since
            """
        ),
        {"org_id": org_id, "since": since},
    ).mappings().first()

    tasks = db.execute(
        text(
            """
            select
              count(*)::int as total_tasks,
              coalesce(sum(case when status='completed' then 1 else 0 end),0)::int as completed_tasks
            from task_inbox
            where org_id = :org_id and created_at >= :since
            """
        ),
        {"org_id": org_id, "since": since},
    ).mappings().first()

    total_tasks = int((tasks or {}).get("total_tasks") or 0)
    completed_tasks = int((tasks or {}).get("completed_tasks") or 0)
    completion_rate = (completed_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0

    data = dict(row or {})
    data["days"] = max(1, days)
    data["task_completion_rate"] = round(completion_rate, 2)
    data["total_tasks"] = total_tasks
    data["completed_tasks"] = completed_tasks
    return data


def get_costs_by_department(db: Session, org_id: str, days: int = 30) -> dict:
    since = _since(days)
    rows = db.execute(
        text(
            """
            select
              coalesce(ac.department, 'Unassigned') as department,
              count(*)::int as interactions,
              coalesce(sum(il.tokens_used),0)::bigint as tokens_used,
              coalesce(
                sum(
                  case
                    when il.model_used ilike '%opus%' then (il.tokens_used::numeric / 1000.0) * 0.015
                    when il.model_used ilike '%sonnet%' then (il.tokens_used::numeric / 1000.0) * 0.003
                    when il.model_used ilike '%gpt%' then (il.tokens_used::numeric / 1000.0) * 0.005
                    when il.model_used ilike '%gemini%' then (il.tokens_used::numeric / 1000.0) * 0.0015
                    when il.model_used ilike '%llama%' then (il.tokens_used::numeric / 1000.0) * 0.0008
                    else (il.tokens_used::numeric / 1000.0) * 0.001
                  end
                ),
                0
              )::float as estimated_cost_usd
            from interaction_logs il
            left join agent_catalog ac on ac.code = il.agent_code
            where il.org_id = :org_id and il.created_at >= :since
            group by coalesce(ac.department, 'Unassigned')
            order by estimated_cost_usd desc
            """
        ),
        {"org_id": org_id, "since": since},
    ).mappings().all()

    by_department = [dict(item) for item in rows]
    total_cost = sum(float(item.get("estimated_cost_usd") or 0.0) for item in by_department)
    return {"days": max(1, days), "total_estimated_cost_usd": round(total_cost, 4), "departments": by_department}


def get_activity_timeseries(db: Session, org_id: str, days: int = 30) -> dict:
    since = _since(days)
    rows = db.execute(
        text(
            """
            select
              date_trunc('day', created_at) as day,
              count(*)::int as interactions,
              coalesce(avg(latency_ms), 0)::float as avg_latency_ms,
              coalesce(avg(quality_score), 0)::float as avg_quality_score,
              coalesce(sum(tokens_used),0)::bigint as tokens_used
            from interaction_logs
            where org_id = :org_id and created_at >= :since
            group by date_trunc('day', created_at)
            order by day asc
            """
        ),
        {"org_id": org_id, "since": since},
    ).mappings().all()

    task_rows = db.execute(
        text(
            """
            select
              date_trunc('day', created_at) as day,
              count(*)::int as tasks_created,
              coalesce(sum(case when status='completed' then 1 else 0 end),0)::int as tasks_completed
            from task_inbox
            where org_id = :org_id and created_at >= :since
            group by date_trunc('day', created_at)
            order by day asc
            """
        ),
        {"org_id": org_id, "since": since},
    ).mappings().all()

    task_map = {str(item["day"]): dict(item) for item in task_rows}
    series = []
    for row in rows:
        key = str(row["day"])
        tasks = task_map.get(key, {})
        series.append(
            {
                "day": row["day"],
                "interactions": int(row["interactions"] or 0),
                "avg_latency_ms": float(row["avg_latency_ms"] or 0.0),
                "avg_quality_score": float(row["avg_quality_score"] or 0.0),
                "tokens_used": int(row["tokens_used"] or 0),
                "tasks_created": int(tasks.get("tasks_created") or 0),
                "tasks_completed": int(tasks.get("tasks_completed") or 0),
            }
        )

    return {"days": max(1, days), "series": series}

