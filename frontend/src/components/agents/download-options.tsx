"use client";

import { useState } from "react";

import { apiBaseUrl } from "@/lib/env";
import { toast } from "@/lib/toast";

type DownloadOptionsProps = {
  interactionId: string;
  response: string;
  orgId: string;
};

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

export function DownloadOptions({ interactionId, response, orgId }: DownloadOptionsProps) {
  const [downloading, setDownloading] = useState(false);

  const downloadPDF = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/interactions/${interactionId}/pdf`, {
        headers: { "X-Org-Id": orgId },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      triggerBlobDownload(blob, `response-${interactionId}.pdf`);
      toast.success("PDF downloaded");
    } catch {
      toast.error("PDF download failed");
    } finally {
      setDownloading(false);
    }
  };

  const downloadCSV = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/interactions/${interactionId}/csv`, {
        headers: { "X-Org-Id": orgId },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      triggerBlobDownload(blob, `response-${interactionId}.csv`);
      toast.success("CSV downloaded");
    } catch {
      toast.error("CSV download failed");
    } finally {
      setDownloading(false);
    }
  };

  const copyAsEmail = async () => {
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/interactions/${interactionId}/email`, {
        headers: { "X-Org-Id": orgId },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const email = (await res.json()) as { to: string; subject: string; body: string };
      const mailto = `mailto:${email.to || ""}?subject=${encodeURIComponent(email.subject || "Email Draft")}&body=${encodeURIComponent(email.body || "")}`;
      await navigator.clipboard.writeText(mailto);
      toast.success("Email draft copied");
    } catch {
      toast.error("Failed to format email");
    }
  };

  const showCsv = response.includes("|");

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      <button
        onClick={() => void downloadPDF()}
        disabled={downloading}
        className="px-2 py-1 text-xs border border-cyan/30 text-cyan/80 hover:border-cyan disabled:opacity-60"
      >
        PDF
      </button>
      {showCsv ? (
        <button
          onClick={() => void downloadCSV()}
          disabled={downloading}
          className="px-2 py-1 text-xs border border-cyan/30 text-cyan/80 hover:border-cyan disabled:opacity-60"
        >
          CSV
        </button>
      ) : null}
      <button
        onClick={() => void copyAsEmail()}
        className="px-2 py-1 text-xs border border-amber/40 text-amber hover:border-amber"
      >
        EMAIL
      </button>
    </div>
  );
}

