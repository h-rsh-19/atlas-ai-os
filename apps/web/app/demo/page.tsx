"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, CircleDashed, RotateCcw, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getDemoFlow, type DemoFlowStatus, type DemoFlowStep } from "@/lib/api";

function toneFor(status: DemoFlowStep["status"]) {
  if (status === "completed") {
    return "teal" as const;
  }
  if (status === "ready") {
    return "blue" as const;
  }
  return "neutral" as const;
}

function iconFor(status: DemoFlowStep["status"]) {
  if (status === "completed") {
    return <CheckCircle2 className="h-4 w-4 text-atlas-teal" />;
  }
  return <CircleDashed className="h-4 w-4 text-atlas-muted" />;
}

export default function DemoPage() {
  const [flow, setFlow] = useState<DemoFlowStatus | null>(null);
  const [status, setStatus] = useState("Loading demo flow...");

  const refresh = useCallback(async () => {
    try {
      const next = await getDemoFlow();
      setFlow(next);
      setStatus(`${next.completion_percent}% complete`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Demo flow unavailable");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const nextStep = flow?.steps.find((step) => step.status !== "completed");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Golden Flow
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            One complete Atlas story
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="blue">{status}</Badge>
          <Button variant="secondary" size="sm" onClick={refresh}>
            <RotateCcw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Current mode" title={flow?.title || "Golden Atlas Demo Flow"} />
          <div className="space-y-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-xs text-atlas-muted">
                <span>Progress</span>
                <span>{flow?.completion_percent ?? 0}%</span>
              </div>
              <div className="h-2 rounded-full bg-atlas-panelSoft">
                <div
                  className="h-2 rounded-full bg-atlas-teal transition-all"
                  style={{ width: `${flow?.completion_percent ?? 0}%` }}
                />
              </div>
            </div>

            <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-atlas-teal" />
                <p className="text-sm font-semibold text-atlas-text">Mode</p>
              </div>
              <p className="text-sm leading-6 text-atlas-muted">{flow?.current_mode}</p>
            </div>

            <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-atlas-muted">
                Next
              </p>
              <p className="mt-2 text-sm font-semibold leading-6 text-atlas-text">
                {flow?.next_step || "Load the demo flow."}
              </p>
              {nextStep ? (
                <Button className="mt-3 w-full" variant="primary" asChild>
                  <Link href={nextStep.route}>
                    Open Step
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              ) : null}
            </div>
          </div>
        </Panel>

        <div className="grid gap-3 lg:grid-cols-2">
          {flow?.steps.map((step, index) => (
            <Panel key={step.id} className="min-h-40">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-atlas-line bg-atlas-bg text-xs font-semibold text-atlas-muted">
                    {index + 1}
                  </div>
                  <div className="min-w-0">
                    <div className="mb-2 flex items-center gap-2">
                      {iconFor(step.status)}
                      <h2 className="text-sm font-semibold text-atlas-text">{step.title}</h2>
                    </div>
                    <p className="text-sm leading-6 text-atlas-muted">{step.detail}</p>
                  </div>
                </div>
                <Badge tone={toneFor(step.status)}>{step.status}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <Badge tone="neutral">{step.evidence_count} evidence</Badge>
                <Button variant="ghost" size="sm" asChild>
                  <Link href={step.route}>
                    Open
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </Panel>
          ))}
        </div>
      </div>
    </div>
  );
}
