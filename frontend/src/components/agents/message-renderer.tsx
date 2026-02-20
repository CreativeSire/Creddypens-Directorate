"use client";

import { CodeBlock } from "@/components/ui/code-block";
import { parseMessage } from "@/lib/message-parser";

export function MessageRenderer({ message }: { message: string }) {
  const parts = parseMessage(message);
  return (
    <div className="space-y-2">
      {parts.map((part, idx) =>
        part.type === "code" ? (
          <CodeBlock key={`${idx}-${part.language}`} code={part.content} language={part.language} />
        ) : (
          <p key={`${idx}-text`} className="whitespace-pre-wrap">
            {part.content}
          </p>
        ),
      )}
    </div>
  );
}

