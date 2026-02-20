"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiBaseUrl } from "@/lib/env";

type TaskItem = {
  task_id: string;
  org_id: string;
  agent_code?: string | null;
  task_title: string;
  task_description: string;
  status: "pending" | "in_progress" | "completed";
  priority: "low" | "medium" | "high" | "urgent";
  assigned_to?: string | null;
  created_by: string;
  result: string;
};

type AgentOption = { code: string; role: string };

type Props = {
  orgId: string;
};

const columns: Array<{ key: TaskItem["status"]; label: string }> = [
  { key: "pending", label: "PENDING" },
  { key: "in_progress", label: "IN PROGRESS" },
  { key: "completed", label: "COMPLETED" },
];

export function TaskBoard({ orgId }: Props) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({
    task_title: "",
    task_description: "",
    agent_code: "",
    priority: "medium",
    assigned_to: "",
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [taskRes, agentRes] = await Promise.all([
        fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/inbox`, { cache: "no-store" }),
        fetch(`${apiBaseUrl()}/v1/agents`, { cache: "no-store" }),
      ]);
      if (!taskRes.ok) throw new Error(`Task API HTTP ${taskRes.status}`);
      const taskData = (await taskRes.json()) as TaskItem[];
      setTasks(Array.isArray(taskData) ? taskData : []);
      if (agentRes.ok) {
        const agentData = (await agentRes.json()) as Array<{ code: string; role: string }>;
        setAgents(Array.isArray(agentData) ? agentData.map((item) => ({ code: item.code, role: item.role })) : []);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load inbox");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => {
    const map: Record<string, TaskItem[]> = { pending: [], in_progress: [], completed: [] };
    for (const task of tasks) map[task.status].push(task);
    return map as Record<TaskItem["status"], TaskItem[]>;
  }, [tasks]);

  const createTask = async () => {
    if (!newTask.task_title.trim()) return;
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/organizations/${encodeURIComponent(orgId)}/inbox`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTask),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setNewTask({ task_title: "", task_description: "", agent_code: "", priority: "medium", assigned_to: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    }
  };

  const updateStatus = async (taskId: string, status: TaskItem["status"]) => {
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/inbox/tasks/${encodeURIComponent(taskId)}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  };

  const assignTask = async (taskId: string, assignedTo: string) => {
    try {
      const res = await fetch(`${apiBaseUrl()}/v1/inbox/tasks/${encodeURIComponent(taskId)}/assign`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to: assignedTo }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign task");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 p-5 space-y-3">
        <div className="text-xs text-[#FFB800] tracking-[0.25em]">ORG-WIDE TASK INBOX</div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          <input
            value={newTask.task_title}
            onChange={(e) => setNewTask((prev) => ({ ...prev, task_title: e.target.value }))}
            placeholder="Task title"
            className="md:col-span-2 bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
          <input
            value={newTask.task_description}
            onChange={(e) => setNewTask((prev) => ({ ...prev, task_description: e.target.value }))}
            placeholder="Description"
            className="md:col-span-2 bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
          <button onClick={() => void createTask()} className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] text-xs font-bold tracking-[0.2em]">
            ADD TASK
          </button>
          <select
            value={newTask.agent_code}
            onChange={(e) => setNewTask((prev) => ({ ...prev, agent_code: e.target.value }))}
            className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          >
            <option value="">Agent (optional)</option>
            {agents.map((agent) => (
              <option key={agent.code} value={agent.code}>
                {agent.code} — {agent.role}
              </option>
            ))}
          </select>
          <select
            value={newTask.priority}
            onChange={(e) => setNewTask((prev) => ({ ...prev, priority: e.target.value }))}
            className="bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          >
            <option value="low">LOW</option>
            <option value="medium">MEDIUM</option>
            <option value="high">HIGH</option>
            <option value="urgent">URGENT</option>
          </select>
          <input
            value={newTask.assigned_to}
            onChange={(e) => setNewTask((prev) => ({ ...prev, assigned_to: e.target.value }))}
            placeholder="Assigned to (email/name)"
            className="md:col-span-2 bg-[#0A0F14] border border-[#00F0FF]/30 px-3 py-2 text-[#00F0FF] text-sm"
          />
        </div>
      </div>

      {error ? <div className="text-sm text-red-400">{error}</div> : null}
      {loading ? <div className="text-sm text-[#00F0FF]/60">Loading task board...</div> : null}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {columns.map((column) => (
          <div
            key={column.key}
            className="border border-[#00F0FF]/20 bg-[#0D1520]/60 p-3 min-h-[260px]"
            onDragOver={(event) => {
              event.preventDefault();
            }}
            onDrop={(event) => {
              event.preventDefault();
              const taskId = event.dataTransfer.getData("text/task-id");
              if (taskId) void updateStatus(taskId, column.key);
            }}
          >
            <div className="text-xs text-[#00F0FF] tracking-[0.25em] mb-3">
              {column.label} ({grouped[column.key].length})
            </div>
            <div className="space-y-3">
              {grouped[column.key].map((task) => (
                <div
                  key={task.task_id}
                  draggable
                  onDragStart={(event) => event.dataTransfer.setData("text/task-id", task.task_id)}
                  className="border border-[#00F0FF]/20 bg-[#0A0F14]/70 p-3 cursor-move"
                >
                  <div className="text-sm text-white">{task.task_title}</div>
                  <div className="text-xs text-[#00F0FF]/60 mt-1">{task.task_description}</div>
                  <div className="text-[11px] text-[#FFB800] mt-2">Priority: {task.priority.toUpperCase()}</div>
                  <div className="text-[11px] text-[#00F0FF]/60 mt-1">Agent: {task.agent_code || "Unassigned"}</div>
                  <div className="mt-2">
                    <input
                      defaultValue={task.assigned_to || ""}
                      onBlur={(event) => {
                        const value = event.target.value.trim();
                        if (value && value !== (task.assigned_to || "")) {
                          void assignTask(task.task_id, value);
                        }
                      }}
                      placeholder="Assign to..."
                      className="w-full bg-[#0A0F14] border border-[#00F0FF]/20 px-2 py-1 text-xs text-[#00F0FF]"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
