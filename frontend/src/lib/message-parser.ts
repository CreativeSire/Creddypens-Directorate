export type ParsedContent =
  | { type: "text"; content: string }
  | { type: "code"; content: string; language: string };

export function parseMessage(message: string): ParsedContent[] {
  const source = message || "";
  const parts: ParsedContent[] = [];
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = codeBlockRegex.exec(source)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: source.substring(lastIndex, match.index) });
    }
    parts.push({
      type: "code",
      content: (match[2] || "").trim(),
      language: (match[1] || "text").toLowerCase(),
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < source.length) {
    parts.push({ type: "text", content: source.substring(lastIndex) });
  }

  return parts.length ? parts : [{ type: "text", content: source }];
}

