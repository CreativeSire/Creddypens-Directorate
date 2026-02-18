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
  tokens_used?: number;
  trace_id: string;
  session_id: string;
};
