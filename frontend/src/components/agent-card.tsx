import Link from "next/link";

import type { Agent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function formatPrice(cents: number) {
  if (!cents) return "$0";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}

export function AgentCard({ agent }: { agent: Agent }) {
  const active = agent.status === "active";
  return (
    <Card className={cn("h-full", active ? "border-foreground/30" : "opacity-80")}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-3">
          <span>{agent.code}</span>
          <span
            className={cn(
              "text-xs rounded-full px-2 py-1 border",
              active ? "border-emerald-400/50 text-emerald-600" : "border-muted-foreground/30 text-muted-foreground"
            )}
          >
            {active ? "ACTIVE" : "COMING SOON"}
          </span>
        </CardTitle>
        <div className="text-sm text-muted-foreground">{agent.role}</div>
        <div className="text-xs text-muted-foreground">{agent.department}</div>
      </CardHeader>
      <CardContent className="text-sm">{agent.description}</CardContent>
      <CardFooter className="justify-between gap-3">
        <div className="text-sm font-semibold">{formatPrice(agent.price_cents)}/mo</div>
        {active ? (
          <Button asChild size="sm">
            <Link href={`/agents/${encodeURIComponent(agent.code)}`}>View Dossier</Link>
          </Button>
        ) : (
          <Button size="sm" variant="outline" disabled>
            Clearance Pending
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

