from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class BootstrapOut(BaseModel):
    org_id: str
    user_id: str
    email: str = ""


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)

