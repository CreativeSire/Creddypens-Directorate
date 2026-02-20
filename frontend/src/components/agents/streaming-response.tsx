"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  requestId: string;
  url: string;
  payload: object;
  headers?: Record<string, string>;
  onDone?: (data: { response: string; latency_ms?: number; tokens_used?: number; model_used?: string }) => void;
  onError?: (message: string) => void;
};

export function StreamingResponse({ requestId, url, payload, headers, onDone, onError }: Props) {
  const [text, setText] = useState("");
  const [running, setRunning] = useState(true);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const run = async () => {
      controllerRef.current = new AbortController();
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(headers || {}) },
          body: JSON.stringify(payload),
          signal: controllerRef.current.signal,
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() || "";
          for (const chunk of chunks) {
            const lines = chunk.split("\n");
            let eventType = "message";
            let eventData = "";
            for (const line of lines) {
              if (line.startsWith("event:")) eventType = line.slice(6).trim();
              if (line.startsWith("data:")) eventData += line.slice(5).trim();
            }
            if (!eventData) continue;
            const parsed = JSON.parse(eventData) as Record<string, unknown>;
            if (eventType === "token") {
              setText(String(parsed.partial || ""));
            } else if (eventType === "done") {
              setText(String(parsed.response || ""));
              onDone?.({
                response: String(parsed.response || ""),
                latency_ms: Number(parsed.latency_ms || 0),
                tokens_used: Number(parsed.tokens_used || 0),
                model_used: String(parsed.model_used || ""),
              });
              setRunning(false);
            } else if (eventType === "error") {
              onError?.(String(parsed.error || "Streaming failed"));
              setRunning(false);
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          onError?.((err as Error).message || "Streaming failed");
        }
        setRunning(false);
      }
    };
    void run();
    return () => {
      controllerRef.current?.abort();
    };
  }, [requestId, url, payload, headers, onDone, onError]);

  return (
    <div className="text-sm leading-relaxed text-white/90 whitespace-pre-wrap">
      {text}
      {running ? <span className="inline-block w-2 h-4 bg-[#FFB800] ml-1 animate-pulse align-middle" /> : null}
    </div>
  );
}
