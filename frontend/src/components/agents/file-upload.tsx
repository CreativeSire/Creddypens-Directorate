"use client";

import { useRef, useState } from "react";

import { FileText, Upload, X } from "lucide-react";

import { apiBaseUrl } from "@/lib/env";

export type UploadedFileItem = {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
};

type Props = {
  orgId: string;
  onChange: (items: UploadedFileItem[]) => void;
  maxFiles?: number;
};

export function FileUploadButton({ orgId, onChange, maxFiles = 5 }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<UploadedFileItem[]>([]);
  const [uploading, setUploading] = useState(false);

  const update = (next: UploadedFileItem[]) => {
    setItems(next);
    onChange(next);
  };

  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    const current = [...items];
    try {
      for (const file of files.slice(0, Math.max(0, maxFiles - current.length))) {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${apiBaseUrl()}/v1/files/upload?org_id=${encodeURIComponent(orgId)}`, {
          method: "POST",
          body: formData,
          headers: { "X-Org-Id": orgId },
        });
        if (!res.ok) continue;
        const data = (await res.json()) as UploadedFileItem;
        current.push(data);
      }
      update(current);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        multiple
        onChange={(event) => {
          const files = Array.from(event.target.files || []);
          void uploadFiles(files);
        }}
      />
      <div
        onDragOver={(event) => {
          event.preventDefault();
          event.stopPropagation();
        }}
        onDrop={(event) => {
          event.preventDefault();
          event.stopPropagation();
          const dropped = Array.from(event.dataTransfer.files || []);
          void uploadFiles(dropped);
        }}
        className="border border-dashed border-[#00F0FF]/30 p-3 rounded"
      >
        <button
          onClick={() => inputRef.current?.click()}
          className="px-3 py-2 border border-[#00F0FF]/30 text-[#00F0FF]/80 text-xs hover:text-[#00F0FF] focus-ring inline-flex items-center gap-2"
        >
          <Upload className="w-3.5 h-3.5" />
          {uploading ? "UPLOADING..." : "UPLOAD FILES"}
        </button>
        <div className="text-[11px] text-[#00F0FF]/50 mt-2">or drag and drop files here</div>
      </div>
      {items.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <button
              key={item.file_id}
              onClick={() => update(items.filter((entry) => entry.file_id !== item.file_id))}
              className="px-2 py-1 text-xs border border-[#00F0FF]/25 text-[#00F0FF]/70 hover:border-[#FFB800]/50 hover:text-[#FFB800] focus-ring inline-flex items-center gap-1"
              title="Remove file from context"
            >
              <FileText className="w-3 h-3" />
              {item.filename}
              <X className="w-3 h-3" />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
