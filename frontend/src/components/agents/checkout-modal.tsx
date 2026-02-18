"use client";

import { useState } from "react";

import { X, Check, CreditCard } from "lucide-react";

import { apiBaseUrl } from "@/lib/env";
import { toast } from "@/lib/toast";

type CheckoutModalProps = {
  agent: {
    code: string;
    role: string;
    price_cents: number;
  };
  orgId: string;
  onClose: () => void;
  onSuccess: () => void;
};

export function CheckoutModal({ agent, orgId, onClose, onSuccess }: CheckoutModalProps) {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkoutMode, setCheckoutMode] = useState<"mock" | "stripe" | null>(null);

  const price = Math.floor((agent.price_cents || 0) / 100);

  const handleCheckout = async () => {
    const toastId = toast.loading("Authorizing deployment...");
    setProcessing(true);
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/agents/${encodeURIComponent(agent.code)}/checkout`, {
        method: "POST",
        headers: {
          "X-Org-Id": orgId,
          "Content-Type": "application/json",
        },
      });
      const data = (await res.json().catch(() => ({}))) as {
        detail?: string;
        mode?: "mock" | "stripe";
        checkout_url?: string;
      };
      if (!res.ok) throw new Error(data.detail || "Checkout failed");
      setCheckoutMode(data.mode || null);

      if (data.mode === "stripe" && data.checkout_url) {
        toast.success("Redirecting to secure checkout...", toastId);
        window.location.assign(data.checkout_url);
        return;
      }

      toast.success(`Deployment authorized for ${agent.code}`, toastId);
      setTimeout(() => onSuccess(), 700);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Checkout failed", toastId);
      setError(err instanceof Error ? err.message : "Checkout failed");
      setProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#0A0F14]/95 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#0D1520] border-2 border-[#00F0FF]/30 max-w-md w-full">
        <div className="border-b border-[#00F0FF]/30 p-6 flex items-center justify-between">
          <div>
            <div className="text-xs text-[#FFB800] tracking-[0.25em] mb-1">DEPLOYMENT AUTHORIZATION</div>
            <div className="text-2xl text-white font-semibold">Hire {agent.code}</div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-[#00F0FF]/10 transition-colors focus-ring" disabled={processing}>
            <X className="w-5 h-5 text-white/70" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="border border-[#00F0FF]/30 p-4 bg-[#00F0FF]/5">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="text-xs text-[#00F0FF] tracking-[0.25em]">AGENT</div>
                <div className="text-xl text-white font-semibold mt-1">{agent.code}</div>
                <div className="text-sm text-[#00F0FF]/60 mt-1">{agent.role}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-[#00F0FF] tracking-[0.25em]">MONTHLY COST</div>
                <div className="text-2xl text-[#FFB800] font-bold mt-1">${price}</div>
              </div>
            </div>
          </div>

          <div className="border border-[#FFB800]/30 bg-[#FFB800]/10 p-4">
            <div className="flex gap-3">
              <CreditCard className="w-5 h-5 text-[#FFB800] flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-xs text-[#FFB800] tracking-[0.25em] mb-1">
                  {checkoutMode === "stripe" ? "SECURE CHECKOUT MODE" : "MOCK CHECKOUT MODE"}
                </div>
                <div className="text-xs text-white/70 leading-relaxed">
                  {checkoutMode === "stripe"
                    ? "You will be redirected to Stripe Checkout to complete subscription setup."
                    : "Payment processing is simulated. No charges will be made. Real billing will be enabled before public launch."}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-3">{"// DEPLOYMENT INCLUDES"}</div>
            {[
              "Unlimited task execution",
              "Academy retraining every 3 days",
              "Field Instance quality oversight",
              "Full interaction logs and traces",
              "Cancel anytime",
            ].map((t) => (
              <div key={t} className="flex items-center gap-2 text-sm text-white/80">
                <Check className="w-4 h-4 text-[#00FF00]" />
                <span>{t}</span>
              </div>
            ))}
          </div>

          {error && <div className="border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 border border-[#00F0FF]/30 text-[#00F0FF] py-3 text-sm tracking-[0.25em] hover:bg-[#00F0FF]/10 transition-all focus-ring"
              disabled={processing}
            >
              CANCEL
            </button>
            <button
              onClick={() => void handleCheckout()}
              disabled={processing}
              className="flex-1 bg-[#FFB800] hover:bg-[#FFB800]/90 disabled:bg-white/10 disabled:text-white/40 disabled:cursor-not-allowed text-[#0A0F14] py-3 text-sm font-bold tracking-[0.25em] transition-all flex items-center justify-center gap-2 focus-ring"
            >
              {processing ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#0A0F14]/30 border-t-[#0A0F14] rounded-full animate-spin" />
                  PROCESSING...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  AUTHORIZE
                </>
              )}
            </button>
          </div>

          <div className="text-xs text-white/50 text-center">
            By proceeding you authorize deployment of this agent to your organization.
          </div>
        </div>
      </div>
    </div>
  );
}
