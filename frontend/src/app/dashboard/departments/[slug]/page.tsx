import { apiBaseUrl } from "@/lib/env";
import type { Agent } from "@/lib/types";
import { AgentCard } from "@/components/agents/agent-card";

const DEPT_INFO: Record<string, { name: string; code: string; description: string }> = {
  "customer-experience": {
    name: "Customer Experience",
    code: "CX-01",
    description: "Front-line agents handling customer interactions",
  },
  "sales-business-dev": {
    name: "Sales & Business Development",
    code: "SD-02",
    description: "Revenue generation and pipeline management",
  },
  "marketing-creative": {
    name: "Marketing & Creative",
    code: "MC-03",
    description: "Content creation and brand amplification",
  },
  "operations-admin": {
    name: "Operations & Admin",
    code: "OA-04",
    description: "Back-office efficiency and coordination",
  },
  "technical-it": {
    name: "Technical & IT",
    code: "IT-05",
    description: "Development, security, and infrastructure",
  },
  "specialized-services": {
    name: "Specialized Services",
    code: "SP-06",
    description: "Domain-specific expertise and compliance",
  },
};

export default async function DepartmentPage({ params }: { params: { slug: string } }) {
  const dept = DEPT_INFO[params.slug];
  if (!dept) return <div className="text-white">Department not found</div>;

  const res = await fetch(`${apiBaseUrl()}/v1/agents?department=${encodeURIComponent(params.slug)}`, {
    cache: "no-store",
  });
  const agents = (await res.json()) as Agent[];

  return (
    <div>
      <div className="border-b border-[#00F0FF]/30 pb-6 mb-8">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em]">DEPARTMENT // {dept.code}</div>
        <h1 className="text-4xl text-white mt-2 tracking-wide">{dept.name}</h1>
        <p className="text-[#00F0FF]/60 mt-2 text-sm">
          {dept.description} • {agents.length} agents available
        </p>
      </div>

      <div className="flex gap-4 mb-6">
        <select className="bg-[#0D1520] border border-[#00F0FF]/30 text-white px-4 py-2 text-sm">
          <option>All Agents</option>
          <option>Active Only</option>
          <option>Coming Soon</option>
        </select>
        <select className="bg-[#0D1520] border border-[#00F0FF]/30 text-white px-4 py-2 text-sm">
          <option>All Price Tiers</option>
          <option>Essential</option>
          <option>Standard</option>
          <option>Premium</option>
        </select>
      </div>

      {agents.length === 0 ? (
        <div className="border-2 border-dashed border-[#00F0FF]/30 p-16 text-center bg-[#00F0FF]/5">
          <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-3">{"// DEPARTMENT EMPTY"}</div>
          <h3 className="text-2xl text-white mb-2">No Agents in This Department</h3>
          <p className="text-[#00F0FF]/60 text-sm max-w-md mx-auto">
            Agents are currently being retrained in The Academy. Check back soon or explore other departments.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <AgentCard key={agent.agent_id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
