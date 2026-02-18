"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Shield } from "lucide-react";

import { cn } from "@/lib/utils";
import { getOrgId } from "@/lib/org";
import { supabase } from "@/lib/supabase";
import { toast } from "@/lib/toast";
import { MobileNav } from "@/components/layout/mobile-nav";
import Sidebar from "@/components/navigation/sidebar";

const SIDEBAR_KEY = "creddypens_sidebar_collapsed";

function getInitialCollapsed() {
  try {
    const v = localStorage.getItem(SIDEBAR_KEY);
    return v === "1";
  } catch {
    return false;
  }
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  const [orgName, setOrgName] = useState<string>("—");

  useEffect(() => {
    setCollapsed(getInitialCollapsed());
  }, []);

  useEffect(() => {
    setOrgName(getOrgId() || "—");
  }, []);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((c) => {
      const next = !c;
      try {
        localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const isMac = navigator.platform.toLowerCase().includes("mac");
      const mod = isMac ? e.metaKey : e.ctrlKey;
      if (mod && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleCollapsed();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggleCollapsed]);

  const sidebarWidth = collapsed ? 72 : 260;

  async function handleLogout() {
    await supabase.auth.signOut();
    toast.success("Logged out successfully");
    window.location.href = "/login";
  }

  return (
    <div className="min-h-screen bg-[#0A0F14] text-[#00F0FF] font-mono">
      {/* Top Nav */}
      <div className="fixed top-0 left-0 right-0 h-[60px] z-[100] border-b border-[#00F0FF]/30 bg-[rgba(10,15,20,0.95)] backdrop-blur">
        <div className="h-full px-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <MobileNav />
            <Link href="/" className="flex items-center gap-3">
              <Shield className="w-6 h-6 text-[#00F0FF]" />
              <div className="leading-none">
                <div className="text-sm font-bold tracking-wider text-white">THE CREDDYPENS DIRECTORATE</div>
                <div className="text-[10px] text-[#00F0FF]/60 tracking-[0.25em]">COMMAND CENTER</div>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-xs text-[#00F0FF]/60">
              ORG: <span className="text-white">{orgName}</span>
            </div>
            <details className="relative">
              <summary className="list-none cursor-pointer px-4 py-2 border border-[#00F0FF]/30 hover:bg-[#00F0FF]/10 focus-ring">
                USER MENU
              </summary>
              <div className="absolute right-0 mt-2 w-56 border border-[#00F0FF]/30 bg-[#0D1520]">
                <div className="p-3 border-b border-[#00F0FF]/20">
                  <div className="text-[10px] text-[#00F0FF]/60 tracking-[0.25em]">ORGANIZATION</div>
                  <div className="text-sm text-white mt-1">{orgName}</div>
                </div>
                <div className="p-2 flex flex-col">
                  <Link
                    href="/dashboard/settings"
                    className="px-3 py-2 text-sm text-[#00F0FF] hover:bg-[#00F0FF]/10 focus-ring"
                  >
                    Settings
                  </Link>
                  <button
                    onClick={() => void handleLogout()}
                    className="px-3 py-2 text-left text-sm text-[#FFB800] hover:bg-[#FFB800]/10 focus-ring"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </details>
          </div>
        </div>
      </div>

      {/* Sidebar (desktop) */}
      <div
        className={cn(
          "hidden md:block fixed left-0 top-[60px] bottom-0 border-r border-[#00F0FF]/30 bg-[#0D1520] overflow-y-auto"
        )}
        style={{ width: sidebarWidth }}
      >
        <Sidebar collapsed={collapsed} onToggleCollapsed={toggleCollapsed} />
      </div>

      {/* Main */}
      <main
        className="pt-[60px] bg-[#0A0F14] min-h-[calc(100vh-60px)]"
        style={{ marginLeft: 0 }}
      >
        <div className="md:block hidden" style={{ marginLeft: sidebarWidth }} />
        <div className="px-8 py-8 md:ml-[260px]" style={collapsed ? { marginLeft: 72 } : undefined}>
          {children}
        </div>
      </main>
    </div>
  );
}
