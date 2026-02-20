"use client";

import { useEffect, useRef } from "react";
import Prism from "prismjs";

import "prismjs/components/prism-bash";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/components/prism-sql";
import "prismjs/components/prism-typescript";

type CodeBlockProps = {
  code: string;
  language: string;
};

export function CodeBlock({ code, language }: CodeBlockProps) {
  const codeRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (codeRef.current) Prism.highlightElement(codeRef.current);
  }, [code, language]);

  const safeLanguage = language || "text";

  return (
    <div className="my-3 border border-cyan/30 bg-black/40">
      <div className="flex items-center justify-between px-3 py-2 border-b border-cyan/20 text-xs text-cyan/70 tracking-wider">
        <span>{safeLanguage.toUpperCase()}</span>
        <button
          onClick={() => navigator.clipboard.writeText(code)}
          className="px-2 py-1 border border-cyan/30 hover:border-cyan hover:text-cyan text-cyan/80"
        >
          COPY
        </button>
      </div>
      <pre className={`language-${safeLanguage} m-0 overflow-x-auto p-3 text-sm`}>
        <code ref={codeRef} className={`language-${safeLanguage}`}>
          {code}
        </code>
      </pre>
    </div>
  );
}

