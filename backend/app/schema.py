from __future__ import annotations

from sqlalchemy import Engine, text


def ensure_schema(engine: Engine) -> None:
    """
    Minimal, additive schema guard for local dev.

    Docker's `/docker-entrypoint-initdb.d` init scripts only run on first boot of the DB volume,
    so this ensures newly-added tables exist for existing local volumes.
    """
    ddl = """
    create extension if not exists "pgcrypto";
    alter table if exists agent_catalog add column if not exists human_name text;
    alter table if exists agent_catalog add column if not exists tagline text;
    alter table if exists agent_catalog add column if not exists profile text not null default '';
    alter table if exists agent_catalog add column if not exists capabilities jsonb not null default '[]'::jsonb;
    alter table if exists agent_catalog add column if not exists operational_sections jsonb not null default '[]'::jsonb;
    alter table if exists agent_catalog add column if not exists ideal_for text;
    alter table if exists agent_catalog add column if not exists personality text;
    alter table if exists agent_catalog add column if not exists communication_style text;

    create table if not exists interaction_logs (
      interaction_id uuid primary key default gen_random_uuid(),
      org_id text not null references organizations(org_id) on delete cascade,
      agent_code text not null references agent_catalog(code) on delete restrict,
      session_id text not null default '',
      message text not null default '',
      response text not null default '',
      model_used text not null default '',
      latency_ms integer not null default 0,
      trace_id text not null default '',
      created_at timestamptz not null default now()
    );

    create index if not exists idx_interaction_logs_org_created on interaction_logs(org_id, created_at desc);
    create index if not exists idx_interaction_logs_agent_created on interaction_logs(agent_code, created_at desc);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
