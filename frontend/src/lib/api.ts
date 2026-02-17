import { apiBaseUrl } from "@/lib/env";
import type { Agent, AgentDetail, ExecuteRequest, ExecuteResponse } from "@/lib/types";

export async function fetchAgents(): Promise<Agent[]> {
  const res = await fetch(`${apiBaseUrl()}/v1/agents`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load agents: ${res.status}`);
  return res.json();
}

export async function fetchAgent(code: string): Promise<AgentDetail> {
  const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(code)}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load agent: ${res.status}`);
  return res.json();
}

export async function executeAgent(opts: {
  code: string;
  orgId: string;
  payload: ExecuteRequest;
}): Promise<ExecuteResponse> {
  const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(opts.code)}/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Org-Id": opts.orgId,
    },
    body: JSON.stringify(opts.payload),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Execute failed (${res.status}): ${txt}`);
  }
  return res.json();
}

export async function hireAgent(opts: { code: string; orgId: string }): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(opts.code)}/hire`, {
    method: "POST",
    headers: {
      "X-Org-Id": opts.orgId,
    },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Hire failed (${res.status}): ${txt}`);
  }
}

export async function fetchOrgAgents(orgId: string): Promise<{
  org_id: string;
  agents: Array<{
    agent_code: string;
    hire_status: string;
    configuration: Record<string, unknown>;
    role: string;
    department: string;
    price_cents: number;
  }>;
}> {
  const res = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/agents`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load org agents: ${res.status}`);
  return res.json();
}

