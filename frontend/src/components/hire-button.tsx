"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getOrgId } from "@/lib/org";
import { Button } from "@/components/ui/button";
import { CheckoutModal } from "@/components/agents/checkout-modal";

export function HireButton({
  agent,
  disabled,
}: {
  agent: { code: string; role: string; price_cents: number };
  disabled?: boolean;
}) {
  const router = useRouter();
  const [orgId, setOrgId] = useState<string>("org_test");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOrgId(getOrgId() || "org_test");
  }, []);

  function onHire() {
    setOpen(true);
  }

  return (
    <>
      <Button onClick={onHire} disabled={disabled}>
        Hire
      </Button>
      {open ? (
        <CheckoutModal
          agent={agent}
          orgId={orgId}
          onClose={() => setOpen(false)}
          onSuccess={() => {
            setOpen(false);
            router.push("/dashboard/my-agents");
          }}
        />
      ) : null}
    </>
  );
}
