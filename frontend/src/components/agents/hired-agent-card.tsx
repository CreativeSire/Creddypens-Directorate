"use client";

import { useRouter } from "next/navigation";

type HiredAgentCardProps = {
  agent: {
    agent_code: string;
    name: string;
    role: string;
    department: string;
    llm_model: string | null;
  };
  stats: {
    tasks_today: number;
    avg_latency_ms: number;
    quality_score: number;
  };
  status: string;
  onOpenChat: () => void;
};

export function HiredAgentCard({ agent, stats, status, onOpenChat }: HiredAgentCardProps) {
  const router = useRouter();
  const isOnline = status === "active";

  const avgSeconds = stats.avg_latency_ms > 0 ? `${(stats.avg_latency_ms / 1000).toFixed(1)}s` : "—";
  const quality = stats.quality_score > 0 ? stats.quality_score.toFixed(1) : "—";

  return (
    <div className="border border-[#00F0FF]/30 bg-gradient-to-br from-[#00F0FF]/5 to-transparent hover:border-[#FFB800]/50 transition-all duration-200 hover:-translate-y-1">
      <div className="border-b border-[#00F0FF]/30 p-4 bg-[#00F0FF]/5">
        <div className="text-xs text-[#FFB800] tracking-[0.25em] mb-1">{agent.agent_code}</div>
        <div className="text-xl text-white font-semibold">{agent.name}</div>
        <div className="text-xs text-[#00F0FF]/60 mt-1">{agent.role}</div>
      </div>

      <div className="p-4 border-b border-[#00F0FF]/30">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isOnline ? "bg-[#00FF00] animate-pulse" : "bg-[#00F0FF]/30"}`} />
          <span className={`text-xs tracking-[0.25em] ${isOnline ? "text-[#00FF00]" : "text-[#00F0FF]/50"}`}>
            {isOnline ? "ONLINE — ACTIVE" : "OFFLINE"}
          </span>
        </div>
        <div className="text-xs text-[#00F0FF]/40 mt-2">
          {agent.department}
          {agent.llm_model ? ` • ${agent.llm_model}` : ""}
        </div>
      </div>

      <div className="p-4 space-y-2">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-3">{"// TODAY'S PERFORMANCE"}</div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#00F0FF]/60">Tasks Completed</span>
          <span className="font-mono text-sm text-[#00F0FF]">{stats.tasks_today}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#00F0FF]/60">Avg Response</span>
          <span className="font-mono text-sm text-[#00F0FF]">{avgSeconds}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-xs text-[#00F0FF]/60">Quality Score</span>
          <span className="font-mono text-sm text-[#00F0FF]">{quality}</span>
        </div>
      </div>

      <div className="p-4 pt-0 flex gap-2">
        <button
          onClick={onOpenChat}
          className="flex-1 bg-[#FFB800] hover:bg-[#FFB800]/90 text-[#0A0F14] py-2 px-4 text-xs font-bold tracking-[0.25em] transition-all"
        >
          OPEN CHAT
        </button>
        <button
          onClick={() => router.push(`/agents/${encodeURIComponent(agent.agent_code)}`)}
          className="px-4 py-2 border border-[#00F0FF]/30 text-[#00F0FF] text-xs tracking-[0.25em] hover:bg-[#00F0FF]/10 transition-all"
        >
          DETAILS
        </button>
      </div>
    </div>
  );
}

