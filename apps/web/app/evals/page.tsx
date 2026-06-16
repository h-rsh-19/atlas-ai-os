"use client";

import { useCallback, useEffect, useState } from "react";
import { Gauge, PlayCircle, ShieldQuestion, TestTubeDiagonal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  listEvaluationPrompts,
  listEvaluationRuns,
  runEvaluations,
  selfEvaluate,
  type EvaluationPrompt,
  type EvaluationRun,
  type SelfEvaluationResponse
} from "@/lib/api";

export default function EvalsPage() {
  const [prompts, setPrompts] = useState<EvaluationPrompt[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [selfEvalText, setSelfEvalText] = useState(
    "Atlas is grounded because it cites memory, traces tool calls, and requires approval before writes."
  );
  const [selfEval, setSelfEval] = useState<SelfEvaluationResponse | null>(null);
  const [status, setStatus] = useState("Evaluation suite ready.");

  const refresh = useCallback(async () => {
    try {
      const [nextPrompts, nextRuns] = await Promise.all([
        listEvaluationPrompts(),
        listEvaluationRuns()
      ]);
      setPrompts(nextPrompts);
      setRuns(nextRuns);
      setStatus(`${nextPrompts.length} eval prompts, ${nextRuns.length} runs`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load evals");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function runSuite() {
    try {
      setStatus("Running local evaluation suite...");
      const run = await runEvaluations();
      setRuns((current) => [run, ...current]);
      setStatus(run.summary);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Evaluation run failed");
    }
  }

  async function runSelfEval() {
    try {
      const result = await selfEvaluate({
        prompt: "Check whether this Atlas output is grounded.",
        output: selfEvalText,
        citations: [],
        source_snippets: []
      });
      setSelfEval(result);
      setStatus(`Self-check risk: ${result.hallucination_risk}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Self-evaluation failed");
    }
  }

  const latest = runs[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Evaluation Suite
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Retrieval, workflow, citation, and safety checks
          </h1>
        </div>
        <Button onClick={runSuite} variant="primary">
          <PlayCircle className="h-4 w-4" />
          Run evals
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
        <Panel>
          <SectionTitle
            eyebrow="Status"
            title="Local checkpoint"
            action={<Gauge className="h-5 w-5 text-atlas-blue" />}
          />
          <p className="text-sm leading-6 text-atlas-muted">{status}</p>
          {latest ? (
            <div className="mt-4 rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <p className="text-sm font-semibold text-atlas-text">{latest.summary}</p>
              <p className="mt-1 text-xs text-atlas-muted">
                Trace: {latest.trace_id || "not recorded"}
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-atlas-muted">
              No runs yet. Run evals after adding memory, workflows, and repo analysis.
            </p>
          )}
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Prompts"
            title="Evaluation coverage"
            action={<TestTubeDiagonal className="h-5 w-5 text-atlas-teal" />}
          />
          <div className="grid gap-3 md:grid-cols-2">
            {prompts.map((prompt) => (
              <div key={prompt.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-atlas-text">{prompt.id}</p>
                  <Badge tone="blue">{prompt.category}</Badge>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{prompt.prompt}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {prompt.success_criteria.map((criterion) => (
                    <Badge key={criterion}>{criterion}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel>
        <SectionTitle
          eyebrow="Self-Evaluation"
          title="Grounding and hallucination check"
          action={<ShieldQuestion className="h-5 w-5 text-atlas-amber" />}
        />
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div>
            <textarea
              className="min-h-40 w-full rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none"
              value={selfEvalText}
              onChange={(event) => setSelfEvalText(event.target.value)}
              aria-label="Output to self-evaluate"
            />
            <Button className="mt-3" onClick={runSelfEval}>
              <ShieldQuestion className="h-4 w-4" />
              Run self-check
            </Button>
          </div>
          <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
            {selfEval ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge tone={selfEval.grounded ? "teal" : "rose"}>
                    {selfEval.grounded ? "grounded" : "ungrounded"}
                  </Badge>
                  <Badge tone="amber">{selfEval.hallucination_risk} risk</Badge>
                </div>
                <p className="text-2xl font-semibold text-atlas-text">
                  {Math.round(selfEval.confidence * 100)}%
                </p>
                <p className="text-sm leading-6 text-atlas-muted">{selfEval.critique}</p>
                <div className="space-y-2">
                  {selfEval.verification_items.map((item) => (
                    <p key={item} className="rounded-md border border-atlas-line bg-atlas-bg p-2 text-xs text-atlas-muted">
                      {item}
                    </p>
                  ))}
                </div>
                <p className="truncate text-xs text-atlas-muted">
                  Trace: {selfEval.trace_id || "not recorded"}
                </p>
              </div>
            ) : (
              <p className="text-sm leading-6 text-atlas-muted">
                Paste or draft an output, then ask Atlas to critique grounding and verification risk.
              </p>
            )}
          </div>
        </div>
      </Panel>

      <Panel>
        <SectionTitle eyebrow="Runs" title="Latest results" />
        <div className="space-y-4">
          {runs.map((run) => (
            <div key={run.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-semibold text-atlas-text">{run.summary}</p>
                  <p className="text-xs text-atlas-muted">{new Date(run.generated_at).toLocaleString()}</p>
                </div>
                <Badge tone="teal">{run.status}</Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {run.results.map((result) => (
                  <div
                    key={String(result.id)}
                    className="rounded-md border border-atlas-line bg-atlas-bg p-3"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-semibold text-atlas-text">
                        {String(result.id)}
                      </p>
                      <Badge tone={result.status === "pass" ? "teal" : "amber"}>
                        {String(result.status)}
                      </Badge>
                    </div>
                    <p className="text-2xl font-semibold text-atlas-text">
                      {Math.round(Number(result.score || 0) * 100)}%
                    </p>
                    <p className="mt-2 text-xs leading-5 text-atlas-muted">
                      {Array.isArray(result.evidence)
                        ? result.evidence.join(", ")
                        : "No evidence recorded"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {!runs.length ? (
            <p className="text-sm text-atlas-muted">
              Evaluation history will appear after the first run.
            </p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
