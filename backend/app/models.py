from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AgentCatalog(Base):
    __tablename__ = "agent_catalog"

    agent_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    human_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tagline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[str] = mapped_column(Text, nullable=False, default="")
    capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    operational_sections: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    ideal_for: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    communication_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department: Mapped[str] = mapped_column(String(64), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="coming_soon")
    llm_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Organization(Base):
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class HiredAgent(Base):
    __tablename__ = "hired_agents"

    hired_agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    interaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model_used: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ResponseEvaluation(Base):
    __tablename__ = "response_evaluations"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    interaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    org_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_criteria: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evaluated_by: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentPromptVersion(Base):
    __tablename__ = "agent_prompt_versions"

    prompt_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    agent_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    changes_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    performance_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TrainingScenario(Base):
    __tablename__ = "training_scenarios"

    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    agent_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    expected_capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TrainingRun(Base):
    __tablename__ = "training_runs"

    training_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    agent_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False, default="synthetic")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    scenarios_tested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    improvements_identified: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
