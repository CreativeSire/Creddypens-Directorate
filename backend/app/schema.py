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
    alter table if exists interaction_logs add column if not exists tokens_used integer not null default 0;
    alter table if exists interaction_logs add column if not exists quality_score double precision;
    alter table if exists interaction_logs add column if not exists user_rating integer not null default 0;
    alter table if exists interaction_logs add column if not exists response_time_ms integer;
    alter table if exists interaction_logs add column if not exists total_tokens integer;
    alter table if exists interaction_logs add column if not exists session_id_uuid uuid;
    alter table if exists interaction_logs add column if not exists feedback_text text;
    alter table if exists interaction_logs add column if not exists feedback_category text;
    alter table if exists interaction_logs add column if not exists evaluation_metadata jsonb not null default '{}'::jsonb;
    alter table if exists interaction_logs add column if not exists updated_at timestamptz not null default now();

    create table if not exists interaction_logs (
      interaction_id uuid primary key default gen_random_uuid(),
      org_id text not null references organizations(org_id) on delete cascade,
      agent_code text not null references agent_catalog(code) on delete restrict,
      session_id text not null default '',
      session_id_uuid uuid,
      message text not null default '',
      response text not null default '',
      model_used text not null default '',
      latency_ms integer not null default 0,
      response_time_ms integer,
      trace_id text not null default '',
      tokens_used integer not null default 0,
      total_tokens integer,
      user_rating integer not null default 0,
      feedback_text text,
      feedback_category text,
      evaluation_metadata jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now()
    );
    alter table if exists interaction_logs add column if not exists updated_at timestamptz not null default now();

    create index if not exists idx_interaction_logs_org_created on interaction_logs(org_id, created_at desc);
    create index if not exists idx_interaction_logs_agent_created on interaction_logs(agent_code, created_at desc);
    create index if not exists idx_interaction_logs_org_agent_date on interaction_logs(org_id, agent_code, created_at desc);

    create table if not exists response_evaluations (
      evaluation_id uuid primary key default gen_random_uuid(),
      interaction_id uuid,
      org_id text not null references organizations(org_id) on delete cascade,
      agent_code text not null references agent_catalog(code) on delete restrict,
      quality_score double precision not null,
      evaluation_criteria jsonb not null default '{}'::jsonb,
      evaluated_by text not null default 'auto',
      notes text,
      evaluated_at timestamptz not null default now()
    );
    create index if not exists idx_response_eval_org_agent on response_evaluations(org_id, agent_code, evaluated_at desc);

    create table if not exists agent_prompt_versions (
      prompt_version_id uuid primary key default gen_random_uuid(),
      agent_code text not null references agent_catalog(code) on delete restrict,
      version integer not null,
      system_prompt text not null,
      changes_description text not null default '',
      performance_metrics jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now(),
      unique(agent_code, version)
    );

    create table if not exists training_scenarios (
      scenario_id uuid primary key default gen_random_uuid(),
      agent_code text not null references agent_catalog(code) on delete restrict,
      scenario_name text not null,
      user_message text not null,
      expected_capabilities jsonb not null default '[]'::jsonb,
      difficulty text not null default 'medium',
      created_at timestamptz not null default now()
    );
    create index if not exists idx_training_scenarios_agent on training_scenarios(agent_code);

    create table if not exists training_runs (
      training_run_id uuid primary key default gen_random_uuid(),
      org_id text references organizations(org_id) on delete cascade,
      agent_code text not null references agent_catalog(code) on delete restrict,
      run_type text not null default 'synthetic',
      status text not null default 'running',
      scenarios_tested integer not null default 0,
      avg_quality_score double precision,
      improvements_identified jsonb not null default '{}'::jsonb,
      passed boolean not null default true,
      started_at timestamptz not null default now(),
      completed_at timestamptz
    );
    create index if not exists idx_training_runs_org_created on training_runs(org_id, started_at desc);
    create index if not exists idx_training_runs_agent_created on training_runs(agent_code, started_at desc);

    -- Academy Week-1 foundation tables (per academy plan)
    create table if not exists training_sessions (
      id uuid primary key default gen_random_uuid(),
      agent_code text not null references agent_catalog(code) on delete restrict,
      session_type text not null,
      started_at timestamptz not null default now(),
      completed_at timestamptz,
      total_interactions integer not null default 0,
      avg_quality_score double precision,
      system_prompt_version integer,
      improvement_notes text,
      status text not null default 'in_progress',
      error_message text
    );
    create index if not exists idx_training_sessions_agent on training_sessions(agent_code);
    create index if not exists idx_training_sessions_status on training_sessions(status);

    create table if not exists agent_performance_metrics (
      id uuid primary key default gen_random_uuid(),
      agent_code text not null references agent_catalog(code) on delete restrict,
      metric_date date not null default current_date,
      total_interactions integer not null default 0,
      positive_ratings integer not null default 0,
      negative_ratings integer not null default 0,
      neutral_ratings integer not null default 0,
      avg_latency_ms integer,
      avg_quality_score double precision,
      avg_response_length integer,
      successful_resolutions integer not null default 0,
      escalations integer not null default 0,
      most_common_topics text[],
      unique(agent_code, metric_date)
    );
    create index if not exists idx_performance_agent_date on agent_performance_metrics(agent_code, metric_date desc);

    create table if not exists system_prompt_versions (
      id serial primary key,
      agent_code text not null references agent_catalog(code) on delete restrict,
      version integer not null,
      system_prompt text not null,
      created_at timestamptz not null default now(),
      created_by text not null default 'academy_auto',
      performance_notes text,
      is_active boolean not null default false,
      test_quality_score double precision,
      improvement_areas text[],
      unique(agent_code, version)
    );
    create index if not exists idx_prompt_versions_active on system_prompt_versions(agent_code, is_active);

    create table if not exists test_scenarios (
      id uuid primary key default gen_random_uuid(),
      agent_code text not null references agent_catalog(code) on delete restrict,
      scenario_type text not null,
      difficulty text not null default 'medium',
      user_message text not null,
      expected_qualities text[],
      created_at timestamptz not null default now(),
      is_active boolean not null default true
    );
    create index if not exists idx_scenarios_agent on test_scenarios(agent_code, is_active);

    create table if not exists evaluation_results (
      id uuid primary key default gen_random_uuid(),
      training_session_id uuid references training_sessions(id) on delete cascade,
      scenario_id uuid references test_scenarios(id) on delete set null,
      agent_code text not null references agent_catalog(code) on delete restrict,
      system_prompt_version integer,
      user_message text not null,
      agent_response text not null,
      quality_score double precision not null,
      subscores jsonb,
      evaluator_notes text,
      evaluated_at timestamptz not null default now()
    );
    create index if not exists idx_evaluation_session on evaluation_results(training_session_id);
    create index if not exists idx_evaluation_agent on evaluation_results(agent_code, evaluated_at desc);

    -- Workflow templates + recurring schedules (cron-ready model)
    create table if not exists workflow_templates (
      template_id uuid primary key default gen_random_uuid(),
      org_id text not null references organizations(org_id) on delete cascade,
      name text not null,
      description text not null default '',
      context jsonb not null default '{}'::jsonb,
      steps jsonb not null default '[]'::jsonb,
      is_active boolean not null default true,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now(),
      unique(org_id, name)
    );
    create index if not exists idx_workflow_templates_org on workflow_templates(org_id, created_at desc);

    create table if not exists workflow_schedules (
      schedule_id uuid primary key default gen_random_uuid(),
      org_id text not null references organizations(org_id) on delete cascade,
      template_id uuid not null references workflow_templates(template_id) on delete cascade,
      name text not null,
      cron_expression text not null,
      initial_message text not null default '',
      timezone text not null default 'UTC',
      is_active boolean not null default true,
      last_run_at timestamptz,
      next_run_at timestamptz,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    );
    alter table if exists workflow_schedules add column if not exists initial_message text not null default '';
    create index if not exists idx_workflow_schedules_org on workflow_schedules(org_id, is_active, next_run_at);
    create index if not exists idx_workflow_schedules_template on workflow_schedules(template_id);

    create table if not exists workflow_runs (
      run_id uuid primary key default gen_random_uuid(),
      workflow_id text not null,
      org_id text not null references organizations(org_id) on delete cascade,
      template_id uuid references workflow_templates(template_id) on delete set null,
      schedule_id uuid references workflow_schedules(schedule_id) on delete set null,
      session_id text not null,
      status text not null default 'completed',
      initial_message text not null default '',
      final_response text not null default '',
      steps_count integer not null default 0,
      started_at timestamptz not null default now(),
      completed_at timestamptz,
      error_message text
    );
    create index if not exists idx_workflow_runs_org on workflow_runs(org_id, started_at desc);
    create index if not exists idx_workflow_runs_template on workflow_runs(template_id, started_at desc);

    -- Internal knowledge base for document retrieval
    create table if not exists knowledge_base (
      id uuid primary key default gen_random_uuid(),
      title varchar(500) not null,
      content text not null,
      category varchar(100),
      tags text[],
      source_url varchar(1000),
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now(),
      created_by varchar(100) not null default 'system',
      is_active boolean not null default true
    );
    create index if not exists idx_knowledge_base_content_fts
      on knowledge_base using gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')));
    create index if not exists idx_knowledge_base_category on knowledge_base(category);
    create index if not exists idx_knowledge_base_active on knowledge_base(is_active);

    -- Session management at scale
    create table if not exists chat_sessions (
      session_id text primary key,
      org_id text not null references organizations(org_id) on delete cascade,
      agent_code text not null references agent_catalog(code) on delete restrict,
      title text not null default '',
      status text not null default 'active',
      turns_count integer not null default 0,
      compacted_turns integer not null default 0,
      summary text not null default '',
      metadata jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now(),
      last_activity_at timestamptz not null default now()
    );
    create index if not exists idx_chat_sessions_org on chat_sessions(org_id, updated_at desc);
    create index if not exists idx_chat_sessions_org_status on chat_sessions(org_id, status, updated_at desc);

    create table if not exists chat_session_messages (
      id uuid primary key default gen_random_uuid(),
      session_id text not null references chat_sessions(session_id) on delete cascade,
      role text not null,
      content text not null default '',
      metadata jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now()
    );
    create index if not exists idx_session_messages_session on chat_session_messages(session_id, created_at asc);

    -- Tool permissions (org + optional agent override)
    create table if not exists org_tool_policies (
      id uuid primary key default gen_random_uuid(),
      org_id text not null references organizations(org_id) on delete cascade,
      agent_code text,
      tool_name text not null,
      allow boolean not null default true,
      config jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    );
    create unique index if not exists uq_org_tool_policy
      on org_tool_policies(org_id, coalesce(agent_code, ''), tool_name);
    create index if not exists idx_org_tool_policy_org on org_tool_policies(org_id);

    -- Runtime hooks + telemetry/audit
    create table if not exists runtime_events (
      id uuid primary key default gen_random_uuid(),
      org_id text,
      session_id text,
      agent_code text,
      event_type text not null,
      payload jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now()
    );
    create index if not exists idx_runtime_events_org on runtime_events(org_id, created_at desc);
    create index if not exists idx_runtime_events_session on runtime_events(session_id, created_at desc);

    -- BYOK/org model routing preferences
    create table if not exists org_model_policies (
      id uuid primary key default gen_random_uuid(),
      org_id text not null references organizations(org_id) on delete cascade,
      agent_code text,
      preferred_provider text,
      preferred_model text,
      reasoning_effort text,
      metadata jsonb not null default '{}'::jsonb,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    );
    create unique index if not exists uq_org_model_policy
      on org_model_policies(org_id, coalesce(agent_code, ''));
    create index if not exists idx_org_model_policy_org on org_model_policies(org_id);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
