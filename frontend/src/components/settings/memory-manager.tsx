"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/env";

type MemoryItem = {
  memory_id: string;
  org_id: string;
  agent_code?: string | null;
  memory_type: string;
  memory_key: string;
  memory_value: string;
  confidence: number;
  source: string;
  access_count: number;
  is_active: boolean;
};

type Props = {
  orgId: string;
};

const MEMORY_TYPES = ["preference", "org_fact", "instruction", "context"] as const;

export function MemoryManager({ orgId }: Props) {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [form, setForm] = useState({
    memory_type: "preference",
    memory_key: "",
    memory_value: "",
    agent_code: "",
    confidence: 0.8,
  });

  const baseUrl = useMemo(() => apiBaseUrl(), []);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${baseUrl}/v1/organizations/${encodeURIComponent(orgId)}/memories`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as MemoryItem[];
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memories");
    } finally {
      setLoading(false);
    }
  }, [baseUrl, orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  const createMemory = async () => {
    if (!form.memory_key.trim() || !form.memory_value.trim()) return;
    try {
      setSaving(true);
      setError(null);
      const res = await fetch(`${baseUrl}/v1/organizations/${encodeURIComponent(orgId)}/memories`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          agent_code: form.agent_code.trim() || null,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm((prev) => ({ ...prev, memory_key: "", memory_value: "" }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save memory");
    } finally {
      setSaving(false);
    }
  };

  const deleteMemory = async (memoryId: string) => {
    try {
      const res = await fetch(`${baseUrl}/v1/memories/${encodeURIComponent(memoryId)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete memory");
    }
  };

  const extractFromSession = async () => {
    if (!sessionId.trim()) return;
    try {
      setExtracting(true);
      setError(null);
      const res = await fetch(`${baseUrl}/v1/organizations/${encodeURIComponent(orgId)}/memories/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId.trim() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to auto-extract memory");
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5 space-y-4">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">MEMORY MANAGER</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <select
            value={form.memory_type}
            onChange={(e) => setForm((prev) => ({ ...prev, memory_type: e.target.value }))}
            className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          >
            {MEMORY_TYPES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <input
            value={form.agent_code}
            onChange={(e) => setForm((prev) => ({ ...prev, agent_code: e.target.value }))}
            placeholder="Agent code (optional)"
            className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
          <input
            value={form.memory_key}
            onChange={(e) => setForm((prev) => ({ ...prev, memory_key: e.target.value }))}
            placeholder="Memory key (example: tone)"
            className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
          <input
            value={String(form.confidence)}
            onChange={(e) => setForm((prev) => ({ ...prev, confidence: Number(e.target.value) || 0.8 }))}
            placeholder="Confidence 0-1"
            className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
        </div>
        <textarea
          value={form.memory_value}
          onChange={(e) => setForm((prev) => ({ ...prev, memory_value: e.target.value }))}
          placeholder="Memory value"
          rows={3}
          className="w-full bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
        />
        <button
          disabled={saving}
          onClick={() => void createMemory()}
          className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] text-xs font-bold tracking-[0.2em] disabled:opacity-50"
        >
          {saving ? "SAVING..." : "ADD MEMORY"}
        </button>
      </div>

      <div className="border border-[#00F0FF]/20 bg-[#0D1520]/60 p-5 space-y-3">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em]">AUTO-EXTRACT FROM SESSION</div>
        <div className="flex gap-2">
          <input
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="Session ID"
            className="flex-1 bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
          <button
            onClick={() => void extractFromSession()}
            disabled={extracting}
            className="px-4 py-2 border border-[#00F0FF]/40 text-[#00F0FF] text-xs tracking-[0.2em] disabled:opacity-50"
          >
            {extracting ? "EXTRACTING..." : "EXTRACT"}
          </button>
        </div>
      </div>

      {error ? <div className="text-sm text-red-400">{error}</div> : null}

      <div className="border border-[#00F0FF]/20 bg-[#00F0FF]/5 p-5">
        <div className="text-xs text-[#00F0FF]/70 tracking-[0.25em] mb-3">STORED MEMORIES</div>
        {loading ? (
          <div className="text-sm text-[#00F0FF]/60">Loading memories...</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-[#00F0FF]/60">No memories yet.</div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.memory_id} className="border border-[#00F0FF]/20 bg-[#0A0F14]/70 p-3">
                <div className="flex justify-between gap-3">
                  <div className="text-sm text-white">
                    <span className="text-[#FFB800]">{item.memory_type}</span> • <span>{item.memory_key}</span>
                    {item.agent_code ? <span className="text-[#00F0FF]/60"> • {item.agent_code}</span> : null}
                  </div>
                  <button
                    onClick={() => void deleteMemory(item.memory_id)}
                    className="text-xs text-red-400 border border-red-400/40 px-2 py-1"
                  >
                    DELETE
                  </button>
                </div>
                <div className="text-sm text-[#00F0FF]/80 mt-2 whitespace-pre-wrap">{item.memory_value}</div>
                <div className="text-xs text-[#00F0FF]/50 mt-2">
                  confidence {item.confidence.toFixed(2)} • source {item.source} • accessed {item.access_count}x
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
