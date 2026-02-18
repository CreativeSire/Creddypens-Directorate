import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse bg-gradient-to-r from-[#00F0FF]/5 via-[#00F0FF]/10 to-[#00F0FF]/5 bg-[length:200%_100%]",
        className
      )}
      style={{ animation: "shimmer 2s infinite" }}
    />
  );
}

