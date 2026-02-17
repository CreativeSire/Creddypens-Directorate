import DirectorChat from "@/components/director/director-chat";
import StatsPanel from "@/components/dashboard/stats-panel";

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[65%_35%] gap-6">
      <DirectorChat />
      <StatsPanel />
    </div>
  );
}

