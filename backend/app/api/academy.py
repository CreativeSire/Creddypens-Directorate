from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(prefix="/v1/academy", tags=["academy"])


class FeedbackSubmit(BaseModel):
    interaction_id: str = Field(min_length=1)
    rating: int = Field(ge=-1, le=1)
    category: str | None = None
    text: str | None = None


class TrainingSessionCreate(BaseModel):
    agent_code: str = Field(min_length=1, max_length=32)
    session_type: str = Field(min_length=1, max_length=50)


def calculate_quality_score(rating: int, category: str | None) -> float:
    base_scores = {1: 85.0, 0: 50.0, -1: 20.0}
    score = base_scores.get(rating, 50.0)
    cat = (category or "").strip().lower()
    if cat == "helpful":
        score += 5
    elif cat == "accurate":
        score += 5
    elif cat == "tone":
        score += 3
    return float(min(100.0, max(0.0, score)))


def update_daily_metrics(agent_code: str, metric_date: date, db: Session) -> None:
    # Aggregate from interaction_logs (today) and upsert.
    db.execute(
        text(
            """
            insert into agent_performance_metrics (
              agent_code,
              metric_date,
              total_interactions,
              positive_ratings,
              negative_ratings,
              neutral_ratings,
              avg_latency_ms,
              avg_quality_score,
              avg_response_length,
              successful_resolutions,
              escalations
            )
            select
              :agent_code,
              :metric_date,
              count(*)::int,
              count(*) filter (where user_rating = 1)::int,
              count(*) filter (where user_rating = -1)::int,
              count(*) filter (where user_rating = 0)::int,
              coalesce(avg(latency_ms), 0)::int,
              coalesce(avg(quality_score), 0)::float,
              coalesce(avg(length(response)), 0)::int,
              count(*) filter (where user_rating = 1)::int,
              count(*) filter (where user_rating = -1)::int
            from interaction_logs
            where agent_code = :agent_code and created_at::date = :metric_date
            on conflict (agent_code, metric_date) do update set
              total_interactions = excluded.total_interactions,
              positive_ratings = excluded.positive_ratings,
              negative_ratings = excluded.negative_ratings,
              neutral_ratings = excluded.neutral_ratings,
              avg_latency_ms = excluded.avg_latency_ms,
              avg_quality_score = excluded.avg_quality_score,
              avg_response_length = excluded.avg_response_length,
              successful_resolutions = excluded.successful_resolutions,
              escalations = excluded.escalations;
            """
        ),
        {"agent_code": agent_code, "metric_date": metric_date},
    )


@router.post("/feedback")
def submit_feedback(
    feedback: FeedbackSubmit,
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> dict:
    org_id = x_org_id or "org_test"
    quality_score = calculate_quality_score(feedback.rating, feedback.category)

    row = db.execute(
        text(
            """
            update interaction_logs
            set
              user_rating = :rating,
              feedback_category = :category,
              feedback_text = :text,
              quality_score = :quality_score,
              updated_at = now()
            where interaction_id = nullif(:interaction_id, '')::uuid
              and org_id = :org_id
            returning agent_code;
            """
        ),
        {
            "interaction_id": feedback.interaction_id,
            "org_id": org_id,
            "rating": int(feedback.rating),
            "category": (feedback.category or "").strip() or None,
            "text": (feedback.text or "").strip() or None,
            "quality_score": float(quality_score),
        },
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")

    update_daily_metrics(row["agent_code"], date.today(), db)
    db.commit()
    return {"success": True, "quality_score": quality_score}


@router.get("/agents/{agent_code}/performance")
def get_agent_performance(agent_code: str, days: int = 7, db: Session = Depends(get_db)) -> dict:
    days = max(1, min(90, int(days)))
    since = date.today() - timedelta(days=days)
    metrics = db.execute(
        text(
            """
            select
              metric_date,
              total_interactions,
              positive_ratings,
              negative_ratings,
              neutral_ratings,
              avg_quality_score,
              avg_latency_ms
            from agent_performance_metrics
            where agent_code = :agent_code and metric_date >= :since
            order by metric_date desc;
            """
        ),
        {"agent_code": agent_code, "since": since},
    ).mappings().all()

    return {"agent_code": agent_code, "metrics": [dict(m) for m in metrics]}


@router.post("/training-sessions")
def create_training_session(session: TrainingSessionCreate, db: Session = Depends(get_db)) -> dict:
    row = db.execute(
        text(
            """
            insert into training_sessions (agent_code, session_type)
            values (:agent_code, :session_type)
            returning id, started_at;
            """
        ),
        {"agent_code": session.agent_code, "session_type": session.session_type},
    ).mappings().first()
    db.commit()
    return {"session_id": str(row["id"]), "started_at": row["started_at"].isoformat() if row else None}


@router.get("/training-sessions/{session_id}")
def get_training_session(session_id: UUID, db: Session = Depends(get_db)) -> dict:
    row = db.execute(
        text(
            """
            select
              id,
              agent_code,
              session_type,
              started_at,
              completed_at,
              total_interactions,
              avg_quality_score,
              status,
              improvement_notes,
              error_message
            from training_sessions
            where id = :id;
            """
        ),
        {"id": str(session_id)},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Training session not found")

    data = dict(row)
    for k in ("started_at", "completed_at"):
        v = data.get(k)
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
    data["id"] = str(data["id"])
    return data


@router.get("/leaderboard")
def get_agent_leaderboard(db: Session = Depends(get_db)) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    rows = db.execute(
        text(
            """
            select
              ac.code as agent_code,
              coalesce(ac.human_name, ac.name) as human_name,
              ac.name as role,
              coalesce(avg(apm.avg_quality_score), 0)::float as avg_score,
              coalesce(sum(apm.total_interactions), 0)::int as total_interactions,
              coalesce(sum(apm.positive_ratings), 0)::int as positive_ratings
            from agent_catalog ac
            left join agent_performance_metrics apm on apm.agent_code = ac.code
            where apm.metric_date >= :since::date
            group by ac.code, ac.human_name, ac.name
            having coalesce(sum(apm.total_interactions), 0) > 0
            order by avg_score desc
            limit 20;
            """
        ),
        {"since": since},
    ).mappings().all()
    return [dict(r) for r in rows]

