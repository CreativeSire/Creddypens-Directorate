from __future__ import annotations

from pydantic import BaseModel, Field


class AgentOut(BaseModel):
    agent_id: str
    code: str
    role: str = Field(description="Role title shown on dossier")
    description: str
    department: str
    price_cents: int
    status: str
    llm_route: str | None = Field(default=None, description="Routing label (e.g. claude_sonnet)")
    llm_provider: str | None = Field(default=None, description="Resolved provider name (e.g. anthropic)")
    llm_model: str | None = Field(default=None, description="Resolved model identifier, if configured")
    llm_profile: dict = Field(default_factory=dict, description="LLM routing profile (e.g. default provider)")
    operational_rating: float | None = Field(default=None, description="0-10 public aggregate rating")


class AgentDetailOut(AgentOut):
    system_prompt: str = ""
