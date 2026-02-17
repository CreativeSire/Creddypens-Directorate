import { fetchAgents } from "@/lib/api";
import Landing from "@/components/landing";

export default async function Home() {
  const agents = await fetchAgents();
  return <Landing agents={agents} />;
}
