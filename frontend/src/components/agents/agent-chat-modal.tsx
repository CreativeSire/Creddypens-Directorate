"use client";

import { useEffect, useRef, useState } from "react";

import { X, Send, Plus, Search, Brain, Mic, MicOff, FileText, Image as ImageIcon, Link2 } from "lucide-react";

import { apiBaseUrl } from "@/lib/env";
import type { AgentDetail, ExecuteResponse } from "@/lib/types";
import { ChatSkeleton } from "@/components/skeletons/chat-skeleton";
import { MessageFeedback } from "@/components/agents/message-feedback";
import { FileUploadButton, type UploadedFileItem } from "@/components/agents/file-upload";
import { StreamingResponse } from "@/components/agents/streaming-response";

type Message = {
  role: "user" | "agent";
  content: string;
  timestamp: string;
  interactionId?: string;
  metadata?: {
    model_used?: string;
    latency_ms?: number;
    tokens_used?: number;
  };
  suggestedAgent?: ExecuteResponse["suggested_agent"];
};

type AgentChatModalProps = {
  agentCode: string;
  orgId: string;
  onClose: () => void;
  onAfterMessage?: () => void;
  onSwitchAgent?: (agentCode: string) => void;
};

type AgentDetailLite = Pick<AgentDetail, "code" | "role" | "department">;

type SpeechRecognitionResultLike = { transcript: string };
type SpeechRecognitionResultListLike = ArrayLike<ArrayLike<SpeechRecognitionResultLike>>;
type SpeechRecognitionEventLike = { results: SpeechRecognitionResultListLike };

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type WindowWithSpeechRecognition = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

function newSessionId() {
  try {
    return `chat-${crypto.randomUUID()}`;
  } catch {
    return `chat-${Date.now()}`;
  }
}

type LocalAttachment = {
  name: string;
  mime_type?: string;
  content_excerpt?: string;
  size_bytes?: number;
};

export function AgentChatModal({ agentCode, orgId, onClose, onAfterMessage, onSwitchAgent }: AgentChatModalProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agent, setAgent] = useState<AgentDetailLite | null>(null);
  const [showActions, setShowActions] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const [deepResearch, setDeepResearch] = useState(false);
  const [outputFormat, setOutputFormat] = useState<"text" | "markdown" | "json" | "email" | "csv" | "code" | "presentation">("text");
  const [attachments, setAttachments] = useState<LocalAttachment[]>([]);
  const [voiceListening, setVoiceListening] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileItem[]>([]);
  const [streamRequest, setStreamRequest] = useState<{
    id: string;
    payload: Record<string, unknown>;
  } | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const speechRef = useRef<SpeechRecognitionLike | null>(null);

  const [sessionId, setSessionId] = useState<string>(() => newSessionId());
  useEffect(() => {
    setSessionId(newSessionId());
    setAttachments([]);
    setUploadedFiles([]);
    setWebSearch(false);
    setDeepResearch(false);
    setOutputFormat("text");
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

  const toggleVoiceInput = () => {
    const SpeechRecognitionApi =
      typeof window !== "undefined"
        ? (window as WindowWithSpeechRecognition).SpeechRecognition ||
          (window as WindowWithSpeechRecognition).webkitSpeechRecognition
        : undefined;

    if (!SpeechRecognitionApi) return;

    if (voiceListening && speechRef.current) {
      speechRef.current.stop();
      setVoiceListening(false);
      return;
    }

    const recognition = new SpeechRecognitionApi();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onerror = () => setVoiceListening(false);
    recognition.onend = () => setVoiceListening(false);
    speechRef.current = recognition;
    recognition.start();
    setVoiceListening(true);
  };

  const handleHireAndSwitch = async (suggestedCode: string) => {
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(suggestedCode)}/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
      });
      const payload = (await res.json()) as { checkout_url?: string };
      if (!res.ok) throw new Error("checkout failed");
      if (payload.checkout_url) {
        window.location.href = payload.checkout_url;
        return;
      }
      onAfterMessage?.();
      if (onSwitchAgent) onSwitchAgent(suggestedCode);
    } catch (error) {
      console.error("Failed to hire suggested agent:", error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const content = input;
    const userMsg: Message = { role: "user", content, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setStreamError(null);

    try {
      const payload = {
        message: content,
        session_id: sessionId,
        file_ids: uploadedFiles.map((item) => item.file_id),
        context: {
          company_name: "",
          tone: "",
          output_format: outputFormat,
          web_search: webSearch,
          deep_research: deepResearch,
          attachments,
          additional: {
            action_menu_enabled: true,
            requested_tools: {
              web_search: webSearch,
              deep_research: deepResearch,
              voice_input: voiceListening,
            },
          },
        },
      };
      setStreamRequest({
        id: `${Date.now()}-${Math.random()}`,
        payload,
      });
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
      setStreamRequest(null);
    } finally {
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
  };

  if (!agent) {
    return (
      <div className="fixed inset-0 bg-[#0A0F14]/95 flex items-center justify-center z-50 p-6">
        <div className="w-full max-w-3xl border border-cyan/30 bg-cyan/5">
          <ChatSkeleton />
        </div>
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

        <button onClick={onClose} className="p-2 hover:bg-[#00F0FF]/10 transition-colors group focus-ring" aria-label="Close">
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
                {msg.metadata
                  ? `Response Time • ${msg.metadata.latency_ms ?? 0}ms${
                      msg.metadata.tokens_used ? ` • ${msg.metadata.tokens_used} tokens` : ""
                    }`
                  : new Date(msg.timestamp).toLocaleTimeString()}
              </div>

              {msg.role === "agent" && msg.interactionId ? <MessageFeedback interactionId={msg.interactionId} /> : null}

              {msg.role === "agent" && msg.suggestedAgent ? (
                <div className="mt-3 border border-[#00F0FF]/20 bg-[#00F0FF]/5 p-3">
                  <div className="text-xs text-[#00F0FF]/80 tracking-[0.2em] mb-1">SPECIALIST REFERRAL</div>
                  <div className="text-sm text-white/90">{msg.suggestedAgent.reason}</div>
                  <div className="text-xs text-[#00F0FF]/60 mt-1">
                    Suggested: {msg.suggestedAgent.code} • {msg.suggestedAgent.department || "Directorate"}
                  </div>
                  <div className="flex gap-2 mt-3">
                    {msg.suggestedAgent.is_hired ? (
                      <button
                        onClick={() => onSwitchAgent?.(msg.suggestedAgent?.code || "")}
                        className="px-3 py-2 text-xs tracking-[0.18em] bg-[#FFB800] text-[#0A0F14] hover:bg-[#FFB800]/90 focus-ring"
                      >
                        SWITCH AGENT
                      </button>
                    ) : (
                      <button
                        onClick={() => void handleHireAndSwitch(msg.suggestedAgent?.code || "")}
                        className="px-3 py-2 text-xs tracking-[0.18em] bg-[#FFB800] text-[#0A0F14] hover:bg-[#FFB800]/90 focus-ring"
                      >
                        HIRE & SWITCH
                      </button>
                    )}
                    <button
                      onClick={() => {
                        const code = msg.suggestedAgent?.code || "";
                        if (!code) return;
                        window.location.href = `/dashboard/agents/${encodeURIComponent(code)}`;
                      }}
                      className="px-3 py-2 text-xs tracking-[0.18em] border border-[#00F0FF]/30 text-[#00F0FF] hover:border-[#00F0FF] focus-ring"
                    >
                      OPEN DOSSIER
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ))}

        {streamRequest && (
          <div className="flex justify-start">
            <div className="bg-[#FFB800]/5 border border-[#FFB800]/20 p-4 flex items-center gap-3">
              <div className="w-full">
                <StreamingResponse
                  requestId={streamRequest.id}
                  url={`${apiBaseUrl()}/v1/agents/${encodeURIComponent(agentCode)}/execute/stream`}
                  payload={streamRequest.payload}
                  headers={{ "X-Org-Id": orgId }}
                  onDone={(streamData) => {
                    const agentMsg: Message = {
                      role: "agent",
                      content: streamData.response || "",
                      timestamp: new Date().toISOString(),
                      metadata: {
                        model_used: streamData.model_used,
                        latency_ms: streamData.latency_ms,
                        tokens_used: streamData.tokens_used,
                      },
                    };
                    setMessages((prev) => [...prev, agentMsg]);
                    setStreamRequest(null);
                    setLoading(false);
                    onAfterMessage?.();
                  }}
                  onError={(message) => {
                    setStreamError(message);
                    setMessages((prev) => [
                      ...prev,
                      {
                        role: "agent",
                        content: "ERROR: Failed to stream response. Please retry.",
                        timestamp: new Date().toISOString(),
                      },
                    ]);
                    setStreamRequest(null);
                    setLoading(false);
                  }}
                />
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() => {
                      setStreamRequest(null);
                      setLoading(false);
                      setMessages((prev) => [
                        ...prev,
                        {
                          role: "agent",
                          content: "Streaming cancelled.",
                          timestamp: new Date().toISOString(),
                        },
                      ]);
                    }}
                    className="text-xs border border-[#FFB800]/50 text-[#FFB800] px-2 py-1 tracking-[0.15em]"
                  >
                    CANCEL
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        {streamError ? <div className="text-xs text-red-400">{streamError}</div> : null}

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
            className="flex-1 resize-none bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-4 py-3 text-[#00F0FF] placeholder-[#00F0FF]/30 focus:outline-none focus:border-[#00F0FF] focus-ring font-mono text-sm"
            rows={2}
            disabled={loading}
          />
          <button
            onClick={() => void sendMessage()}
            disabled={loading || !!streamRequest || !input.trim()}
            className="bg-[#FFB800] hover:bg-[#FFB800]/90 disabled:bg-white/10 disabled:text-white/40 disabled:cursor-not-allowed px-6 py-3 flex items-center gap-2 text-[#0A0F14] font-bold text-sm tracking-[0.25em] transition-all focus-ring"
          >
            <Send className="w-4 h-4" />
            SEND
          </button>
        </div>
        <div className="max-w-4xl mx-auto mt-3">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setShowActions((v) => !v)}
              className="px-3 py-2 border border-[#00F0FF]/30 text-[#00F0FF]/80 text-xs tracking-[0.2em] hover:text-[#00F0FF] hover:border-[#00F0FF] focus-ring"
            >
              <span className="inline-flex items-center gap-2"><Plus className="w-3.5 h-3.5" />TOOLS</span>
            </button>
            <button
              onClick={() => setWebSearch((v) => !v)}
              className={`px-3 py-2 text-xs tracking-[0.2em] border focus-ring ${webSearch ? "border-[#FFB800] text-[#FFB800]" : "border-[#00F0FF]/30 text-[#00F0FF]/70"}`}
            >
              <span className="inline-flex items-center gap-2"><Search className="w-3.5 h-3.5" />WEB SEARCH</span>
            </button>
            <button
              onClick={() => setDeepResearch((v) => !v)}
              className={`px-3 py-2 text-xs tracking-[0.2em] border focus-ring ${deepResearch ? "border-[#FFB800] text-[#FFB800]" : "border-[#00F0FF]/30 text-[#00F0FF]/70"}`}
            >
              <span className="inline-flex items-center gap-2"><Brain className="w-3.5 h-3.5" />DEEP RESEARCH</span>
            </button>
            <button
              onClick={toggleVoiceInput}
              className={`px-3 py-2 text-xs tracking-[0.2em] border focus-ring ${voiceListening ? "border-[#FFB800] text-[#FFB800]" : "border-[#00F0FF]/30 text-[#00F0FF]/70"}`}
            >
              <span className="inline-flex items-center gap-2">{voiceListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}VOICE</span>
            </button>
            <select
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value as typeof outputFormat)}
              className="bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-3 py-2 text-xs tracking-[0.15em] text-[#00F0FF] focus:outline-none focus:border-[#00F0FF] focus-ring"
            >
              <option value="text">TEXT</option>
              <option value="markdown">MARKDOWN</option>
              <option value="json">JSON</option>
              <option value="email">EMAIL</option>
              <option value="csv">CSV</option>
              <option value="code">CODE</option>
              <option value="presentation">PRESENTATION</option>
            </select>
          </div>
          {showActions && (
            <div className="mt-2 border border-[#00F0FF]/20 bg-[#00F0FF]/5 p-3 flex items-center gap-2 flex-wrap">
              <button
                onClick={() => setShowActions((v) => !v)}
                className="px-3 py-2 border border-[#00F0FF]/30 text-[#00F0FF]/80 text-xs hover:text-[#00F0FF] focus-ring inline-flex items-center gap-2"
              >
                <FileText className="w-3.5 h-3.5" /> ADD FILES
              </button>
              <button
                onClick={() => setShowActions((v) => !v)}
                className="px-3 py-2 border border-[#00F0FF]/30 text-[#00F0FF]/80 text-xs hover:text-[#00F0FF] focus-ring inline-flex items-center gap-2"
              >
                <ImageIcon className="w-3.5 h-3.5" /> ADD IMAGE
              </button>
            </div>
          )}
          {showActions ? <FileUploadButton orgId={orgId} onChange={setUploadedFiles} /> : null}
          {attachments.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {attachments.map((attachment, idx) => (
                <button
                  key={`${attachment.name}-${idx}`}
                  onClick={() => setAttachments((prev) => prev.filter((_, i) => i !== idx))}
                  className="px-2 py-1 text-xs border border-[#00F0FF]/25 text-[#00F0FF]/70 hover:border-[#FFB800]/50 hover:text-[#FFB800] focus-ring inline-flex items-center gap-1"
                  title="Remove attachment"
                >
                  <Link2 className="w-3 h-3" />{attachment.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="text-xs text-[#00F0FF]/40 text-center mt-3 font-mono">
          Press Enter to send • Shift+Enter for new line • ESC to close
        </div>
      </div>
    </div>
  );
}
