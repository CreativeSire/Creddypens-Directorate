from __future__ import annotations

from pydantic import BaseModel, Field


class ExecuteContext(BaseModel):
    company_name: str | None = None
    tone: str | None = None
    additional: dict = Field(default_factory=dict)


class ExecuteIn(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    context: ExecuteContext = Field(default_factory=ExecuteContext)
    session_id: str = Field(min_length=1, max_length=128)


class ExecuteOut(BaseModel):
    agent_code: str
    response: str
    model_used: str
    latency_ms: int
    tokens_used: int = 0
    interaction_id: str | None = None
    trace_id: str
    session_id: str
