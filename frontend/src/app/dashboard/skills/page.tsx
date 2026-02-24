"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Package, CheckCircle, Download, Trash2, Tag, Zap, Lock } from "lucide-react";

import { apiBaseUrl } from "@/lib/env";
import { getOrgId } from "@/lib/org";
import { toast } from "@/lib/toast";

type Skill = {
  skill_id: string;
  name: string;
  category: string;
  description: string;
  author: string;
  compatible_agents: string[];
  domain_tags: string[];
  tool_actions: string[];
  price_cents: number;
  status: string;
  install_count: number;
  created_at: string;
};

type InstalledSkill = {
  installation_id: string;
  org_id: string;
  agent_code: string | null;
  installed_at: string;
  skill: {
    skill_id: string;
    name: string;
    category: string;
    description: string;
    compatible_agents: string[];
    domain_tags: string[];
    price_cents: number;
    status: string;
  };
};

const CATEGORY_LABELS: Record<string, string> = {
  "Marketing & Creative": "Marketing & Creative",
  "Sales & Business Dev": "Sales & Business Dev",
  "Operations & Admin": "Operations & Admin",
  "Technical & IT": "Technical & IT",
  "Customer Experience": "Customer Experience",
  "Specialized Services": "Specialized Services",
  "Product & Design": "Product & Design",
  "Learning & Development": "Learning & Development",
};

function formatPrice(cents: number): string {
  if (cents === 0) return "FREE";
  return `$${(cents / 100).toFixed(0)}/mo`;
}

function categoryColor(category: string): string {
  const map: Record<string, string> = {
    "Marketing & Creative": "text-[#FF6B6B] border-[#FF6B6B]/40 bg-[#FF6B6B]/10",
    "Sales & Business Dev": "text-[#FFB800] border-[#FFB800]/40 bg-[#FFB800]/10",
    "Operations & Admin": "text-[#34D399] border-[#34D399]/40 bg-[#34D399]/10",
    "Technical & IT": "text-[#60A5FA] border-[#60A5FA]/40 bg-[#60A5FA]/10",
    "Customer Experience": "text-[#4ADE80] border-[#4ADE80]/40 bg-[#4ADE80]/10",
    "Specialized Services": "text-[#F87171] border-[#F87171]/40 bg-[#F87171]/10",
    "Product & Design": "text-[#A78BFA] border-[#A78BFA]/40 bg-[#A78BFA]/10",
    "Learning & Development": "text-[#F472B6] border-[#F472B6]/40 bg-[#F472B6]/10",
  };
  return map[category] ?? "text-[#00F0FF] border-[#00F0FF]/40 bg-[#00F0FF]/10";
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [installed, setInstalled] = useState<InstalledSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);

  useEffect(() => {
    setOrgId(getOrgId());
  }, []);

  const fetchAll = useCallback(async () => {
    if (!orgId) return;
    try {
      const [catRes, instRes] = await Promise.all([
        fetch(`${apiBaseUrl()}/v1/skills`),
        fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/skills`, {
          headers: { "X-Org-Id": orgId },
        }),
      ]);
      if (catRes.ok) setSkills((await catRes.json()) as Skill[]);
      if (instRes.ok) setInstalled((await instRes.json()) as InstalledSkill[]);
    } catch (err) {
      console.error("Failed to load skills:", err);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (!orgId) {
      setLoading(false);
      return;
    }
    void fetchAll();
  }, [fetchAll, orgId]);

  const installedIds = useMemo(
    () => new Set(installed.map((i) => i.skill.skill_id)),
    [installed]
  );

  const categories = useMemo(() => {
    return Array.from(new Set(skills.map((s) => s.category))).sort();
  }, [skills]);

  const filtered = useMemo(() => {
    if (categoryFilter === "all") return skills;
    return skills.filter((s) => s.category === categoryFilter);
  }, [skills, categoryFilter]);

  async function handleInstall(skillId: string) {
    if (!orgId) return;
    setActionLoading(skillId);
    try {
      const res = await fetch(
        `${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/skills/${encodeURIComponent(skillId)}`,
        { method: "POST", headers: { "X-Org-Id": orgId } }
      );
      if (!res.ok) {
        const err = (await res.json()) as { detail?: string };
        toast.error(err.detail ?? "Install failed");
        return;
      }
      toast.success("Skill pack installed org-wide");
      await fetchAll();
    } catch {
      toast.error("Network error. Please try again.");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleUninstall(skillId: string) {
    if (!orgId) return;
    setActionLoading(skillId);
    try {
      const res = await fetch(
        `${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/skills/${encodeURIComponent(skillId)}`,
        { method: "DELETE", headers: { "X-Org-Id": orgId } }
      );
      if (!res.ok) {
        toast.error("Uninstall failed");
        return;
      }
      toast.success("Skill pack removed");
      await fetchAll();
    } catch {
      toast.error("Network error. Please try again.");
    } finally {
      setActionLoading(null);
    }
  }

  if (!orgId) {
    return (
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">{"// AUTH REQUIRED"}</div>
        <div className="text-white font-semibold">Sign in to access the Skills Marketplace.</div>
        <button
          className="mt-4 px-5 py-3 bg-[#FFB800] text-[#0A0F14] font-bold tracking-[0.25em] hover:bg-[#FFB800]/90"
          onClick={() => (window.location.href = "/login")}
        >
          GO TO LOGIN
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Package className="w-6 h-6 text-[#FFB800]" />
            <h1 className="text-3xl text-white tracking-wide font-semibold">SKILLS MARKETPLACE</h1>
          </div>
          <p className="text-[#00F0FF]/60 text-sm">
            Enhance your agents with domain-specific skill packs. Install org-wide or per-agent.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-[#00F0FF]/60 border border-[#00F0FF]/30 px-3 py-2">
            <span className="text-[#00F0FF]">{installed.filter((i) => !i.agent_code).length}</span> ORG-WIDE INSTALLED
          </div>
          <div className="text-xs text-[#00F0FF]/60 border border-[#00F0FF]/30 px-3 py-2">
            <span className="text-[#FFB800]">{skills.length}</span> AVAILABLE
          </div>
        </div>
      </div>

      {/* Category Filters */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        <button
          className={`px-4 py-2 text-xs tracking-[0.2em] border transition-all whitespace-nowrap ${
            categoryFilter === "all"
              ? "bg-[#FFB800]/10 border-[#FFB800] text-[#FFB800]"
              : "border-[#00F0FF]/30 text-[#00F0FF]/60 hover:border-[#00F0FF] hover:text-[#00F0FF]"
          }`}
          onClick={() => setCategoryFilter("all")}
        >
          ALL ({skills.length})
        </button>
        {categories.map((cat) => {
          const count = skills.filter((s) => s.category === cat).length;
          const short = cat.replace(" & Creative", "").replace(" & Business Dev", "").replace(" & Admin", "").replace(" & IT", "").replace(" & Design", "").replace(" & Development", " Dev");
          return (
            <button
              key={cat}
              className={`px-4 py-2 text-xs tracking-[0.2em] border transition-all whitespace-nowrap ${
                categoryFilter === cat
                  ? "bg-[#FFB800]/10 border-[#FFB800] text-[#FFB800]"
                  : "border-[#00F0FF]/30 text-[#00F0FF]/60 hover:border-[#00F0FF] hover:text-[#00F0FF]"
              }`}
              onClick={() => setCategoryFilter(cat)}
            >
              {short.toUpperCase()} ({count})
            </button>
          );
        })}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="border border-[#00F0FF]/20 bg-[#0D1520] p-5 animate-pulse">
              <div className="h-4 w-24 bg-[#00F0FF]/10 mb-3 rounded" />
              <div className="h-6 w-40 bg-[#00F0FF]/10 mb-2 rounded" />
              <div className="h-3 w-full bg-[#00F0FF]/10 mb-1 rounded" />
              <div className="h-3 w-4/5 bg-[#00F0FF]/10 rounded" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="border border-[#00F0FF]/20 bg-[#0D1520] p-12 text-center">
          <Package className="w-12 h-12 text-[#00F0FF]/30 mx-auto mb-4" />
          <div className="text-white font-semibold mb-2">No skill packs in this category</div>
          <div className="text-sm text-[#00F0FF]/50">Check back soon — new packs are added regularly.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filtered.map((skill) => {
            const isInstalled = installedIds.has(skill.skill_id);
            const isLoading = actionLoading === skill.skill_id;
            const isPaid = skill.price_cents > 0;

            return (
              <div
                key={skill.skill_id}
                className={`border bg-[#0D1520] p-5 flex flex-col gap-3 transition-all ${
                  isInstalled ? "border-[#00FF00]/40" : "border-[#00F0FF]/20 hover:border-[#00F0FF]/50"
                }`}
              >
                {/* Top row: category badge + price */}
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] tracking-[0.2em] px-2 py-1 border font-semibold ${categoryColor(skill.category)}`}
                  >
                    {(CATEGORY_LABELS[skill.category] ?? skill.category).toUpperCase()}
                  </span>
                  <span
                    className={`text-xs font-bold tracking-wider ${
                      isPaid ? "text-[#FFB800]" : "text-[#00FF00]"
                    }`}
                  >
                    {isPaid && <Lock className="w-3 h-3 inline mr-1 opacity-70" />}
                    {formatPrice(skill.price_cents)}
                  </span>
                </div>

                {/* Name + author */}
                <div>
                  <div className="flex items-start gap-2">
                    <Zap className="w-4 h-4 text-[#FFB800] mt-0.5 flex-shrink-0" />
                    <h3 className="text-white font-semibold text-sm leading-tight">{skill.name}</h3>
                  </div>
                  <div className="text-[10px] text-[#00F0FF]/40 tracking-wider mt-1 ml-6">
                    by {skill.author}
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-[#00F0FF]/70 leading-relaxed line-clamp-3">
                  {skill.description}
                </p>

                {/* Domain tags */}
                {skill.domain_tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {skill.domain_tags.slice(0, 4).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 text-[9px] text-[#00F0FF]/50 border border-[#00F0FF]/20 px-2 py-0.5"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        {tag}
                      </span>
                    ))}
                    {skill.domain_tags.length > 4 && (
                      <span className="text-[9px] text-[#00F0FF]/40 px-1">+{skill.domain_tags.length - 4}</span>
                    )}
                  </div>
                )}

                {/* Footer: installs + action */}
                <div className="flex items-center justify-between mt-auto pt-3 border-t border-[#00F0FF]/10">
                  <span className="text-[10px] text-[#00F0FF]/40">
                    <Download className="w-3 h-3 inline mr-1" />
                    {skill.install_count.toLocaleString()} installs
                  </span>

                  {isInstalled ? (
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-[#00FF00] flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> INSTALLED
                      </span>
                      <button
                        disabled={isLoading}
                        onClick={() => void handleUninstall(skill.skill_id)}
                        className="text-[10px] text-[#FF6B6B]/70 hover:text-[#FF6B6B] border border-[#FF6B6B]/30 hover:border-[#FF6B6B] px-2 py-1 transition-all disabled:opacity-50"
                        title="Remove this skill pack"
                      >
                        {isLoading ? "..." : <Trash2 className="w-3 h-3" />}
                      </button>
                    </div>
                  ) : (
                    <button
                      disabled={isLoading || isPaid}
                      onClick={() => !isPaid && void handleInstall(skill.skill_id)}
                      className={`text-[10px] tracking-[0.15em] px-4 py-2 font-bold transition-all disabled:opacity-50 ${
                        isPaid
                          ? "border border-[#FFB800]/40 text-[#FFB800]/60 cursor-not-allowed"
                          : "bg-[#00F0FF]/10 border border-[#00F0FF] text-[#00F0FF] hover:bg-[#00F0FF]/20"
                      }`}
                      title={isPaid ? "Paid skill — billing coming soon" : "Install org-wide"}
                    >
                      {isLoading ? "INSTALLING..." : isPaid ? "COMING SOON" : "+ INSTALL"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer note */}
      <div className="mt-8 border border-[#00F0FF]/20 bg-[#00F0FF]/5 p-4">
        <div className="text-xs text-[#00F0FF]/60 leading-relaxed">
          <span className="text-[#00F0FF] font-semibold">Org-wide installs</span> activate a skill for all your agents automatically.
          To install a skill for a specific agent only, open that agent&apos;s settings page.
          Paid skill packs will be available via Stripe billing in the next release.
        </div>
      </div>
    </div>
  );
}
