"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { BookOpen, GraduationCap, LayoutDashboard, Settings, Users, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { getOrgId } from "@/lib/org";

const DEPTS_KEY = "creddypens_sidebar_departments_open";

type Dept = { name: string; slug: string; count: number; short: string };

const DEPARTMENTS: Dept[] = [
  { name: "Customer Experience", slug: "customer-experience", count: 6, short: "CX (6)" },
  { name: "Sales & Business Dev", slug: "sales-business-dev", count: 5, short: "Sales (5)" },
  { name: "Marketing & Creative", slug: "marketing-creative", count: 6, short: "Marketing (6)" },
  { name: "Operations & Admin", slug: "operations-admin", count: 7, short: "Operations (7)" },
  { name: "Technical & IT", slug: "technical-it", count: 6, short: "Technical (6)" },
  { name: "Specialized Services", slug: "specialized-services", count: 7, short: "Specialized (7)" },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/");
}

export default function Sidebar({
  collapsed,
  onToggleCollapsed,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const pathname = usePathname();
  const [deptOpen, setDeptOpen] = useState(true);

  const orgName = useMemo(() => getOrgId() || "org_test", []);

  useEffect(() => {
    try {
      const v = localStorage.getItem(DEPTS_KEY);
      if (v === "0") setDeptOpen(false);
    } catch {
      // ignore
    }
  }, []);

  function toggleDeptOpen() {
    setDeptOpen((o) => {
      const next = !o;
      try {
        localStorage.setItem(DEPTS_KEY, next ? "1" : "0");
      } catch {
        // ignore
      }
      return next;
    });
  }

  const navItem = (href: string, label: string, Icon: React.ComponentType<{ className?: string }>) => {
    const active = isActive(pathname, href);
    return (
      <Link
        href={href}
        className={cn(
          "flex items-center gap-3 px-4 py-3 text-sm border-l-4 transition-all",
          active ? "border-l-[#FFB800] text-[#FFB800] bg-[#FFB800]/5" : "border-l-transparent text-[#00F0FF]/80",
          !active && "hover:text-[#00F0FF] hover:border-l-[#00F0FF]/60 hover:bg-[#00F0FF]/5"
        )}
        title={label}
      >
        <Icon className="w-4 h-4" />
        {collapsed ? null : <span>{label}</span>}
      </Link>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Org Info */}
      <div className="border-b border-[#00F0FF]/30 p-4">
        {collapsed ? (
          <button
            className="w-full px-2 py-2 border border-[#00F0FF]/30 hover:bg-[#00F0FF]/10 text-xs"
            onClick={onToggleCollapsed}
            title="Toggle sidebar (Ctrl/Cmd+B)"
          >
            ⇔
          </button>
        ) : (
          <>
            <div className="text-xs text-[#00F0FF]/50 tracking-[0.25em]">ORGANIZATION</div>
            <div className="text-white mt-1 text-lg font-semibold">{orgName}</div>
            <div className="text-xs text-[#00F0FF] mt-1 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00FF00] animate-pulse" />
              STANDARD PLAN
            </div>
            <button
              className="mt-3 w-full px-3 py-2 border border-[#00F0FF]/30 hover:bg-[#00F0FF]/10 text-xs"
              onClick={onToggleCollapsed}
              title="Toggle sidebar (Ctrl/Cmd+B)"
            >
              COLLAPSE
            </button>
          </>
        )}
      </div>

      {/* Nav */}
      <div className="py-2">
        {navItem("/dashboard", "Dashboard", LayoutDashboard)}
        <button
          onClick={toggleDeptOpen}
          className={cn(
            "w-full flex items-center justify-between px-4 py-3 text-sm text-[#00F0FF]/80 hover:text-[#00F0FF] border-l-4 border-l-transparent hover:border-l-[#00F0FF]/60 hover:bg-[#00F0FF]/5"
          )}
        >
          <span className="flex items-center gap-3">
            <BookOpen className="w-4 h-4" />
            {collapsed ? null : "Departments"}
          </span>
          {collapsed ? null : (
            <ChevronDown className={cn("w-4 h-4 transition-transform", deptOpen ? "rotate-0" : "-rotate-90")} />
          )}
        </button>

        {deptOpen && !collapsed ? (
          <div className="pl-10">
            {DEPARTMENTS.map((d) => {
              const href = `/dashboard/departments/${d.slug}`;
              const active = isActive(pathname, href);
              return (
                <Link
                  key={d.slug}
                  href={href}
                  className={cn(
                    "block px-4 py-2 text-sm border-l-4 transition-all",
                    active
                      ? "border-l-[#FFB800] text-[#FFB800] bg-[#FFB800]/5"
                      : "border-l-transparent text-[#00F0FF]/70 hover:text-[#00F0FF] hover:bg-[#00F0FF]/5 hover:border-l-[#00F0FF]/60"
                  )}
                >
                  {d.short}
                </Link>
              );
            })}
          </div>
        ) : null}

        {navItem("/dashboard/my-agents", "My Agents", Users)}
        {navItem("/dashboard/academy", "The Academy", GraduationCap)}
        {navItem("/dashboard/settings", "Settings", Settings)}
      </div>

      {/* Quick Stats Footer */}
      {!collapsed ? (
        <div className="border-t border-[#00F0FF]/30 p-4 mt-auto">
          <div className="text-xs text-[#00F0FF]/50 mb-2">TODAY</div>
          <div className="flex justify-between text-sm">
            <span className="text-[#00F0FF]/80">
              Tasks: <span className="text-[#00F0FF]">12</span>
            </span>
            <span className="text-[#00F0FF]/80">
              Online: <span className="text-[#00FF00]">2</span>
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
