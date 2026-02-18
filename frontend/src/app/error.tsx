"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <AlertTriangle className="w-16 h-16 text-amber mx-auto mb-6" />
        <h1 className="text-4xl font-bold text-white mb-4">System Malfunction</h1>
        <p className="text-white/60 mb-8 leading-relaxed">
          A critical error occurred in directorate systems. Retry the operation or return to dashboard.
        </p>
        <div className="space-y-4">
          <Button onClick={reset} className="w-full">
            Retry Operation
          </Button>
          <Button onClick={() => (window.location.href = "/dashboard")} variant="secondary" className="w-full">
            Return to Dashboard
          </Button>
        </div>
        {error.digest ? <p className="text-xs text-white/40 mt-8 font-mono">Error ID: {error.digest}</p> : null}
      </div>
    </div>
  );
}
