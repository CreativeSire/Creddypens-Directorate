"use client";

import { useEffect, useState } from "react";

import Link from "next/link";
import CountUp from "react-countup";
import { AnimatePresence, motion } from "framer-motion";
import { Activity } from "lucide-react";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";
import { StatsSkeleton } from "@/components/skeletons/stats-skeleton";
import { EmptyState } from "@/components/ui/empty-state";

type StatCardProps = {
  label: string;
  value: string | number;
  color: "cyan" | "green" | "amber";
};

function StatCard({ label, value, color }: StatCardProps) {
  const isNumber = typeof value === "number";
  const colorClass =
    color === "cyan"
      ? "text-[#00F0FF]"
      : color === "green"
        ? "text-[#00FF00]"
        : "text-[#FFB800]";
  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-4 hover:border-[#00F0FF]/50 transition-all"
    >
      <div className="text-xs text-[#00F0FF]/60 tracking-[0.25em]">{label}</div>
      <div className={`text-3xl font-bold mt-2 ${colorClass}`}>
        {isNumber ? <CountUp end={value} duration={1.5} /> : value}
      </div>
    </motion.div>
  );
}

type DashboardStats = {
  hired_agents_count: number;
  active_agents_count: number;
  tasks_this_week: number;
  avg_response_time_ms: number;
  avg_quality_score?: number;
  recent_activities: Array<{
    agent_code: string;
    agent_name: string;
    task_summary: string;
    timestamp: string;
    latency_ms: number;
  }>;
};

export default function StatsPanel() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgId, setOrgIdState] = useState<string | null>(null);

  useEffect(() => {
    setOrgIdState(getOrgId());
  }, []);

  useEffect(() => {
    if (!orgId) {
      setLoading(false);
      return;
    }

    let canceled = false;

    const fetchStats = async () => {
      try {
        const res = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/dashboard-stats`, {
          headers: { "X-Org-Id": orgId },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as DashboardStats;
        if (!canceled) setStats(data);
      } catch (err) {
        console.error("Failed to fetch stats:", err);
        if (!canceled) setStats(null);
      } finally {
        if (!canceled) setLoading(false);
      }
    };

    fetchStats();
    const interval = window.setInterval(fetchStats, 30_000);
    return () => {
      canceled = true;
      window.clearInterval(interval);
    };
  }, [orgId]);

  if (!orgId) {
    return (
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-4 text-sm text-[#00F0FF]/60">
        Sign in to view organization stats.
      </div>
    );
  }

  if (loading) {
    return <StatsSkeleton />;
  }

  if (!stats) {
    return <div className="text-[#00F0FF]/60 text-sm">No stats available.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="AGENTS HIRED" value={stats.hired_agents_count} color="cyan" />
        <StatCard label="ACTIVE NOW" value={stats.active_agents_count} color="green" />
        <StatCard label="TASKS THIS WEEK" value={stats.tasks_this_week} color="amber" />
        <StatCard label="AVG RESPONSE" value={`${(stats.avg_response_time_ms / 1000).toFixed(1)}s`} color="cyan" />
        <StatCard label="AVG QUALITY" value={(stats.avg_quality_score ?? 0).toFixed(2)} color="green" />
      </div>

      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-4">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-3">
          {"// RECENT ACTIVITY"}
        </div>

        {stats.recent_activities.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No Recent Activity"
            description="Your agent interactions will appear here. Start chatting with deployed agents to populate the feed."
          />
        ) : (
          <div className="space-y-2 max-h-[420px] overflow-y-auto">
            <AnimatePresence mode="popLayout" initial={false}>
              {stats.recent_activities.map((a) => (
                <motion.div
                  key={`${a.agent_code}-${a.timestamp}-${a.latency_ms}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="border-b border-[#00F0FF]/20 py-2 last:border-0"
                >
                  <div className="text-xs text-white">
                    {a.agent_code} <span className="text-[#00F0FF]/60">— {a.agent_name}</span>
                  </div>
                  <div className="text-xs text-[#00F0FF]/60 mt-1">{a.task_summary}</div>
                  <div className="text-xs text-[#00F0FF]/40 mt-1">
                    {new Date(a.timestamp).toLocaleString()} • {a.latency_ms}ms
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}

        <Link
          href="/dashboard/departments/customer-experience"
          className="mt-4 block text-center px-4 py-3 bg-[#FFB800] text-[#0A0F14] font-bold hover:bg-[#FFB800]/90"
        >
          BROWSE MARKETPLACE
        </Link>
      </div>
    </div>
  );
}
