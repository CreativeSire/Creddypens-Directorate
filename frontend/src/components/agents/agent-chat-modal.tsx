"use client";

import { useEffect, useRef, useState } from "react";

import { X, Send } from "lucide-react";

import { apiBaseUrl } from "@/lib/env";
import type { AgentDetail, ExecuteResponse } from "@/lib/types";

type Message = {
  role: "user" | "agent";
  content: string;
  timestamp: string;
  metadata?: {
    model_used?: string;
    latency_ms?: number;
  };
};

type AgentChatModalProps = {
  agentCode: string;
  orgId: string;
  onClose: () => void;
  onAfterMessage?: () => void;
};

type AgentDetailLite = Pick<AgentDetail, "code" | "role" | "department">;

function newSessionId() {
  try {
    return `chat-${crypto.randomUUID()}`;
  } catch {
    return `chat-${Date.now()}`;
  }
}

export function AgentChatModal({ agentCode, orgId, onClose, onAfterMessage }: AgentChatModalProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agent, setAgent] = useState<AgentDetailLite | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [sessionId, setSessionId] = useState<string>(() => newSessionId());
  useEffect(() => {
    setSessionId(newSessionId());
  }, [agentCode]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  useEffect(() => {
    const fetchAgent = async () => {
      const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(agentCode)}`, { cache: "no-store" });
      const data = (await res.json()) as AgentDetail;
      const detail: AgentDetailLite = {
        code: data.code,
        role: data.role,
        department: data.department,
      };
      setAgent(detail);
      setMessages([
        {
          role: "agent",
          content: `${detail.code} reporting for duty. I am ready to assist. What would you like me to work on?`,
          timestamp: new Date().toISOString(),
        },
      ]);
      setTimeout(() => textareaRef.current?.focus(), 50);
    };
    fetchAgent().catch(() => {
      setAgent({ code: agentCode, role: "Agent", department: "Directorate" });
      setMessages([
        {
          role: "agent",
          content: `${agentCode} reporting for duty. What would you like me to work on?`,
          timestamp: new Date().toISOString(),
        },
      ]);
    });
  }, [agentCode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const content = input;
    const userMsg: Message = { role: "user", content, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(agentCode)}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
        body: JSON.stringify({
          message: content,
          context: { company_name: "", tone: "", additional: {} },
          session_id: sessionId,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as ExecuteResponse;

      const agentMsg: Message = {
        role: "agent",
        content: data.response || "",
        timestamp: new Date().toISOString(),
        metadata: { model_used: data.model_used, latency_ms: data.latency_ms },
      };
      setMessages((prev) => [...prev, agentMsg]);
      onAfterMessage?.();
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content: "ERROR: Failed to process request. Please try again.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
  };

  if (!agent) {
    return (
      <div className="fixed inset-0 bg-[#0A0F14]/95 flex items-center justify-center z-50">
        <div className="text-[#00F0FF]/60">Loading agent...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-[#0A0F14] backdrop-blur-sm z-50 flex flex-col">
      <div className="h-16 border-b border-[#00F0FF]/30 flex items-center justify-between px-6 bg-[#0D1520]/60">
        <div>
          <div className="flex items-center gap-3">
            <div className="text-xs text-[#FFB800] tracking-[0.25em]">{agent.code}</div>
            <div className="w-px h-4 bg-[#00F0FF]/30" />
            <div className="text-lg text-white font-semibold">{agent.role}</div>
          </div>
          <div className="text-xs text-[#00F0FF]/50 mt-0.5">
            {agent.department}
          </div>
        </div>

        <button onClick={onClose} className="p-2 hover:bg-[#00F0FF]/10 transition-colors group" aria-label="Close">
          <X className="w-5 h-5 text-[#00F0FF]/60 group-hover:text-[#00F0FF]" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[78%] ${
                msg.role === "user"
                  ? "bg-[#00F0FF]/10 border border-[#00F0FF]/40"
                  : "bg-[#FFB800]/5 border border-[#FFB800]/20"
              } p-4`}
            >
              <div
                className={`text-sm leading-relaxed ${
                  msg.role === "user" ? "text-[#00F0FF]" : "text-white/90"
                } whitespace-pre-wrap`}
              >
                {msg.content}
              </div>

              <div className="mt-2 text-xs text-[#00F0FF]/40 font-mono">
                {msg.metadata ? `Response Time • ${msg.metadata.latency_ms ?? 0}ms` : new Date(msg.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#FFB800]/5 border border-[#FFB800]/20 p-4 flex items-center gap-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-[#FFB800] rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span
                  className="w-2 h-2 bg-[#FFB800] rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <span
                  className="w-2 h-2 bg-[#FFB800] rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
              <span className="text-xs text-[#00F0FF]/50">Processing...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-[#00F0FF]/30 p-4 bg-[#0D1520]/60">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
            placeholder="Give this agent a task..."
            className="flex-1 resize-none bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-4 py-3 text-[#00F0FF] placeholder-[#00F0FF]/30 focus:outline-none focus:border-[#00F0FF] font-mono text-sm"
            rows={2}
            disabled={loading}
          />
          <button
            onClick={() => void sendMessage()}
            disabled={loading || !input.trim()}
            className="bg-[#FFB800] hover:bg-[#FFB800]/90 disabled:bg-white/10 disabled:text-white/40 disabled:cursor-not-allowed px-6 py-3 flex items-center gap-2 text-[#0A0F14] font-bold text-sm tracking-[0.25em] transition-all"
          >
            <Send className="w-4 h-4" />
            SEND
          </button>
        </div>
        <div className="text-xs text-[#00F0FF]/40 text-center mt-3 font-mono">
          Press Enter to send • Shift+Enter for new line • ESC to close
        </div>
      </div>
    </div>
  );
}
