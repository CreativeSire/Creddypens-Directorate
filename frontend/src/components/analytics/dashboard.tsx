"use client";

import { useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";
import { Skeleton } from "@/components/ui/skeleton";

type Overview = {
  days: number;
  total_interactions: number;
  active_agents: number;
  avg_latency_ms: number;
  avg_quality_score: number;
  total_tokens: number;
  total_tasks: number;
  completed_tasks: number;
  task_completion_rate: number;
};

type CostDepartment = {
  department: string;
  interactions: number;
  tokens_used: number;
  estimated_cost_usd: number;
};

type Costs = {
  days: number;
  total_estimated_cost_usd: number;
  departments: CostDepartment[];
};

type ActivityPoint = {
  day: string;
  interactions: number;
  avg_latency_ms: number;
  avg_quality_score: number;
  tokens_used: number;
  tasks_created: number;
  tasks_completed: number;
};

type Activity = {
  days: number;
  series: ActivityPoint[];
};

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 rounded p-4">
      <div className="text-xs tracking-widest text-[#00F0FF]/60 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  );
}

export default function AnalyticsDashboard() {
  const [days, setDays] = useState<number>(30);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [costs, setCosts] = useState<Costs | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    async function run() {
      setLoading(true);
      setError("");
      const orgId = getOrgId();
      if (!orgId) {
        setLoading(false);
        setError("No organization selected.");
        return;
      }

      try {
        const base = apiBaseUrl();
        const [overviewRes, costsRes, activityRes] = await Promise.all([
          fetch(`${base}/v1/organizations/${encodeURIComponent(orgId)}/analytics/overview?days=${days}`, { cache: "no-store" }),
          fetch(`${base}/v1/organizations/${encodeURIComponent(orgId)}/analytics/costs?days=${days}`, { cache: "no-store" }),
          fetch(`${base}/v1/organizations/${encodeURIComponent(orgId)}/analytics/activity?days=${days}`, { cache: "no-store" }),
        ]);
        if (!overviewRes.ok || !costsRes.ok || !activityRes.ok) {
          throw new Error(`Failed to load analytics (${overviewRes.status}/${costsRes.status}/${activityRes.status})`);
        }
        const [overviewData, costsData, activityData] = await Promise.all([
          overviewRes.json(),
          costsRes.json(),
          activityRes.json(),
        ]);
        if (!mounted) return;
        setOverview(overviewData);
        setCosts(costsData);
        setActivity(activityData);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    void run();
    return () => {
      mounted = false;
    };
  }, [days]);

  const peakDay = useMemo(() => {
    if (!activity?.series?.length) return null;
    return [...activity.series].sort((a, b) => b.interactions - a.interactions)[0];
  }, [activity]);

  if (loading) {
    return <Skeleton className="h-[520px] border border-cyan/30" />;
  }

  if (error) {
    return <div className="text-sm text-red-300 border border-red-400/30 bg-red-500/5 rounded p-4">{error}</div>;
  }

  if (!overview || !costs || !activity) {
    return <div className="text-[#00F0FF]/60 text-sm">No analytics available.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-white">Analytics</h1>
          <p className="text-sm text-white/60 mt-1">Usage, costs, and activity trends for your organization.</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="bg-[#0D1520] border border-[#00F0FF]/30 text-[#00F0FF] px-3 py-2 rounded focus-ring"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="INTERACTIONS" value={overview.total_interactions.toLocaleString()} />
        <MetricCard label="ACTIVE AGENTS" value={overview.active_agents.toLocaleString()} />
        <MetricCard label="AVG LATENCY" value={`${(overview.avg_latency_ms / 1000).toFixed(2)}s`} />
        <MetricCard label="AVG QUALITY" value={overview.avg_quality_score.toFixed(2)} />
        <MetricCard label="TOKENS" value={overview.total_tokens.toLocaleString()} />
        <MetricCard label="TASKS" value={overview.total_tasks.toLocaleString()} />
        <MetricCard label="TASKS DONE" value={overview.completed_tasks.toLocaleString()} />
        <MetricCard label="TASK COMPLETION" value={`${overview.task_completion_rate.toFixed(1)}%`} />
      </div>

      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 rounded p-5">
        <div className="text-xs tracking-widest text-[#00F0FF] mb-4">COST BY DEPARTMENT</div>
        <div className="space-y-3">
          {costs.departments.length === 0 ? (
            <div className="text-white/60 text-sm">No department cost data yet.</div>
          ) : (
            costs.departments.map((item) => (
              <div key={item.department} className="flex items-center justify-between gap-3">
                <div className="text-white text-sm">{item.department}</div>
                <div className="text-right">
                  <div className="text-[#FFB800] font-semibold">${Number(item.estimated_cost_usd || 0).toFixed(4)}</div>
                  <div className="text-xs text-white/60">{item.interactions} interactions</div>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="mt-4 pt-3 border-t border-[#00F0FF]/20 flex items-center justify-between text-sm">
          <span className="text-white/70">Total estimated cost</span>
          <span className="text-[#FFB800] font-semibold">${Number(costs.total_estimated_cost_usd || 0).toFixed(4)}</span>
        </div>
      </div>

      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 rounded p-5">
        <div className="text-xs tracking-widest text-[#00F0FF] mb-4">ACTIVITY TREND</div>
        {activity.series.length === 0 ? (
          <div className="text-white/60 text-sm">No activity trend data yet.</div>
        ) : (
          <div className="space-y-2">
            {activity.series.slice(-14).map((row) => (
              <div key={row.day} className="flex items-center justify-between text-sm">
                <span className="text-white/80">{new Date(row.day).toLocaleDateString()}</span>
                <span className="text-[#00F0FF]">{row.interactions} interactions</span>
                <span className="text-white/60">{(row.avg_latency_ms / 1000).toFixed(2)}s avg</span>
                <span className="text-[#00FF88]">{row.avg_quality_score.toFixed(2)} quality</span>
              </div>
            ))}
          </div>
        )}
        {peakDay ? (
          <div className="mt-4 pt-3 border-t border-[#00F0FF]/20 text-xs text-white/70">
            Peak day: {new Date(peakDay.day).toLocaleDateString()} ({peakDay.interactions} interactions)
          </div>
        ) : null}
      </div>
    </div>
  );
}
