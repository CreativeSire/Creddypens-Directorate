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
  const isMock = reply?.startsWith("[MOCK:") ?? false;

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
      setMeta({ model_used: res.model_used, latency_ms: res.latency_ms });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border p-4 space-y-3">
      <div className="text-sm font-semibold">Live Demo</div>
      <textarea
        className="w-full min-h-24 rounded-md border bg-background p-3 text-sm"
        placeholder="Send a test message..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
      />
      <div className="flex items-center justify-end">
        <Button size="sm" onClick={onSend} disabled={busy || !message.trim()}>
          {busy ? "Executing..." : "Execute"}
        </Button>
      </div>
      {error ? <div className="text-sm text-red-600">{error}</div> : null}
      {reply ? (
        <div className="rounded-md bg-secondary p-3 text-sm whitespace-pre-wrap space-y-2">
          {isMock ? (
            <div className="text-xs text-amber-600 font-semibold">Mock mode enabled (LLM_MOCK=1)</div>
          ) : null}
          <div>{reply}</div>
          {meta ? (
            <div className="text-xs text-muted-foreground">
              {meta.model_used} — {meta.latency_ms}ms — DEMO SESSION
            </div>
          ) : null}
        </div>
      ) : (
        <div className="text-xs text-muted-foreground">Send a message to test the live execution endpoint.</div>
      )}
    </div>
  );
}
