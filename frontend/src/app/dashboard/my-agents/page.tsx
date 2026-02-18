"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";
import { HiredAgentCard } from "@/components/agents/hired-agent-card";
import { AgentChatModal } from "@/components/agents/agent-chat-modal";

type HiredAgent = {
  id: string;
  agent: {
    agent_code: string;
    name: string;
    role: string;
    department: string;
  };
  stats: {
    tasks_today: number;
    avg_latency_ms: number;
    quality_score: number;
  };
  status: string;
  hired_at: string;
};

function slugifyDepartment(dept: string) {
  return dept.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export default function MyAgentsPage() {
  const [hiredAgents, setHiredAgents] = useState<HiredAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [orgId, setOrgIdState] = useState<string | null>(null);

  useEffect(() => {
    setOrgIdState(getOrgId());
  }, []);

  const fetchHiredAgents = useCallback(async () => {
    if (!orgId) return;
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/agents?include_stats=1`, {
        headers: { "X-Org-Id": orgId },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as HiredAgent[];
      setHiredAgents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to fetch hired agents:", err);
      setHiredAgents([]);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (!orgId) {
      setLoading(false);
      return;
    }
    void fetchHiredAgents();
    const interval = window.setInterval(() => void fetchHiredAgents(), 60_000);
    return () => window.clearInterval(interval);
  }, [fetchHiredAgents, orgId]);

  const departments = useMemo(() => {
    return Array.from(new Set(hiredAgents.map((h) => h.agent.department))).sort((a, b) => a.localeCompare(b));
  }, [hiredAgents]);

  const filteredAgents = useMemo(() => {
    if (filter === "all") return hiredAgents;
    return hiredAgents.filter((h) => slugifyDepartment(h.agent.department) === filter);
  }, [filter, hiredAgents]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[#00F0FF]/60">Loading your agents...</div>
      </div>
    );
  }

  if (!orgId) {
    return (
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">{"// AUTH REQUIRED"}</div>
        <div className="text-white font-semibold">Sign in to view your deployed agents.</div>
        <div className="text-sm text-[#00F0FF]/60 mt-2">Missing organization context in this browser session.</div>
        <button
          className="mt-4 px-5 py-3 bg-[#FFB800] text-[#0A0F14] font-bold tracking-[0.25em] hover:bg-[#FFB800]/90"
          onClick={() => (window.location.href = "/login")}
        >
          GO TO LOGIN
        </button>
      </div>
    );
  }

  if (hiredAgents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-10">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-4">{"// NO AGENTS DEPLOYED"}</div>
        <h2 className="text-2xl text-white font-semibold mb-2 tracking-wide">Your Workforce Awaits</h2>
        <p className="text-[#00F0FF]/60 text-sm mb-6 max-w-md text-center">
          Browse the marketplace and hire your first agent to get started.
        </p>
        <button
          className="px-6 py-3 bg-[#FFB800] text-[#0A0F14] font-bold tracking-[0.25em] hover:bg-[#FFB800]/90"
          onClick={() => (window.location.href = "/dashboard/departments/customer-experience")}
        >
          BROWSE MARKETPLACE
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl text-white tracking-wide font-semibold">MY AGENTS</h1>
          <p className="text-[#00F0FF]/60 text-sm mt-1">{hiredAgents.length} deployed agents ready for work</p>
        </div>
        <button
          className="px-5 py-3 bg-[#FFB800] text-[#0A0F14] font-bold tracking-[0.25em] hover:bg-[#FFB800]/90"
          onClick={() => (window.location.href = "/dashboard/departments/customer-experience")}
        >
          + HIRE MORE AGENTS
        </button>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <button
          className={`px-4 py-2 text-xs tracking-[0.25em] border transition-all ${
            filter === "all"
              ? "bg-[#FFB800]/10 border-[#FFB800] text-[#FFB800]"
              : "border-[#00F0FF]/30 text-[#00F0FF]/60 hover:border-[#00F0FF] hover:text-[#00F0FF]"
          }`}
          onClick={() => setFilter("all")}
        >
          ALL AGENTS ({hiredAgents.length})
        </button>
        {departments.map((dept) => {
          const slug = slugifyDepartment(dept);
          const count = hiredAgents.filter((h) => h.agent.department === dept).length;
          return (
            <button
              key={dept}
              className={`px-4 py-2 text-xs tracking-[0.25em] border transition-all whitespace-nowrap ${
                filter === slug
                  ? "bg-[#FFB800]/10 border-[#FFB800] text-[#FFB800]"
                  : "border-[#00F0FF]/30 text-[#00F0FF]/60 hover:border-[#00F0FF] hover:text-[#00F0FF]"
              }`}
              onClick={() => setFilter(slug)}
            >
              {dept.toUpperCase()} ({count})
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredAgents.map((hired) => (
          <HiredAgentCard
            key={hired.id}
            agent={hired.agent}
            stats={hired.stats}
            status={hired.status}
            onOpenChat={() => setSelectedAgent(hired.agent.agent_code)}
          />
        ))}
      </div>

      {selectedAgent && (
        <AgentChatModal
          agentCode={selectedAgent}
          orgId={orgId}
          onClose={() => setSelectedAgent(null)}
          onAfterMessage={() => void fetchHiredAgents()}
        />
      )}
    </div>
  );
}
