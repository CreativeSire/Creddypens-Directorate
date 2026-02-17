from __future__ import annotations

from dataclasses import dataclass

from app.settings import settings


@dataclass(frozen=True)
class LLMProfile:
    route: str
    provider: str
    model: str | None


def resolve_llm_profile(route: str | None) -> LLMProfile | None:
    if not route:
        return None

    route = route.strip()
    match route:
        case "claude_sonnet":
            return LLMProfile(route=route, provider="anthropic", model=settings.anthropic_sonnet_model)
        case "claude_opus":
            return LLMProfile(route=route, provider="anthropic", model=settings.anthropic_opus_model)
        case "gemini_pro":
            return LLMProfile(route=route, provider="google", model=settings.gemini_pro_model)
        case "grok_fast":
            return LLMProfile(route=route, provider="xai", model=settings.grok_fast_model)
        case "grok_reasoning":
            return LLMProfile(route=route, provider="xai", model=settings.grok_reasoning_model)
        case _:
            return LLMProfile(route=route, provider="unknown", model=None)

