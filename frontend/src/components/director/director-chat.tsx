"use client";

import { useState } from "react";
import Link from "next/link";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";

type Rec = {
  agent_code: string;
  role: string;
  reasoning: string;
  price_monthly: number;
  department: string;
};

type DirectorResponse = {
  message: string;
  recommendations: Rec[];
};

function formatPrice(cents: number) {
  return `$${Math.floor(cents / 100)}/mo`;
}

export default function DirectorChat() {
  const [messages, setMessages] = useState<Array<{ from: "user" | "director"; text: string }>>([
    {
      from: "director",
      text: "Ask me anything. Describe what you need and I’ll recommend the right asset.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recs, setRecs] = useState<Rec[]>([]);

  async function send() {
    const trimmed = input.trim();
    if (!trimmed) return;

    setMessages((m) => [...m, { from: "user", text: trimmed }]);
    setInput("");
    setLoading(true);
    setRecs([]);

    try {
      const orgId = getOrgId() || "org_test";
      const res = await fetch(`${apiBaseUrl()}/v1/director/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, org_id: orgId }),
      });
      if (!res.ok) throw new Error(`Director failed: ${res.status}`);
      const data = (await res.json()) as DirectorResponse;
      setMessages((m) => [...m, { from: "director", text: data.message }]);
      setRecs(data.recommendations || []);
    } catch {
      setMessages((m) => [
        ...m,
        {
          from: "director",
          text: "I hit an error reaching central intelligence. Try again in a moment.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border border-[#00F0FF]/30 bg-gradient-to-br from-[#00F0FF]/5 to-transparent backdrop-blur-sm overflow-hidden">
      <div className="border-b border-[#00F0FF]/30 p-4 bg-[#00F0FF]/5">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">THE DIRECTOR // CENTRAL INTELLIGENCE</div>
        <div className="text-sm text-[#00F0FF]/70 mt-1">
          Ask me anything. I&apos;ll recommend the right agent for your needs.
        </div>
      </div>

      <div className="p-4 h-[520px] overflow-y-auto space-y-3">
        {messages.map((m, idx) => (
          <div key={idx} className={m.from === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={
                m.from === "user"
                  ? "max-w-[80%] border border-[#00F0FF]/30 bg-[#00F0FF]/10 p-3 text-sm text-white"
                  : "max-w-[80%] border border-[#FFB800]/30 bg-[#FFB800]/10 p-3 text-sm text-white"
              }
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading ? (
          <div className="flex justify-start">
            <div className="max-w-[80%] border border-[#FFB800]/30 bg-[#FFB800]/10 p-3 text-sm text-white">
              Processing…
            </div>
          </div>
        ) : null}

        {recs.length ? (
          <div className="border border-[#00F0FF]/20 bg-[#0D1520]/60 p-4">
            <div className="text-xs text-[#00F0FF]/60 tracking-[0.25em] mb-3">
              {"// RECOMMENDED ASSETS"}
            </div>
            <div className="space-y-3">
              {recs.map((r) => (
                <div key={r.agent_code} className="border border-[#00F0FF]/20 p-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-white font-bold">{r.agent_code}</div>
                      <div className="text-sm text-[#00F0FF]/70">{r.role}</div>
                      <div className="text-xs text-[#00F0FF]/50">{r.department}</div>
                    </div>
                    <div className="text-[#FFB800] font-bold">{formatPrice(r.price_monthly)}</div>
                  </div>
                  <div className="text-sm text-white/80 mt-2">{r.reasoning}</div>
                  <div className="flex gap-3 mt-3">
                    <Link
                      href={`/agents/${encodeURIComponent(r.agent_code)}`}
                      className="px-4 py-2 border border-[#00F0FF]/30 hover:bg-[#00F0FF]/10 text-sm"
                    >
                      View Dossier
                    </Link>
                    <Link
                      href={`/agents/${encodeURIComponent(r.agent_code)}`}
                      className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] font-bold text-sm hover:bg-[#FFB800]/90"
                    >
                      Hire Now
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="border-t border-[#00F0FF]/30 p-4 flex gap-3">
        <input
          className="flex-1 h-11 px-4 bg-transparent border border-[#00F0FF]/30 text-white placeholder-[#00F0FF]/40 focus:outline-none"
          placeholder="Describe what you need…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
        />
        <button
          className="px-5 h-11 bg-[#00F0FF]/10 border border-[#00F0FF]/50 hover:bg-[#00F0FF]/20 font-bold tracking-wider"
          onClick={send}
          disabled={loading}
        >
          SEND
        </button>
      </div>
    </div>
  );
}
