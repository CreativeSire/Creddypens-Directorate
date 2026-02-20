"use client";

import { useEffect, useState } from "react";

import { TaskBoard } from "@/components/inbox/task-board";
import { getOrgId } from "@/lib/org";

export default function InboxPage() {
  const [orgId, setOrgId] = useState<string | null>(null);

  useEffect(() => {
    setOrgId(getOrgId());
  }, []);

  if (!orgId) {
    return (
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">TASK INBOX</div>
        <h1 className="text-2xl font-bold text-white mt-2">Sign in required</h1>
        <p className="text-sm text-[#00F0FF]/60 mt-2">Missing organization context in this browser session.</p>
      </div>
    );
  }

  return <TaskBoard orgId={orgId} />;
}
