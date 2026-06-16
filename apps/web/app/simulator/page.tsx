"use client";

import { useCallback, useEffect, useState } from "react";
import { BrainCircuit, Play, Send } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  answerSimulation,
  listSimulationRuns,
  listSimulatorScenarios,
  startSimulation,
  type SimulationRun,
  type SimulatorScenario
} from "@/lib/api";

export default function SimulatorPage() {
  const [scenarios, setScenarios] = useState<SimulatorScenario[]>([]);
  const [runs, setRuns] = useState<SimulationRun[]>([]);
  const [active, setActive] = useState<SimulationRun | null>(null);
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState("Loading simulator...");

  const refresh = useCallback(async () => {
    try {
      const [nextScenarios, nextRuns] = await Promise.all([
        listSimulatorScenarios(),
        listSimulationRuns()
      ]);
      setScenarios(nextScenarios);
      setRuns(nextRuns);
      setStatus(`${nextScenarios.length} scenarios ready`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load simulator");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function start(scenarioId: string) {
    const run = await startSimulation(scenarioId);
    setActive(run);
    setRuns((current) => [run, ...current]);
    setAnswer("");
    setStatus("Scenario started");
  }

  async function submitAnswer() {
    if (!active || !answer.trim()) {
      return;
    }
    const run = await answerSimulation(active.id, answer);
    setActive(run);
    setRuns((current) => current.map((item) => (item.id === run.id ? run : item)));
    setStatus(`Answer evaluated: ${run.evaluation.score || 0}%`);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Simulator Mode
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Interviews, incidents, PR reviews, and production scenarios
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Scenarios" title="Choose a drill" action={<BrainCircuit className="h-5 w-5 text-atlas-teal" />} />
          <div className="space-y-3">
            {scenarios.map((scenario) => (
              <button
                key={scenario.id}
                onClick={() => start(scenario.id)}
                className="w-full rounded-lg border border-atlas-line bg-atlas-panelSoft p-3 text-left hover:border-atlas-teal/50"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="font-semibold text-atlas-text">{scenario.title}</p>
                  <Badge tone="blue">{scenario.scenario_type}</Badge>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{scenario.prompt}</p>
              </button>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Active Drill"
            title={active ? active.scenario.title : "Start a scenario"}
            action={<Play className="h-5 w-5 text-atlas-blue" />}
          />
          {active ? (
            <div className="space-y-4">
              <p className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3 text-sm leading-6 text-atlas-muted">
                {active.scenario.prompt}
              </p>
              <div className="flex flex-wrap gap-2">
                {active.scenario.rubric.map((item) => (
                  <Badge key={item} tone="amber">{item}</Badge>
                ))}
              </div>
              <textarea
                className="min-h-56 w-full rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder="Answer the scenario..."
                aria-label="Scenario answer"
              />
              <Button onClick={submitAnswer} variant="primary">
                <Send className="h-4 w-4" />
                Evaluate answer
              </Button>
              {Object.keys(active.evaluation).length ? (
                <EvaluationCard run={active} />
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-atlas-muted">
              Pick a scenario to practice under realistic constraints.
            </p>
          )}
        </Panel>
      </div>

      <Panel>
        <SectionTitle eyebrow="History" title="Simulation runs" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {runs.map((run) => (
            <div key={run.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-atlas-text">{run.scenario.title}</p>
                <Badge tone={run.status === "completed" ? "teal" : "amber"}>{run.status}</Badge>
              </div>
              <p className="text-sm text-atlas-muted">
                Score: {String(run.evaluation.score || "pending")}
              </p>
              <p className="mt-1 truncate text-xs text-atlas-muted">
                Trace: {run.trace_id || "not evaluated"}
              </p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function EvaluationCard({ run }: { run: SimulationRun }) {
  const rubric = Array.isArray(run.evaluation.rubric)
    ? (run.evaluation.rubric as Array<Record<string, unknown>>)
    : [];
  return (
    <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
      <div className="mb-3 flex items-center justify-between">
        <p className="font-semibold text-atlas-text">Evaluation</p>
        <Badge tone="teal">{String(run.evaluation.score)}%</Badge>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {rubric.map((item) => (
          <div key={String(item.criterion)} className="rounded-md border border-atlas-line bg-atlas-bg p-3">
            <p className="text-sm font-semibold text-atlas-text">{String(item.criterion)}</p>
            <p className="mt-1 text-sm text-atlas-muted">{String(item.feedback)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
