from __future__ import annotations

from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=20000)


class ChatOut(BaseModel):
    reply: str
