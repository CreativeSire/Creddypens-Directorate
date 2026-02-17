import type { Metadata } from "next";

import { fetchAgent } from "@/lib/api";
import { DemoChat } from "@/components/demo-chat";
import { HireButton } from "@/components/hire-button";

export async function generateMetadata({ params }: { params: { code: string } }): Promise<Metadata> {
  return { title: `${decodeURIComponent(params.code)} | CreddyPens` };
}

const formatPrice = (cents: number) => `$${Math.floor(cents / 100)}/mo`;

export default async function AgentPage({ params }: { params: { code: string } }) {
  const code = decodeURIComponent(params.code);
  const agent = await fetchAgent(code);

  const promptSummary = agent.system_prompt
    ? agent.system_prompt.split(".").slice(0, 2).join(".").trim() + "."
    : "No prompt configured.";

  return (
    <div className="min-h-screen p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex items-start justify-between gap-6">
        <div className="space-y-2">
          <div className="text-sm text-muted-foreground">{agent.department}</div>
          <h1 className="text-3xl font-semibold">{agent.code}</h1>
          <div className="text-lg text-muted-foreground">{agent.role}</div>
          <p className="text-sm max-w-2xl">{agent.description}</p>
          <div className="text-xl font-semibold">{formatPrice(agent.price_cents)}</div>
          <div className="text-xs text-muted-foreground">
            Routing: {agent.llm_provider}/{agent.llm_model}
          </div>
        </div>
        <HireButton agent={{ code: agent.code, role: agent.role, price_cents: agent.price_cents }} disabled={agent.status !== "active"} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border p-4 space-y-2">
          <div className="text-sm font-semibold">System Prompt (Summary)</div>
          <div className="text-sm text-muted-foreground whitespace-pre-wrap">{promptSummary}</div>
        </div>
        <DemoChat agentCode={agent.code} companyName="TestCo" />
      </div>
    </div>
  );
}
