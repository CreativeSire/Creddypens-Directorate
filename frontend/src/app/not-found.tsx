import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-void flex items-center justify-center px-6">
      <div className="text-center max-w-md">
        <FileQuestion className="w-16 h-16 text-cyan mx-auto mb-6" />
        <h1 className="text-6xl font-bold text-white mb-2">404</h1>
        <h2 className="text-2xl font-bold text-cyan mb-4">Asset Not Found</h2>
        <p className="text-white/60 mb-8 leading-relaxed">
          The requested resource does not exist in the directorate database. Check the URL or return to dashboard.
        </p>
        <Link href="/dashboard">
          <Button>Return to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}

