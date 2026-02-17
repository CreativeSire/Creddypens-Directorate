"use client";

import { useEffect, useState } from "react";

import { fetchOrgAgents } from "@/lib/api";
import { getOrgId } from "@/lib/org";
import { DemoChat } from "@/components/demo-chat";

function getCompanyName(cfg: Record<string, unknown>): string | undefined {
  const v = cfg["company_name"];
  return typeof v === "string" ? v : undefined;
}

export function CommandCenterClient() {
  const [orgId, setOrg] = useState<string>("—");
  const [resolvedOrgId, setResolvedOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchOrgAgents>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = getOrgId();
    setResolvedOrgId(id);
    setOrg(id || "—");
    if (!id) {
      setLoading(false);
      return;
    }
    fetchOrgAgents(id)
      .then((d) => setData(d))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Command Center</h1>
        <div className="text-sm text-muted-foreground">Org: {orgId}</div>
      </div>

      {loading ? <div className="text-sm text-muted-foreground">Loading...</div> : null}
      {error ? <div className="text-sm text-red-600">{error}</div> : null}

      {!resolvedOrgId && !loading ? (
        <div className="text-sm text-muted-foreground">
          Sign in to load your organization context.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        {data?.agents?.map((a) => (
          <div key={a.agent_code} className="rounded-xl border p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="font-semibold">{a.agent_code}</div>
              <div className="text-xs rounded-full border border-emerald-400/50 text-emerald-600 px-2 py-1">
                ACTIVE
              </div>
            </div>
            <div className="text-sm text-muted-foreground">{a.role}</div>
            <div className="text-xs text-muted-foreground">{a.department}</div>
            <div className="pt-3">
              <DemoChat agentCode={a.agent_code} companyName={getCompanyName(a.configuration) || "TestCo"} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
