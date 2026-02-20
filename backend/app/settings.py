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
    multi_llm_router_enabled: bool = Field(default=True, validation_alias="MULTI_LLM_ROUTER_ENABLED")
    multi_llm_cache_enabled: bool = Field(default=True, validation_alias="MULTI_LLM_CACHE_ENABLED")
    multi_llm_cache_ttl_s: int = Field(default=3600, validation_alias="MULTI_LLM_CACHE_TTL_S")
    multi_turn_memory_enabled: bool = Field(default=True, validation_alias="MULTI_TURN_MEMORY_ENABLED")
    multi_turn_memory_turns: int = Field(default=6, validation_alias="MULTI_TURN_MEMORY_TURNS")
    workflow_max_steps: int = Field(default=8, validation_alias="WORKFLOW_MAX_STEPS")
    academy_judge_provider: str | None = Field(default="groq", validation_alias="ACADEMY_JUDGE_PROVIDER")
    academy_judge_model: str | None = Field(default="llama-3.3-70b-versatile", validation_alias="ACADEMY_JUDGE_MODEL")

    # Supabase Auth (frontend uses anon key; backend uses it to validate access tokens)
    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, validation_alias="SUPABASE_ANON_KEY")
    sentry_dsn: str | None = Field(default=None, validation_alias="SENTRY_DSN")
    stripe_secret_key: str | None = Field(default=None, validation_alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str | None = Field(default=None, validation_alias="STRIPE_WEBHOOK_SECRET")
    checkout_success_url: str | None = Field(default=None, validation_alias="CHECKOUT_SUCCESS_URL")
    checkout_cancel_url: str | None = Field(default=None, validation_alias="CHECKOUT_CANCEL_URL")
    serper_api_key: str | None = Field(default=None, validation_alias="SERPER_API_KEY")
    enable_web_search: bool = Field(default=True, validation_alias="ENABLE_WEB_SEARCH")
    enable_document_retrieval: bool = Field(default=True, validation_alias="ENABLE_DOCUMENT_RETRIEVAL")
    session_compaction_enabled: bool = Field(default=True, validation_alias="SESSION_COMPACTION_ENABLED")
    session_compaction_turns: int = Field(default=24, validation_alias="SESSION_COMPACTION_TURNS")
    session_context_recent_turns: int = Field(default=8, validation_alias="SESSION_CONTEXT_RECENT_TURNS")
    session_max_parallel_per_org: int = Field(default=50, validation_alias="SESSION_MAX_PARALLEL_PER_ORG")


settings = Settings()
