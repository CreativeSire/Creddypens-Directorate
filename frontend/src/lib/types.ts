export type Agent = {
  agent_id: string;
  code: string;
  role: string;
  description: string;
  department: string;
  price_cents: number;
  status: string;
  llm_provider?: string | null;
  llm_model?: string | null;
  llm_route?: string | null;
};

export type AgentDetail = Agent & {
  llm_profile: Record<string, unknown>;
  system_prompt: string;
};

export type ExecuteRequest = {
  message: string;
  context: {
    company_name?: string;
    tone?: string;
    additional?: Record<string, unknown>;
  };
  session_id: string;
};

export type ExecuteResponse = {
  agent_code: string;
  response: string;
  model_used: string;
  latency_ms: number;
  trace_id: string;
  session_id: string;
};

