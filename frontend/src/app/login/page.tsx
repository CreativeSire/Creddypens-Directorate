"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiBaseUrl } from "@/lib/env";
import { setOrgId } from "@/lib/org";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";

async function bootstrapOrg(accessToken: string) {
  const res = await fetch(`${apiBaseUrl()}/v1/auth/bootstrap`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`Bootstrap failed: ${res.status}`);
  return res.json() as Promise<{ org_id: string }>;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      const token = data.session?.access_token;
      if (!token) throw new Error("No access token");

      const boot = await bootstrapOrg(token);
      setOrgId(boot.org_id);
      router.push("/command-center");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-md rounded-2xl border p-6 space-y-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Login</h1>
          <div className="text-sm text-muted-foreground">Access your Command Center.</div>
        </div>
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-1">
            <label className="text-sm">Email</label>
            <input
              className="w-full h-10 rounded-md border bg-background px-3 text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm">Password</label>
            <input
              className="w-full h-10 rounded-md border bg-background px-3 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />
          </div>
          {error ? <div className="text-sm text-red-600">{error}</div> : null}
          <Button className="w-full" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        <div className="text-sm text-muted-foreground">
          No account?{" "}
          <Link className="underline underline-offset-4" href="/signup">
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
}

