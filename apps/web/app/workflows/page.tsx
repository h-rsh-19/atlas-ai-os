"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, CircleDashed, Play } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  listWorkflowDefinitions,
  listWorkflowRuns,
  runWorkflow,
  type WorkflowDefinition,
  type WorkflowRun
} from "@/lib/api";

const defaultInputs = {
  focus: "ship traceable Atlas workflows",
  target_role: "AI Product Engineer",
  question: "Tell me about a technical project.",
  time_horizon: "one week"
};

export default function WorkflowsPage() {
  const [definitions, setDefinitions] = useState<WorkflowDefinition[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selected, setSelected] = useState("plan_my_day");
  const [inputs, setInputs] = useState(JSON.stringify(defaultInputs, null, 2));
  const [status, setStatus] = useState("Loading workflows...");

  const refresh = useCallback(async () => {
    try {
      const [defs, history] = await Promise.all([listWorkflowDefinitions(), listWorkflowRuns()]);
      setDefinitions(defs);
      setRuns(history);
      setSelected(defs[0]?.name || "plan_my_day");
      setStatus(`${defs.length} workflows available`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Workflow load failed");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function execute() {
    try {
      setStatus("Running workflow...");
      const parsed = JSON.parse(inputs) as Record<string, unknown>;
      const run = await runWorkflow(selected, parsed);
      setRuns((current) => [run, ...current]);
      setStatus(`${selected} completed`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Workflow failed");
    }
  }

  const latest = runs[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Workflows
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Named AI workflows
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Run" title="Workflow launcher" />
          <div className="space-y-3">
            <select
              className="h-11 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {definitions.map((definition) => (
                <option key={definition.name} value={definition.name}>
                  {definition.name}
                </option>
              ))}
            </select>
            <textarea
              className="min-h-44 w-full resize-y rounded-md border border-atlas-line bg-atlas-bg p-3 font-mono text-xs leading-5 text-atlas-text outline-none"
              value={inputs}
              onChange={(event) => setInputs(event.target.value)}
              aria-label="Workflow inputs JSON"
            />
            <Button variant="primary" onClick={execute}>
              <Play className="h-4 w-4" />
              Run Workflow
            </Button>
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Progress" title={latest ? latest.workflow_name : "No runs yet"} />
          {latest ? (
            <div className="space-y-3">
              {latest.steps.map((step) => (
                <div key={step.name} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      {step.status === "completed" ? (
                        <CheckCircle2 className="h-4 w-4 text-atlas-teal" />
                      ) : (
                        <CircleDashed className="h-4 w-4 text-atlas-amber" />
                      )}
                      <p className="font-semibold text-atlas-text">{step.name}</p>
                    </div>
                    <Badge tone={step.status === "completed" ? "teal" : "amber"}>
                      {step.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-atlas-muted">{step.latency_ms} ms</p>
                </div>
              ))}
              <pre className="max-h-72 overflow-auto rounded-lg border border-atlas-line bg-atlas-bg p-3 text-xs leading-5 text-atlas-muted atlas-scrollbar">
                {JSON.stringify(latest.outputs, null, 2)}
              </pre>
            </div>
          ) : (
            <p className="text-sm text-atlas-muted">Run a workflow to see step progress.</p>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {definitions.map((definition) => (
          <Panel key={definition.name}>
            <SectionTitle title={definition.name} action={<Badge tone="neutral">{definition.category}</Badge>} />
            <p className="text-sm leading-6 text-atlas-muted">{definition.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {definition.steps.map((step) => (
                <Badge key={step} tone="blue">
                  {step}
                </Badge>
              ))}
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
