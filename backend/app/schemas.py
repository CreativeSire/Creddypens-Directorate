from __future__ import annotations

from pydantic import BaseModel, Field


class AgentOut(BaseModel):
    agent_id: str
    code: str
    role: str = Field(description="Role title shown on dossier")
    human_name: str | None = None
    tagline: str | None = None
    description: str
    capabilities: list[str] = Field(default_factory=list)
    ideal_for: str | None = None
    personality: str | None = None
    communication_style: str | None = None
    department: str
    price_cents: int
    status: str
    operational_rating: float | None = Field(default=None, description="0-10 public aggregate rating")


class AgentDetailOut(AgentOut):
    profile: str = ""
    operational_sections: list[dict] = Field(default_factory=list)
