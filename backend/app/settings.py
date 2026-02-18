from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Ensure provider SDKs (e.g. LiteLLM) can see API keys from `backend/.env` via os.environ.
# Pydantic's env_file loads values for Settings, but does not automatically populate process env vars.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/creddypens",
        validation_alias="DATABASE_URL",
    )
    allowed_origins: str = Field(default="http://localhost:3000", validation_alias="ALLOWED_ORIGINS")

    # Optional LLM model identifiers (used to surface provider/model in dossiers)
    anthropic_sonnet_model: str | None = Field(default=None, validation_alias="ANTHROPIC_SONNET_MODEL")
    anthropic_opus_model: str | None = Field(default=None, validation_alias="ANTHROPIC_OPUS_MODEL")
    gemini_pro_model: str | None = Field(default=None, validation_alias="GEMINI_PRO_MODEL")
    grok_fast_model: str | None = Field(default=None, validation_alias="GROK_FAST_MODEL")
    grok_reasoning_model: str | None = Field(default=None, validation_alias="GROK_REASONING_MODEL")

    # Dev/testing
    llm_mock: bool = Field(default=False, validation_alias="LLM_MOCK")
    litellm_debug: bool = Field(default=False, validation_alias="LITELLM_DEBUG")
    litellm_timeout_s: int = Field(default=45, validation_alias="LITELLM_TIMEOUT_S")
    litellm_retries: int = Field(default=1, validation_alias="LITELLM_RETRIES")

    # Supabase Auth (frontend uses anon key; backend uses it to validate access tokens)
    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, validation_alias="SUPABASE_ANON_KEY")
    sentry_dsn: str | None = Field(default=None, validation_alias="SENTRY_DSN")
    stripe_secret_key: str | None = Field(default=None, validation_alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, validation_alias="STRIPE_WEBHOOK_SECRET")
    checkout_success_url: str | None = Field(default=None, validation_alias="CHECKOUT_SUCCESS_URL")
    checkout_cancel_url: str | None = Field(default=None, validation_alias="CHECKOUT_CANCEL_URL")


settings = Settings()
