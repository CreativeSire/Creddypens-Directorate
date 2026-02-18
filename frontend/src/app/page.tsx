"use client";

import { useEffect, useState } from "react";

import Landing from "@/components/landing";
import { fetchAgents } from "@/lib/api";
import type { Agent } from "@/lib/types";

export default function Home() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgents()
      .then((a) => setAgents(a))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  return <Landing agents={agents} loading={loading} />;
}
