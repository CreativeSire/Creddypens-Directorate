"use client";

import { useEffect, useMemo, useState } from "react";
import { apiBaseUrl } from "@/lib/env";
import type { WorkflowExecuteResponse, WorkflowSchedule, WorkflowTemplate } from "@/lib/types";

type AgentOption = {
  code: string;
  name: string;
  department?: string;
};

type WorkflowStepLocal = {
  agent_code: string;
  message: string;
  use_previous_response: boolean;
};

type WorkflowRunnerProps = {
  orgId: string;
  agents: AgentOption[];
};

function makeSessionId() {
  try {
    return `wf-${crypto.randomUUID()}`;
  } catch {
    return `wf-${Date.now()}`;
  }
}

export function WorkflowRunner({ orgId, agents }: WorkflowRunnerProps) {
  const [initialMessage, setInitialMessage] = useState("");
  const [sessionId, setSessionId] = useState(makeSessionId());
  const [steps, setSteps] = useState<WorkflowStepLocal[]>([
    { agent_code: agents[0]?.code || "", message: "", use_previous_response: true },
  ]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<WorkflowExecuteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [webSearch, setWebSearch] = useState(false);
  const [deepResearch, setDeepResearch] = useState(false);
  const [outputFormat, setOutputFormat] = useState<"text" | "markdown" | "json" | "email" | "csv" | "code" | "presentation">("text");
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [scheduleName, setScheduleName] = useState("");
  const [scheduleCron, setScheduleCron] = useState("0 9 * * 1");
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([]);

  const hasAgents = agents.length > 0;
  const canRun = hasAgents && initialMessage.trim().length > 0 && steps.length > 0 && steps.every((step) => step.agent_code);

  const agentMap = useMemo(() => {
    const map = new Map<string, AgentOption>();
    for (const agent of agents) map.set(agent.code, agent);
    return map;
  }, [agents]);

  const updateStep = (index: number, patch: Partial<WorkflowStepLocal>) => {
    setSteps((prev) => prev.map((step, idx) => (idx === index ? { ...step, ...patch } : step)));
  };

  const addStep = () => {
    if (!hasAgents) return;
    setSteps((prev) => [...prev, { agent_code: agents[0]?.code || "", message: "", use_previous_response: true }]);
  };

  const removeStep = (index: number) => {
    setSteps((prev) => prev.filter((_, idx) => idx !== index));
  };

  const runWorkflow = async () => {
    if (!canRun || running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/workflows/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
        body: JSON.stringify({
          initial_message: initialMessage,
          session_id: sessionId,
          context: {
            company_name: "",
            tone: "",
            output_format: outputFormat,
            web_search: webSearch,
            deep_research: deepResearch,
            attachments: [],
            additional: { source: "workflow_runner_ui" },
          },
          steps: steps.map((step) => ({
            agent_code: step.agent_code,
            message: step.message || null,
            use_previous_response: step.use_previous_response,
          })),
        }),
      });
      const payload = (await res.json()) as WorkflowExecuteResponse | { detail?: string };
      if (!res.ok) throw new Error((payload as { detail?: string }).detail || `HTTP ${res.status}`);
      setResult(payload as WorkflowExecuteResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow failed");
    } finally {
      setRunning(false);
    }
  };

  const loadTemplatesAndSchedules = async () => {
    try {
      const [templateRes, scheduleRes] = await Promise.all([
        fetch(`${apiBaseUrl()}/v1/workflows/templates`, {
          headers: { "X-Org-Id": orgId },
        }),
        fetch(`${apiBaseUrl()}/v1/workflows/schedules`, {
          headers: { "X-Org-Id": orgId },
        }),
      ]);
      if (templateRes.ok) {
        const data = (await templateRes.json()) as WorkflowTemplate[];
        setTemplates(data);
        if (!selectedTemplateId && data[0]?.template_id) {
          setSelectedTemplateId(data[0].template_id);
        }
      }
      if (scheduleRes.ok) {
        const data = (await scheduleRes.json()) as WorkflowSchedule[];
        setSchedules(data);
      }
    } catch {
      // keep local runner usable even if template/schedule endpoints are unavailable
    }
  };

  const saveTemplate = async () => {
    const cleanName = templateName.trim();
    if (!cleanName || steps.length === 0) return;
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/workflows/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
        body: JSON.stringify({
          name: cleanName,
          description: templateDescription,
          context: {
            company_name: "",
            tone: "",
            output_format: outputFormat,
            web_search: webSearch,
            deep_research: deepResearch,
            attachments: [],
            additional: { source: "workflow_runner_ui_template" },
          },
          steps: steps.map((step) => ({
            agent_code: step.agent_code,
            message: step.message || null,
            use_previous_response: step.use_previous_response,
          })),
          is_active: true,
        }),
      });
      const payload = (await res.json()) as WorkflowTemplate | { detail?: string };
      if (!res.ok) throw new Error((payload as { detail?: string }).detail || `HTTP ${res.status}`);
      setTemplateName("");
      setTemplateDescription("");
      await loadTemplatesAndSchedules();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save template");
    }
  };

  const createSchedule = async () => {
    if (!selectedTemplateId || !scheduleName.trim() || !initialMessage.trim()) return;
    setError(null);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/workflows/templates/${selectedTemplateId}/schedules`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Org-Id": orgId },
        body: JSON.stringify({
          name: scheduleName.trim(),
          cron_expression: scheduleCron.trim(),
          timezone: "UTC",
          initial_message: initialMessage.trim(),
          is_active: true,
        }),
      });
      const payload = (await res.json()) as WorkflowSchedule | { detail?: string };
      if (!res.ok) throw new Error((payload as { detail?: string }).detail || `HTTP ${res.status}`);
      setScheduleName("");
      await loadTemplatesAndSchedules();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create recurring workflow");
    }
  };

  const runScheduleNow = async (scheduleId: string) => {
    setError(null);
    setRunning(true);
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/workflows/schedules/${scheduleId}/run`, {
        method: "POST",
        headers: { "X-Org-Id": orgId },
      });
      const payload = (await res.json()) as { workflow: WorkflowExecuteResponse; detail?: string };
      if (!res.ok) throw new Error(payload.detail || `HTTP ${res.status}`);
      setResult(payload.workflow);
      await loadTemplatesAndSchedules();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run scheduled workflow");
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    void loadTemplatesAndSchedules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  if (!hasAgents) return null;

  return (
    <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-6 mb-8">
      <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-2">{"// WORKFLOW CHAINING"}</div>
      <div className="text-white text-lg font-semibold mb-4">Run multi-agent pipelines</div>

      <textarea
        value={initialMessage}
        onChange={(e) => setInitialMessage(e.target.value)}
        placeholder="Initial task..."
        className="w-full resize-none bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-3 py-3 text-[#00F0FF] placeholder-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF] text-sm"
        rows={3}
      />

      <div className="mt-3 grid grid-cols-1 md:grid-cols-4 gap-2">
        <input
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          className="md:col-span-2 bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-3 py-2 text-xs text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]"
          placeholder="Session ID"
        />
        <select
          value={outputFormat}
          onChange={(e) => setOutputFormat(e.target.value as typeof outputFormat)}
          className="bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-3 py-2 text-xs text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]"
        >
          <option value="text">TEXT</option>
          <option value="markdown">MARKDOWN</option>
          <option value="json">JSON</option>
          <option value="email">EMAIL</option>
          <option value="csv">CSV</option>
          <option value="code">CODE</option>
          <option value="presentation">PRESENTATION</option>
        </select>
        <div className="flex items-center gap-3 text-xs text-[#00F0FF]/80">
          <label className="inline-flex items-center gap-1">
            <input type="checkbox" checked={webSearch} onChange={(e) => setWebSearch(e.target.checked)} />
            Web
          </label>
          <label className="inline-flex items-center gap-1">
            <input type="checkbox" checked={deepResearch} onChange={(e) => setDeepResearch(e.target.checked)} />
            Deep
          </label>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {steps.map((step, index) => (
          <div key={index} className="border border-[#00F0FF]/20 p-3">
            <div className="flex flex-col md:flex-row gap-2">
              <select
                value={step.agent_code}
                onChange={(e) => updateStep(index, { agent_code: e.target.value })}
                className="md:w-64 bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]"
              >
                {agents.map((agent) => (
                  <option key={agent.code} value={agent.code}>
                    {agent.code} — {agent.name}
                  </option>
                ))}
              </select>
              <input
                value={step.message}
                onChange={(e) => updateStep(index, { message: e.target.value })}
                placeholder="Optional step instruction"
                className="flex-1 bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] placeholder-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF]"
              />
              <label className="inline-flex items-center gap-1 text-xs text-[#00F0FF]/80 whitespace-nowrap px-2">
                <input
                  type="checkbox"
                  checked={step.use_previous_response}
                  onChange={(e) => updateStep(index, { use_previous_response: e.target.checked })}
                />
                Use previous output
              </label>
              {steps.length > 1 ? (
                <button
                  onClick={() => removeStep(index)}
                  className="px-3 py-2 border border-red-500/40 text-red-300 text-xs hover:bg-red-500/10"
                >
                  Remove
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex gap-2">
        <button onClick={addStep} className="px-4 py-2 border border-[#00F0FF]/30 text-[#00F0FF] text-xs hover:border-[#00F0FF]">
          + Add Step
        </button>
        <button
          onClick={runWorkflow}
          disabled={!canRun || running}
          className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] font-bold text-xs tracking-[0.2em] disabled:bg-white/10 disabled:text-white/40"
        >
          {running ? "RUNNING..." : "RUN WORKFLOW"}
        </button>
      </div>

      <div className="mt-4 border border-[#00F0FF]/20 p-3 space-y-2">
        <div className="text-xs text-[#00F0FF]/70 tracking-[0.2em]">SAVE WORKFLOW TEMPLATE</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="Template name"
            className="bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] placeholder-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF]"
          />
          <input
            value={templateDescription}
            onChange={(e) => setTemplateDescription(e.target.value)}
            placeholder="Description"
            className="md:col-span-2 bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] placeholder-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF]"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={saveTemplate}
            className="px-4 py-2 border border-[#00F0FF]/30 text-[#00F0FF] text-xs hover:border-[#00F0FF]"
          >
            Save Template
          </button>
          <button
            onClick={loadTemplatesAndSchedules}
            className="px-4 py-2 border border-[#00F0FF]/20 text-[#00F0FF]/80 text-xs hover:border-[#00F0FF]/40"
          >
            Refresh Templates
          </button>
        </div>
      </div>

      <div className="mt-4 border border-[#00F0FF]/20 p-3 space-y-2">
        <div className="text-xs text-[#00F0FF]/70 tracking-[0.2em]">RUN RECURRING WORKFLOW (CRON)</div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <select
            value={selectedTemplateId}
            onChange={(e) => setSelectedTemplateId(e.target.value)}
            className="bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] focus:outline-none focus:border-[#00F0FF]"
          >
            <option value="">Select template</option>
            {templates.map((template) => (
              <option key={template.template_id} value={template.template_id}>
                {template.name}
              </option>
            ))}
          </select>
          <input
            value={scheduleName}
            onChange={(e) => setScheduleName(e.target.value)}
            placeholder="Schedule name"
            className="bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] placeholder-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF]"
          />
          <input
            value={scheduleCron}
            onChange={(e) => setScheduleCron(e.target.value)}
            placeholder="Cron (e.g. 0 9 * * 1)"
            className="bg-[#00F0FF]/5 border border-[#00F0FF]/30 px-2 py-2 text-xs text-[#00F0FF] placeholder-[#00F0FF]/35 focus:outline-none focus:border-[#00F0FF]"
          />
          <button
            onClick={createSchedule}
            className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] font-bold text-xs tracking-[0.1em] disabled:bg-white/10 disabled:text-white/40"
            disabled={!selectedTemplateId || !scheduleName.trim() || !initialMessage.trim()}
          >
            Save Recurring
          </button>
        </div>
        {schedules.length > 0 ? (
          <div className="space-y-2">
            {schedules.slice(0, 5).map((schedule) => (
              <div key={schedule.schedule_id} className="border border-[#00F0FF]/15 px-3 py-2 text-xs text-white/80 flex items-center justify-between gap-2">
                <div>
                  <div className="text-[#00F0FF]">{schedule.name} • {schedule.cron_expression}</div>
                  <div className="text-white/60">
                    Template: {schedule.template_name} • Next: {schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : "N/A"}
                  </div>
                </div>
                <button
                  onClick={() => runScheduleNow(schedule.schedule_id)}
                  className="px-3 py-1 border border-[#00F0FF]/30 text-[#00F0FF] hover:border-[#00F0FF]"
                  disabled={running}
                >
                  Run Now
                </button>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {error ? <div className="mt-3 text-sm text-red-300">{error}</div> : null}

      {result ? (
        <div className="mt-5 border border-[#00F0FF]/20 p-4">
          <div className="text-xs text-[#00F0FF]/70 mb-2 tracking-[0.2em]">RESULT</div>
          <div className="text-xs text-[#00F0FF]/60 mb-3">
            Workflow: {result.workflow_id} • Session: {result.session_id}
          </div>
          <div className="space-y-3">
            {result.steps.map((step) => {
              const label = agentMap.get(step.agent_code);
              return (
                <div key={`${step.step_index}-${step.trace_id}`} className="border border-[#00F0FF]/15 p-3">
                  <div className="text-xs text-[#FFB800] tracking-[0.2em] mb-1">
                    STEP {step.step_index} • {step.agent_code} {label ? `(${label.name})` : ""}
                  </div>
                  <div className="text-xs text-[#00F0FF]/70 mb-2">Latency: {step.latency_ms}ms • Model: {step.model_used}</div>
                  <div className="text-xs text-white/80 whitespace-pre-wrap">{step.response}</div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 border-t border-[#00F0FF]/15 pt-3">
            <div className="text-xs text-[#00F0FF]/70 mb-1 tracking-[0.2em]">FINAL OUTPUT</div>
            <div className="text-sm text-white whitespace-pre-wrap">{result.final_response}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
