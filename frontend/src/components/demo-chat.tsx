"use client";

import { useState } from "react";

import { executeAgent } from "@/lib/api";
import { getOrgId } from "@/lib/org";
import { Button } from "@/components/ui/button";

export function DemoChat({ agentCode, companyName }: { agentCode: string; companyName?: string }) {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ model_used: string; latency_ms: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSend() {
    setBusy(true);
    setError(null);
    setReply(null);
    setMeta(null);
    try {
      const orgId = getOrgId() || "org_test";
      const res = await executeAgent({
        code: agentCode,
        orgId,
        payload: {
          message,
          context: { company_name: companyName || "", tone: "professional", additional: {} },
          session_id: `demo_${Date.now()}`,
        },
      });
      setReply(res.response);
      setMeta({ model_used: "", latency_ms: res.latency_ms });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5 space-y-4">
      <div className="text-xs text-[#FFB800] tracking-[0.25em]">LIVE DEMO SESSION</div>
      <textarea
        className="w-full min-h-24 border border-[#00F0FF]/30 bg-[#0A0F14]/60 p-3 text-sm text-white placeholder:text-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF]"
        placeholder="Send a test message..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
      />
      <div className="flex items-center justify-end">
        <Button size="sm" className="bg-[#FFB800] text-[#0A0F14] hover:bg-[#FFB800]/90" onClick={onSend} disabled={busy || !message.trim()}>
          {busy ? "Executing..." : "Execute"}
        </Button>
      </div>
      {error ? <div className="text-sm text-[#FF6B6B]">{error}</div> : null}
      {reply ? (
        <div className="border border-[#FFB800]/30 bg-[#FFB800]/5 p-4 text-sm whitespace-pre-wrap space-y-2">
          <div className="text-white/90">{reply}</div>
          {meta ? (
            <div className="text-xs text-[#00F0FF]/60">Response Time: {meta.latency_ms}ms</div>
          ) : null}
        </div>
      ) : (
        <div className="text-xs text-[#00F0FF]/60">Send a message to preview this agent&rsquo;s response quality.</div>
      )}
    </div>
  );
}
