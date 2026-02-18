"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiBaseUrl } from "@/lib/env";
import { setOrgId } from "@/lib/org";
import { supabase } from "@/lib/supabase";
import { toast } from "@/lib/toast";
import { Button } from "@/components/ui/button";

async function bootstrapOrg(accessToken: string) {
  const res = await fetch(`${apiBaseUrl()}/v1/auth/bootstrap`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`Bootstrap failed: ${res.status}`);
  return res.json() as Promise<{ org_id: string }>;
}

export default function SignupPage() {
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
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) throw error;
      const token = data.session?.access_token;
      if (!token) throw new Error("No access token (email confirmations may be enabled)");

      const boot = await bootstrapOrg(token);
      setOrgId(boot.org_id);
      toast.success("Account created successfully.");
      router.push("/command-center");
    } catch (e) {
      const message = e instanceof Error ? e.message : "Signup failed";
      setError(message);
      toast.error("Failed to create account. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-void text-white">
      <div className="w-full max-w-md rounded-2xl border border-cyan/30 bg-void-2 p-6 space-y-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Sign up</h1>
          <div className="text-sm text-white/60">Create your clearance.</div>
        </div>
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-1">
            <label className="text-sm">Email</label>
            <input
              className="w-full h-11 rounded-md border border-cyan/30 bg-void px-3 text-sm focus-ring"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm">Password</label>
            <input
              className="w-full h-11 rounded-md border border-cyan/30 bg-void px-3 text-sm focus-ring"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              minLength={8}
              required
            />
          </div>
          {error ? <div className="text-sm text-red-400">{error}</div> : null}
          <Button className="w-full" disabled={busy}>
            {busy ? "Creating..." : "Create account"}
          </Button>
        </form>
        <div className="text-sm text-white/60">
          Already have access?{" "}
          <Link className="underline underline-offset-4 focus-ring" href="/login">
            Login
          </Link>
        </div>
      </div>
    </div>
  );
}
