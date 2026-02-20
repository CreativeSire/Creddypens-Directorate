from __future__ import annotations

from pydantic import BaseModel, Field


class AttachmentRef(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    mime_type: str | None = None
    content_excerpt: str | None = Field(default=None, max_length=2000)
    size_bytes: int | None = None


class ExecuteContext(BaseModel):
    company_name: str | None = None
    tone: str | None = None
    output_format: str | None = None
    web_search: bool = False
    doc_retrieval: bool = True
    deep_research: bool = False
    attachments: list[AttachmentRef] = Field(default_factory=list)
    additional: dict = Field(default_factory=dict)


class ExecuteIn(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    context: ExecuteContext = Field(default_factory=ExecuteContext)
    session_id: str = Field(min_length=1, max_length=128)


class SuggestedAgent(BaseModel):
    """Returned when the responding agent detects the question is outside its domain."""

    code: str
    name: str
    tagline: str | None = None
    department: str | None = None
    # Human-readable reason why this colleague was suggested
    reason: str
    # Whether the org already has this agent hired (true → free handoff, false → hire/one-shot gate)
    is_hired: bool
    # The original user question, forwarded so the referred agent has context when the user switches
    handoff_context: str


class ExecuteOut(BaseModel):
    agent_code: str
    response: str
    model_used: str
    search_used: bool = False
    docs_used: bool = False
    latency_ms: int
    tokens_used: int = 0
    interaction_id: str | None = None
    trace_id: str
    session_id: str
    # Referral fields — populated only when the agent suggests a colleague
    referral_triggered: bool = False
    suggested_agent: SuggestedAgent | None = None
