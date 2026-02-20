export type Agent = {
  agent_id: string;
  code: string;
  role: string;
  human_name?: string | null;
  tagline?: string | null;
  description: string;
  capabilities?: string[];
  ideal_for?: string | null;
  personality?: string | null;
  communication_style?: string | null;
  department: string;
  price_cents: number;
  status: string;
};

export type AgentDetail = Agent & {
  profile: string;
  operational_sections: Array<{ title: string; items: string[] }>;
};

export type ExecuteRequest = {
  message: string;
  file_ids?: string[];
  context: {
    company_name?: string;
    tone?: string;
    output_format?: "text" | "markdown" | "json" | "email" | "csv" | "code" | "presentation";
    web_search?: boolean;
    doc_retrieval?: boolean;
    deep_research?: boolean;
    attachments?: Array<{
      name: string;
      mime_type?: string;
      content_excerpt?: string;
      size_bytes?: number;
    }>;
    additional?: Record<string, unknown>;
  };
  session_id: string;
};

export type SuggestedAgent = {
  code: string;
  name: string;
  tagline?: string | null;
  department?: string | null;
  reason: string;
  is_hired: boolean;
  handoff_context: string;
};

export type ExecuteResponse = {
  agent_code: string;
  response: string;
  model_used: string;
  search_used?: boolean;
  docs_used?: boolean;
  latency_ms: number;
  tokens_used?: number;
  interaction_id?: string | null;
  trace_id: string;
  session_id: string;
  referral_triggered?: boolean;
  suggested_agent?: SuggestedAgent | null;
};

export type WorkflowStepRequest = {
  id?: string | null;
  agent_code: string;
  message?: string | null;
  use_previous_response?: boolean;
  conditions?: Record<string, string>;
  next?: string | null;
  set_var?: string | null;
  action?: string | null;
  integration_id?: string | null;
  action_config?: Record<string, unknown>;
};

export type WorkflowExecuteRequest = {
  initial_message: string;
  session_id?: string | null;
  context: ExecuteRequest["context"];
  steps: WorkflowStepRequest[];
  workflow_definition?: Record<string, unknown>;
};

export type WorkflowStepResponse = {
  step_index: number;
  step_id?: string | null;
  agent_code: string;
  input_message: string;
  response: string;
  model_used: string;
  latency_ms: number;
  trace_id: string;
};

export type WorkflowExecuteResponse = {
  workflow_id: string;
  session_id: string;
  final_response: string;
  steps: WorkflowStepResponse[];
};

export type WorkflowTemplateStep = WorkflowStepRequest;

export type WorkflowTemplate = {
  template_id: string;
  name: string;
  description: string;
  context: ExecuteRequest["context"];
  steps: WorkflowTemplateStep[];
  workflow_definition?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkflowSchedule = {
  schedule_id: string;
  template_id: string;
  template_name: string;
  name: string;
  cron_expression: string;
  timezone: string;
  initial_message: string;
  is_active: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
  created_at: string;
  updated_at: string;
};
