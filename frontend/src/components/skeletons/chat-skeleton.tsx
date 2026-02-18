import { Skeleton } from "@/components/ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex justify-start">
        <Skeleton className="h-16 w-3/4 rounded-lg" />
      </div>
      <div className="flex justify-end">
        <Skeleton className="h-12 w-2/3 rounded-lg" />
      </div>
      <div className="flex justify-start">
        <Skeleton className="h-20 w-4/5 rounded-lg" />
      </div>
    </div>
  );
}

