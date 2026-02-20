from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.academy import router as academy_router
from app.api.files import router as files_router
from app.db import engine
from app.schema import ensure_schema
from app.settings import settings

app = FastAPI(title="CreddyPens API", version="0.1.0")

if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    except Exception:
        pass

allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(academy_router)
app.include_router(files_router)


@app.on_event("startup")
def _ensure_schema() -> None:
    try:
        ensure_schema(engine)
    except Exception:
        # Local dev convenience: don't crash the API if the DB isn't running yet.
        # DB-backed endpoints will fail until Postgres is available.
        return
