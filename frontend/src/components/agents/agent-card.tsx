"use client";

import Link from "next/link";

import type { Agent } from "@/lib/types";
import { motion } from "framer-motion";

function formatPrice(cents: number) {
  const dollars = Math.floor((cents || 0) / 100);
  return `$${dollars}/mo`;
}

export function AgentCard({ agent }: { agent: Agent }) {
  const active = agent.status === "active";
  const displayName = agent.human_name || agent.code;
  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ duration: 0.2 }}
      className="border border-[#00F0FF]/30 bg-[#0D1520] p-5 hover:border-[#FFB800]/60 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs text-[#00F0FF] tracking-[0.25em]">
            {"// "} {agent.department.toUpperCase()}
          </div>
          <div className="text-2xl font-bold text-white tracking-wide mt-2">{displayName}</div>
          <div className="text-sm text-[#00F0FF]/70 mt-1">
            {agent.code} • {agent.role}
          </div>
        </div>
        <div
          className={`text-xs px-2 py-1 border tracking-[0.25em] ${
            active
              ? "border-[#00FF00]/40 text-[#00FF00]"
              : "border-[#00F0FF]/20 text-[#00F0FF]/60"
          }`}
        >
          {active ? "ACTIVE" : "COMING SOON"}
        </div>
      </div>

      <div className="text-sm text-white/80 mt-4 min-h-[48px]">{agent.tagline || agent.description}</div>

      <div className="mt-5 flex items-center justify-between gap-4">
        {active ? (
          <div className="text-[#FFB800] font-bold">{formatPrice(agent.price_cents)}</div>
        ) : (
          <div className="text-[#00F0FF]/40 text-sm">CLEARANCE PENDING</div>
        )}

        {active ? (
          <Link
            href={`/dashboard/agents/${encodeURIComponent(agent.code)}`}
            className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] font-bold hover:bg-[#FFB800]/90"
          >
            VIEW DOSSIER
          </Link>
        ) : (
          <div className="px-4 py-2 border border-[#00F0FF]/20 text-[#00F0FF]/50 text-xs tracking-[0.25em]">
            RESTRICTED
          </div>
        )}
      </div>
    </motion.div>
  );
}
