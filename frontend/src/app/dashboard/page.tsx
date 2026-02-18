import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

const DirectorChat = dynamic(() => import("@/components/director/director-chat"), {
  loading: () => <Skeleton className="h-[520px] border border-cyan/30" />,
});
const StatsPanel = dynamic(() => import("@/components/dashboard/stats-panel"), {
  loading: () => <Skeleton className="h-[520px] border border-cyan/30" />,
});

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[65%_35%] gap-6">
      <DirectorChat />
      <StatsPanel />
    </div>
  );
}
