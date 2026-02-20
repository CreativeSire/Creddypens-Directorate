"use client";

import { useCallback, useEffect, useState } from "react";

import { apiBaseUrl } from "@/lib/env";

type IntegrationItem = {
  integration_id: string;
  org_id: string;
  integration_type: string;
  config: Record<string, unknown>;
  is_active: boolean;
};

type Props = {
  orgId: string;
};

export function IntegrationsManager({ orgId }: Props) {
  const [items, setItems] = useState<IntegrationItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [slackWebhook, setSlackWebhook] = useState("");
  const [emailConfig, setEmailConfig] = useState({
    smtp_host: "",
    smtp_port: "587",
    smtp_user: "",
    smtp_password: "",
    from_email: "",
    test_recipient: "",
  });
  const [webhookConfig, setWebhookConfig] = useState({
    url: "",
    headers_json: "{}",
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/integrations`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = (await response.json()) as IntegrationItem[];
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load integrations");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  const addSlack = async () => {
    try {
      const response = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/integrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ integration_type: "slack", config: { webhook_url: slackWebhook } }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setSlackWebhook("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add Slack integration");
    }
  };

  const addEmail = async () => {
    try {
      const response = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/integrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          integration_type: "email",
          config: {
            smtp_host: emailConfig.smtp_host,
            smtp_port: Number(emailConfig.smtp_port),
            smtp_user: emailConfig.smtp_user,
            smtp_password: emailConfig.smtp_password,
            from_email: emailConfig.from_email,
            test_recipient: emailConfig.test_recipient,
            use_tls: true,
          },
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setEmailConfig({
        smtp_host: "",
        smtp_port: "587",
        smtp_user: "",
        smtp_password: "",
        from_email: "",
        test_recipient: "",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add Email integration");
    }
  };

  const addWebhook = async () => {
    try {
      const parsedHeaders = webhookConfig.headers_json.trim() ? JSON.parse(webhookConfig.headers_json) : {};
      const response = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/integrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          integration_type: "webhook",
          config: {
            url: webhookConfig.url,
            headers: parsedHeaders,
          },
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setWebhookConfig({ url: "", headers_json: "{}" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add Webhook integration");
    }
  };

  const testIntegration = async (item: IntegrationItem) => {
    try {
      const payload =
        item.integration_type === "email"
          ? { to_email: String(item.config.test_recipient || ""), subject: "Test", body: "Test message from CreddyPens" }
          : { text: "Test message from CreddyPens" };
      const response = await fetch(`${apiBaseUrl()}/v1/integrations/${encodeURIComponent(item.integration_id)}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Integration test failed");
    }
  };

  const removeIntegration = async (integrationId: string) => {
    try {
      const response = await fetch(`${apiBaseUrl()}/v1/integrations/${encodeURIComponent(integrationId)}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete integration");
    }
  };

  return (
    <div className="space-y-5">
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5 space-y-3">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">INTEGRATIONS • SLACK</div>
        <input
          value={slackWebhook}
          onChange={(event) => setSlackWebhook(event.target.value)}
          placeholder="Slack webhook URL"
          className="w-full bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
        />
        <button onClick={() => void addSlack()} className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] text-xs font-bold tracking-[0.2em]">
          ADD SLACK
        </button>
      </div>

      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5 space-y-3">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">INTEGRATIONS • EMAIL</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input value={emailConfig.smtp_host} onChange={(e) => setEmailConfig((prev) => ({ ...prev, smtp_host: e.target.value }))} placeholder="SMTP host" className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm" />
          <input value={emailConfig.smtp_port} onChange={(e) => setEmailConfig((prev) => ({ ...prev, smtp_port: e.target.value }))} placeholder="SMTP port" className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm" />
          <input value={emailConfig.smtp_user} onChange={(e) => setEmailConfig((prev) => ({ ...prev, smtp_user: e.target.value }))} placeholder="SMTP user" className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm" />
          <input type="password" value={emailConfig.smtp_password} onChange={(e) => setEmailConfig((prev) => ({ ...prev, smtp_password: e.target.value }))} placeholder="SMTP password" className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm" />
          <input value={emailConfig.from_email} onChange={(e) => setEmailConfig((prev) => ({ ...prev, from_email: e.target.value }))} placeholder="From email" className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm" />
          <input value={emailConfig.test_recipient} onChange={(e) => setEmailConfig((prev) => ({ ...prev, test_recipient: e.target.value }))} placeholder="Test recipient" className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm" />
        </div>
        <button onClick={() => void addEmail()} className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] text-xs font-bold tracking-[0.2em]">
          ADD EMAIL
        </button>
      </div>

      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5 space-y-3">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">INTEGRATIONS • WEBHOOK</div>
        <input
          value={webhookConfig.url}
          onChange={(event) => setWebhookConfig((prev) => ({ ...prev, url: event.target.value }))}
          placeholder="Webhook URL"
          className="w-full bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
        />
        <input
          value={webhookConfig.headers_json}
          onChange={(event) => setWebhookConfig((prev) => ({ ...prev, headers_json: event.target.value }))}
          placeholder='Headers JSON (e.g. {"Authorization":"Bearer ..."} )'
          className="w-full bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
        />
        <button onClick={() => void addWebhook()} className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] text-xs font-bold tracking-[0.2em]">
          ADD WEBHOOK
        </button>
      </div>

      <div className="border border-[#00F0FF]/20 bg-[#0D1520]/60 p-5">
        <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-3">ACTIVE INTEGRATIONS</div>
        {loading ? <div className="text-sm text-[#00F0FF]/60">Loading...</div> : null}
        {!loading && items.length === 0 ? <div className="text-sm text-[#00F0FF]/60">No integrations configured.</div> : null}
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.integration_id} className="border border-[#00F0FF]/20 p-3 flex items-center justify-between gap-3">
              <div>
                <div className="text-sm text-white">{item.integration_type.toUpperCase()}</div>
                <div className="text-xs text-[#00F0FF]/60">{item.integration_id}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => void testIntegration(item)} className="px-3 py-2 border border-[#00F0FF]/40 text-[#00F0FF] text-xs">TEST</button>
                <button onClick={() => void removeIntegration(item.integration_id)} className="px-3 py-2 border border-red-500/40 text-red-300 text-xs">DELETE</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {error ? <div className="text-sm text-red-400">{error}</div> : null}
    </div>
  );
}
