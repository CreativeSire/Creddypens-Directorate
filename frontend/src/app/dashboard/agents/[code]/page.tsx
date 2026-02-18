import Link from "next/link";
import { CheckCircle2, ChevronRight } from "lucide-react";

import { fetchAgent } from "@/lib/api";
import { DemoChat } from "@/components/demo-chat";
import { HireButton } from "@/components/hire-button";

const formatPrice = (cents: number) => `$${Math.floor(cents / 100)}/month`;

function splitCsv(text: string | null | undefined): string[] {
  if (!text) return [];
  return text
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function departmentToSlug(department: string): string {
  const map: Record<string, string> = {
    "Customer Experience": "customer-experience",
    "Sales & Business Development": "sales-business-dev",
    "Sales & Business Dev": "sales-business-dev",
    "Marketing & Creative": "marketing-creative",
    "Operations & Admin": "operations-admin",
    "Technical & IT": "technical-it",
    "Specialized Services": "specialized-services",
  };
  return map[department] || department.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

export default async function DashboardAgentPage({ params }: { params: { code: string } }) {
  const code = decodeURIComponent(params.code);
  const agent = await fetchAgent(code);
  const displayName = agent.human_name || agent.role;
  const idealFor = splitCsv(agent.ideal_for);

  return (
    <div className="min-h-screen bg-[#0A0F14] text-white">
      <div className="max-w-6xl mx-auto px-6 py-4 text-xs text-[#00F0FF]/60 flex items-center gap-2">
        <Link href="/dashboard" className="hover:text-[#00F0FF]">
          Dashboard
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <Link href={`/dashboard/departments/${departmentToSlug(agent.department)}`} className="hover:text-[#00F0FF]">
          {agent.department}
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-white">{agent.code}</span>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8 border-y border-[#00F0FF]/20">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-3xl">
            <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">{agent.department.toUpperCase()}</div>
            <h1 className="text-5xl font-bold tracking-wide">{agent.code}</h1>
            <div className="text-xl text-white/80 mt-2">
              {displayName} — {agent.role}
            </div>
            <div className="text-2xl font-bold text-[#FFB800] mt-2">{formatPrice(agent.price_cents)}</div>
            {agent.tagline ? <p className="text-lg italic text-[#00F0FF]/80 mt-4">{agent.tagline}</p> : null}
          </div>
          <div className="w-full md:w-auto">
            <HireButton agent={{ code: agent.code, role: agent.role, price_cents: agent.price_cents }} disabled={agent.status !== "active"} />
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-12">
        <h2 className="text-xs text-[#00F0FF] tracking-[0.25em] mb-6">{"// CORE CAPABILITIES"}</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {(agent.capabilities || []).slice(0, 8).map((capability, index) => (
            <div key={`${capability}-${index}`} className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 backdrop-blur-sm p-6">
              <div className="flex items-start gap-4">
                <CheckCircle2 className="w-5 h-5 text-[#00F0FF] mt-0.5 flex-shrink-0" />
                <p className="text-sm text-white/85 leading-relaxed">{capability}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-12 border-t border-[#00F0FF]/20">
        <h2 className="text-xs text-[#00F0FF] tracking-[0.25em] mb-6">{"// ASSET PROFILE"}</h2>
        <div className="text-white/80 leading-relaxed space-y-4 whitespace-pre-line">{agent.profile || agent.description}</div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-12 border-t border-[#00F0FF]/20">
        <h2 className="text-xs text-[#00F0FF] tracking-[0.25em] mb-6">{`// OPERATIONAL CAPABILITIES`}</h2>
        <div className="space-y-3">
          {(agent.operational_sections || []).map((section, idx) => (
            <details key={`${section.title}-${idx}`} className="border border-[#00F0FF]/30 bg-[#00F0FF]/5">
              <summary className="cursor-pointer list-none px-5 py-4 flex items-center justify-between">
                <span className="text-white font-semibold">{section.title}</span>
                <span className="text-[#00F0FF]/60 text-xs tracking-[0.25em]">EXPAND</span>
              </summary>
              <div className="px-5 pb-5">
                <div className="space-y-2">
                  {(section.items || []).map((item, itemIdx) => (
                    <div key={`${item}-${itemIdx}`} className="flex items-start gap-3 text-sm text-white/80">
                      <CheckCircle2 className="w-4 h-4 text-[#00F0FF] mt-0.5 flex-shrink-0" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </details>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-12 border-t border-[#00F0FF]/20">
        <div className="border-2 border-[#FFB800]/40 bg-[#FFB800]/5 p-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-3 h-3 rounded-full bg-[#FFB800] animate-pulse" />
            <h2 className="text-xs text-[#FFB800] tracking-[0.25em]">{"// LIVE DEMO — TEST BEFORE DEPLOYMENT"}</h2>
          </div>
          <p className="text-white/80 mb-6">
            Try {displayName} now and preview how this agent performs in real conversations before deployment.
          </p>
          <DemoChat agentCode={agent.code} companyName="TestCo" />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-12 border-t border-[#00F0FF]/20">
        <h2 className="text-xs text-[#00F0FF] tracking-[0.25em] mb-6">{"// RECOMMENDED DEPLOYMENT"}</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {idealFor.map((useCase, idx) => (
            <div key={`${useCase}-${idx}`} className="border border-[#00F0FF]/25 bg-[#00F0FF]/5 p-4 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-[#00FF00] mt-0.5 flex-shrink-0" />
              <span className="text-sm text-white/80">{useCase}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-12 border-t border-[#00F0FF]/20">
        <h2 className="text-xs text-[#00F0FF] tracking-[0.25em] mb-6">{"// COMMUNICATION PROFILE"}</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5">
            <div className="text-xs text-[#00F0FF]/70 tracking-[0.25em] mb-2">PERSONALITY</div>
            <p className="text-sm text-white/80">{agent.personality || "Professional and adaptable."}</p>
          </div>
          <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5">
            <div className="text-xs text-[#00F0FF]/70 tracking-[0.25em] mb-2">COMMUNICATION STYLE</div>
            <p className="text-sm text-white/80">{agent.communication_style || "Clear, concise, and context-aware."}</p>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-16 border-t border-[#00F0FF]/20 text-center">
        <div className="mb-4">
          <HireButton agent={{ code: agent.code, role: agent.role, price_cents: agent.price_cents }} disabled={agent.status !== "active"} />
        </div>
        <p className="text-sm text-white/60">Deploy {displayName} to your organization today.</p>
      </div>
    </div>
  );
}
