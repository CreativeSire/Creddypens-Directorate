"use client";

import { useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";
import { toast } from "@/lib/toast";
import { Skeleton } from "@/components/ui/skeleton";

type AcademyStatus = {
  agents_in_training: number;
  avg_quality_score: number;
  quality_trend: string;
  next_cycle_hours: number;
  recent_sessions: Array<{
    agent_code: string;
    trainer_id: string;
    score: number;
    passed: boolean;
    completed_at: string;
  }>;
};

export default function AcademyPage() {
  const [orgId, setOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<AcademyStatus | null>(null);
  const [trainingCode, setTrainingCode] = useState("Author-01");

  useEffect(() => {
    setOrgId(getOrgId());
  }, []);

  async function fetchStatus(currentOrg: string) {
    const res = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(currentOrg)}/academy-status`, {
      headers: { "X-Org-Id": currentOrg },
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as AcademyStatus;
  }

  useEffect(() => {
    if (!orgId) {
      setLoading(false);
      return;
    }
    let canceled = false;
    const run = async () => {
      try {
        const data = await fetchStatus(orgId);
        if (!canceled) setStatus(data);
      } catch {
        if (!canceled) toast.error("Failed to load Academy status");
      } finally {
        if (!canceled) setLoading(false);
      }
    };
    void run();
    return () => {
      canceled = true;
    };
  }, [orgId]);

  const trendUp = useMemo(() => (status?.quality_trend || "").startsWith("+"), [status?.quality_trend]);

  async function startTraining() {
    if (!orgId) return;
    const toastId = toast.loading(`Starting ${trainingCode} training run...`);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/academy/train/${encodeURIComponent(trainingCode)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
        body: JSON.stringify({ org_id: orgId, run_type: "synthetic", scenario_count: 100 }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Training completed", toastId);
      setLoading(true);
      const refreshed = await fetchStatus(orgId);
      setStatus(refreshed);
    } catch {
      toast.error("Training failed", toastId);
    } finally {
      setLoading(false);
    }
  }

  if (!orgId) {
    return (
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">{"// AUTH REQUIRED"}</div>
        <div className="text-white">Sign in to access Academy operations.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full border border-[#00F0FF]/20" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-28 w-full border border-[#00F0FF]/20" />
          <Skeleton className="h-28 w-full border border-[#00F0FF]/20" />
        </div>
        <Skeleton className="h-72 w-full border border-[#00F0FF]/20" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="border border-[#00F0FF]/30 bg-gradient-to-br from-[#00F0FF]/10 to-transparent p-8">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">THE ACADEMY // CONTINUOUS TRAINING SYSTEM</div>
        <h1 className="text-3xl text-white mt-2">Your Agents Are Getting Smarter</h1>
        <p className="text-[#00F0FF]/65 mt-2 max-w-3xl">
          Every 3 days, agents are retrained and quality-scored using real interaction patterns and synthetic scenarios.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-[#00F0FF]/30 p-6 bg-[#00F0FF]/5">
          <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">AGENTS IN TRAINING</div>
          <div className="text-4xl text-[#FFB800] font-bold">{status?.agents_in_training ?? 0}</div>
          <div className="text-xs text-[#00F0FF]/60 mt-2">Next cycle completes in {status?.next_cycle_hours ?? 0} hours</div>
        </div>
        <div className="border border-[#00F0FF]/30 p-6 bg-[#00F0FF]/5">
          <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">AVG QUALITY SCORE</div>
          <div className="text-4xl text-[#00FF00] font-bold">{(status?.avg_quality_score ?? 0).toFixed(2)}</div>
          <div className={`text-xs mt-2 ${trendUp ? "text-[#00FF00]" : "text-[#FFB800]"}`}>
            {status?.quality_trend ?? "+0.00"} from previous period
          </div>
        </div>
      </div>

      <div className="border border-[#00F0FF]/30">
        <div className="border-b border-[#00F0FF]/30 p-4 bg-[#00F0FF]/10 flex items-center justify-between gap-3">
          <div className="text-xs text-[#00F0FF] tracking-[0.25em]">{"// TRAINING OPERATIONS"}</div>
          <div className="flex items-center gap-2">
            <input
              value={trainingCode}
              onChange={(event) => setTrainingCode(event.target.value)}
              className="h-9 px-3 bg-[#0A0F14] border border-[#00F0FF]/30 text-white text-sm"
              placeholder="Agent code"
            />
            <button
              onClick={() => void startTraining()}
              className="h-9 px-4 bg-[#FFB800] text-[#0A0F14] text-xs font-bold tracking-[0.15em] hover:bg-[#FFB800]/90"
            >
              RUN TRAINING
            </button>
          </div>
        </div>
        <div className="p-4 overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead>
              <tr className="text-left text-xs text-[#00F0FF]/55">
                <th className="py-2">AGENT</th>
                <th className="py-2">TRAINER</th>
                <th className="py-2">SCORE</th>
                <th className="py-2">STATUS</th>
                <th className="py-2">COMPLETED</th>
              </tr>
            </thead>
            <tbody>
              {(status?.recent_sessions || []).map((session) => (
                <tr key={`${session.agent_code}-${session.completed_at}`} className="border-t border-[#00F0FF]/20">
                  <td className="py-3 text-white">{session.agent_code}</td>
                  <td className="py-3 text-[#00F0FF]/70">{session.trainer_id}</td>
                  <td className={`py-3 ${session.passed ? "text-[#00FF00]" : "text-[#FFB800]"}`}>
                    {session.score.toFixed(2)}
                  </td>
                  <td className="py-3 text-white/80">{session.passed ? "PASSED" : "RETRAINING"}</td>
                  <td className="py-3 text-[#00F0FF]/55">
                    {session.completed_at ? new Date(session.completed_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
