from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Protocol

from sqlalchemy import text

from app.db import SessionLocal


@dataclass
class RuntimeEvent:
    event_type: str
    org_id: str | None = None
    session_id: str | None = None
    agent_code: str | None = None
    payload: dict | None = None
    created_at: datetime | None = None


class RuntimeHook(Protocol):
    def handle(self, event: RuntimeEvent) -> None: ...


class RuntimeEventStoreHook:
    """Persist runtime events for audit/ops telemetry."""

    def handle(self, event: RuntimeEvent) -> None:
        ts = event.created_at or datetime.now(timezone.utc)
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    insert into runtime_events (org_id, session_id, agent_code, event_type, payload, created_at)
                    values (:org_id, :session_id, :agent_code, :event_type, cast(:payload as jsonb), :created_at);
                    """
                ),
                {
                    "org_id": event.org_id,
                    "session_id": event.session_id,
                    "agent_code": event.agent_code,
                    "event_type": event.event_type,
                    "payload": json.dumps(event.payload or {}),
                    "created_at": ts,
                },
            )
            db.commit()


class RuntimeHookBus:
    def __init__(self) -> None:
        self._hooks: list[RuntimeHook] = [RuntimeEventStoreHook()]

    def register(self, hook: RuntimeHook) -> None:
        self._hooks.append(hook)

    def emit(self, event: RuntimeEvent) -> None:
        for hook in self._hooks:
            try:
                hook.handle(event)
            except Exception:
                # Hooks must be non-blocking/non-fatal.
                continue


hook_bus = RuntimeHookBus()

