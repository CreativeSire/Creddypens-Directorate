"use client";

import { useEffect, useState } from "react";

import { MemoryManager } from "@/components/settings/memory-manager";
import { IntegrationsManager } from "@/components/settings/integrations";
import { getOrgId } from "@/lib/org";

export default function SettingsPage() {
  const [orgId, setOrgId] = useState<string | null>(null);

  useEffect(() => {
    setOrgId(getOrgId());
  }, []);

  if (!orgId) {
    return (
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">SETTINGS</div>
        <h1 className="text-2xl font-bold text-white mt-2">Sign in required</h1>
        <p className="text-sm text-[#00F0FF]/60 mt-2">Missing organization context. Log in again to manage settings.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">SETTINGS</div>
        <h1 className="text-2xl font-bold text-white mt-2">Organization Memory</h1>
        <p className="text-sm text-[#00F0FF]/60 mt-2">Store and manage reusable context for your agents.</p>
      </div>
      <MemoryManager orgId={orgId} />
      <IntegrationsManager orgId={orgId} />
    </div>
  );
}
