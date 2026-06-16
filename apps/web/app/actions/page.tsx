"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, FileText, ShieldCheck, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  approveAction,
  listActions,
  listArtifacts,
  proposeAction,
  rejectAction,
  type ApprovalAction,
  type ArtifactRecord
} from "@/lib/api";

const tools = [
  "create_markdown_report",
  "create_project_roadmap",
  "create_task_list",
  "export_resume_bullets",
  "generate_interview_prep_doc",
  "create_github_issue_draft",
  "generate_auto_demo_pack",
  "create_memory"
];

export default function ActionsPage() {
  const [actions, setActions] = useState<ApprovalAction[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactRecord[]>([]);
  const [toolName, setToolName] = useState(tools[0]);
  const [title, setTitle] = useState("Atlas implementation report");
  const [topic, setTopic] = useState("Atlas code intelligence and approval system");
  const [status, setStatus] = useState("Approval-gated tools are ready.");

  const pending = useMemo(
    () => actions.filter((action) => action.status === "pending"),
    [actions]
  );

  const refresh = useCallback(async () => {
    try {
      const [nextActions, nextArtifacts] = await Promise.all([listActions(), listArtifacts()]);
      setActions(nextActions);
      setArtifacts(nextArtifacts);
      setStatus(`${nextActions.length} actions, ${nextArtifacts.length} artifacts`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load actions");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function propose() {
    try {
      const action = await proposeAction({
        tool_name: toolName,
        title,
        risk_level: toolName === "create_memory" ? "medium" : "low",
        inputs: buildInputs(toolName, title, topic)
      });
      setActions((current) => [action, ...current]);
      setStatus("Action proposed. Review the preview before approving.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not propose action");
    }
  }

  async function approve(actionId: string) {
    try {
      const updated = await approveAction(actionId);
      setActions((current) =>
        current.map((action) => (action.id === updated.id ? updated : action))
      );
      await refresh();
      setStatus("Approved action executed and logged.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not approve action");
    }
  }

  async function reject(actionId: string) {
    try {
      const updated = await rejectAction(actionId);
      setActions((current) =>
        current.map((action) => (action.id === updated.id ? updated : action))
      );
      setStatus("Action rejected. No write occurred.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not reject action");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Approval System
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Tool actions with previews and audit logs
          </h1>
        </div>
        <Badge tone="amber">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle
            eyebrow="Propose"
            title="Create an approved artifact"
            action={<ShieldCheck className="h-5 w-5 text-atlas-teal" />}
          />
          <div className="space-y-3">
            <select
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={toolName}
              onChange={(event) => setToolName(event.target.value)}
              aria-label="Tool"
            >
              {tools.map((tool) => (
                <option key={tool} value={tool}>
                  {tool}
                </option>
              ))}
            </select>
            <input
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              aria-label="Title"
            />
            <textarea
              className="min-h-28 w-full rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              aria-label="Action context"
            />
            <Button onClick={propose} className="w-full">
              <FileText className="h-4 w-4" />
              Generate preview
            </Button>
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Pending"
            title={`${pending.length} approval gates`}
            action={<Badge tone="teal">no write before approval</Badge>}
          />
          <div className="space-y-3">
            {pending.map((action) => (
              <ActionCard
                key={action.id}
                action={action}
                onApprove={() => approve(action.id)}
                onReject={() => reject(action.id)}
              />
            ))}
            {!pending.length ? (
              <p className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-4 text-sm text-atlas-muted">
                No pending actions. Propose one to review the approval flow.
              </p>
            ) : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Panel>
          <SectionTitle eyebrow="Audit" title="Recent action history" />
          <div className="max-h-[520px] overflow-auto atlas-scrollbar">
            {actions.map((action) => (
              <div
                key={action.id}
                className="grid gap-3 border-b border-atlas-line py-3 text-sm md:grid-cols-[1fr_110px_120px]"
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-atlas-text">{action.title}</p>
                  <p className="truncate text-xs text-atlas-muted">{action.tool_name}</p>
                </div>
                <Badge tone={action.status === "approved" ? "teal" : action.status === "rejected" ? "rose" : "amber"}>
                  {action.status}
                </Badge>
                <span className="truncate text-right text-atlas-muted">
                  {action.trace_id || "not executed"}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Artifacts" title="Approved outputs" />
          <div className="space-y-3">
            {artifacts.map((artifact) => (
              <div key={artifact.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-semibold text-atlas-text">{artifact.title}</p>
                  <Badge tone="blue">{artifact.kind}</Badge>
                </div>
                <p className="truncate text-xs text-atlas-muted">{artifact.path}</p>
                <p className="mt-2 text-sm leading-6 text-atlas-muted">{artifact.content_preview}</p>
              </div>
            ))}
            {!artifacts.length ? (
              <p className="text-sm text-atlas-muted">
                Approved artifact-generating actions will appear here.
              </p>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function ActionCard({
  action,
  onApprove,
  onReject
}: {
  action: ApprovalAction;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold text-atlas-text">{action.title}</p>
          <p className="text-xs text-atlas-muted">{action.tool_name}</p>
        </div>
        <Badge tone={action.risk_level === "medium" ? "amber" : "blue"}>
          {action.risk_level} risk
        </Badge>
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md border border-atlas-line bg-atlas-bg p-3 text-xs leading-5 text-atlas-muted atlas-scrollbar">
        {action.preview}
      </pre>
      <div className="mt-3 flex justify-end gap-2">
        <Button variant="ghost" onClick={onReject}>
          <XCircle className="h-4 w-4" />
          Reject
        </Button>
        <Button variant="primary" onClick={onApprove}>
          <CheckCircle2 className="h-4 w-4" />
          Approve
        </Button>
      </div>
    </div>
  );
}

function buildInputs(toolName: string, title: string, topic: string): Record<string, unknown> {
  if (toolName === "create_task_list") {
    return {
      topic,
      tasks: [
        `Analyze ${topic}`,
        "Review risks and citations",
        "Create a journal entry",
        "Run the evaluation suite"
      ]
    };
  }
  if (toolName === "create_memory") {
    return {
      title,
      source_title: "Approved action",
      source_type: "approval",
      memory_type: "decision",
      content: topic,
      tags: ["approval", "decision"],
      importance: 0.75
    };
  }
  return {
    topic,
    target: "AI product engineering",
    sections: ["Summary", "Evidence", "Next Steps"],
    problem: topic,
    scope: "Implement and verify the next Atlas product slice."
  };
}
