"use client";

import { useEffect, useState } from "react";
import { Activity, Clock3, DatabaseZap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { listTraces, type TraceRun } from "@/lib/api";

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceRun[]>([]);
  const [selected, setSelected] = useState<TraceRun | null>(null);
  const totalLatency = traces.reduce((sum, trace) => sum + trace.latency_ms, 0);
  const citationCount = traces.reduce(
    (sum, trace) => sum + trace.retrieved_memories.flatMap((hit) => hit.citations).length,
    0
  );

  useEffect(() => {
    listTraces().then((data) => {
      setTraces(data);
      setSelected(data[0] || null);
    });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">Traces</p>
        <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
          AI action observability
        </h1>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Panel>
          <Activity className="mb-4 h-5 w-5 text-atlas-teal" />
          <p className="text-3xl font-semibold">{traces.length}</p>
          <p className="mt-1 text-sm text-atlas-muted">Trace runs</p>
        </Panel>
        <Panel>
          <DatabaseZap className="mb-4 h-5 w-5 text-atlas-blue" />
          <p className="text-3xl font-semibold">{citationCount}</p>
          <p className="mt-1 text-sm text-atlas-muted">Citations attached</p>
        </Panel>
        <Panel>
          <Clock3 className="mb-4 h-5 w-5 text-atlas-amber" />
          <p className="text-3xl font-semibold">{totalLatency} ms</p>
          <p className="mt-1 text-sm text-atlas-muted">Total latency</p>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Audit" title="Trace log" />
          <div className="space-y-3">
            {traces.map((trace) => (
              <button
                key={trace.id}
                onClick={() => setSelected(trace)}
                className="w-full rounded-lg border border-atlas-line bg-atlas-panelSoft p-3 text-left transition hover:border-atlas-teal/50"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-semibold text-atlas-text">
                    {trace.interaction_type}
                  </p>
                  <Badge tone="teal">{Math.round(trace.confidence * 100)}%</Badge>
                </div>
                <p className="truncate text-sm text-atlas-muted">{trace.user_input}</p>
                <p className="mt-2 text-xs text-atlas-muted">{trace.latency_ms} ms</p>
              </button>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Detail" title={selected ? selected.id : "Select a trace"} />
          {selected ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <Badge tone="blue">{selected.prompt_version}</Badge>
                <Badge tone="neutral">{selected.model_used}</Badge>
                <Badge tone={selected.errors.length ? "rose" : "teal"}>
                  {selected.errors.length ? "errors" : "clean"}
                </Badge>
              </div>
              <div>
                <p className="mb-2 text-sm font-semibold text-atlas-text">Evidence</p>
                <div className="space-y-2">
                  {selected.retrieved_memories.map((hit) => (
                    <div key={hit.memory_id} className="rounded-md border border-atlas-line bg-atlas-panelSoft p-3">
                      <p className="text-sm font-semibold text-atlas-text">{hit.title}</p>
                      <p className="mt-1 text-sm leading-6 text-atlas-muted">{hit.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-sm font-semibold text-atlas-text">Steps</p>
                <div className="space-y-2">
                  {selected.steps.map((step) => (
                    <div key={step.name} className="rounded-md border border-atlas-line bg-atlas-panelSoft p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-atlas-text">{step.name}</p>
                        <Badge tone="neutral">{step.latency_ms} ms</Badge>
                      </div>
                      <pre className="mt-2 max-h-36 overflow-auto text-xs leading-5 text-atlas-muted atlas-scrollbar">
                        {JSON.stringify(step.output, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-sm font-semibold text-atlas-text">Assumptions</p>
                <div className="flex flex-wrap gap-2">
                  {selected.assumptions.map((assumption) => (
                    <Badge key={assumption} tone="amber">
                      {assumption}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-atlas-muted">Run chat or a workflow to create traces.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}
