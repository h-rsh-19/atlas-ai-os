"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import {
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  DatabaseZap,
  FlaskConical,
  Network,
  Route
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getLabsOverview, type LabsOverview, type LabTrack } from "@/lib/api";

const trackIcons: Record<string, ComponentType<{ className?: string }>> = {
  tiny_database_from_scratch: DatabaseZap,
  local_code_intelligence_engine: Network,
  end_to_end_ml_platform_lite: BrainCircuit
};

export default function LabsPage() {
  const [overview, setOverview] = useState<LabsOverview | null>(null);
  const [status, setStatus] = useState("Loading proof modules...");

  useEffect(() => {
    getLabsOverview()
      .then((data) => {
        setOverview(data);
        setStatus(`${data.tracks.length} proof tracks loaded`);
      })
      .catch((error) => {
        setStatus(error instanceof Error ? error.message : "Labs unavailable");
      });
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Atlas Labs
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Systems proof for a recruiter-grade AI OS
          </h1>
        </div>
        <Badge tone="teal">{status}</Badge>
      </div>

      <Panel>
        <SectionTitle
          eyebrow="Portfolio Thesis"
          title="One product, three serious engineering signals"
          action={<FlaskConical className="h-5 w-5 text-atlas-teal" />}
        />
        <p className="max-w-4xl text-sm leading-6 text-atlas-muted">
          {overview?.portfolio_pitch ||
            "Atlas combines product execution with systems fundamentals, code analysis, and ML platform thinking."}
        </p>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-3">
        {(overview?.tracks || []).map((track) => (
          <TrackPanel key={track.id} track={track} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Panel>
          <SectionTitle
            eyebrow="Tiny Database"
            title={overview?.tiny_database_demo.engine || "TinyAtlasDatabase"}
            action={<DatabaseZap className="h-5 w-5 text-atlas-blue" />}
          />
          <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
            <div className="space-y-2">
              {(overview?.tiny_database_demo.operations || []).map((operation, index) => (
                <div
                  key={operation}
                  className="flex items-center gap-3 rounded-lg border border-atlas-line bg-atlas-panelSoft p-3"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-atlas-teal/30 bg-atlas-teal/10 text-xs font-semibold text-atlas-teal">
                    {index + 1}
                  </div>
                  <p className="text-sm text-atlas-text">{operation}</p>
                </div>
              ))}
            </div>
            <div className="rounded-lg border border-atlas-line bg-atlas-bg p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-atlas-text">Query result</p>
                <Badge tone="blue">{overview?.tiny_database_demo.row_count || 0} rows</Badge>
              </div>
              <div className="space-y-2">
                {Object.entries(overview?.tiny_database_demo.query_result || {}).map(
                  ([key, value]) => (
                    <div key={key} className="grid grid-cols-[120px_1fr] gap-3 text-sm">
                      <span className="text-atlas-muted">{key}</span>
                      <span className="break-words text-atlas-text">{String(value)}</span>
                    </div>
                  )
                )}
              </div>
              <p className="mt-4 text-sm leading-6 text-atlas-muted">
                {overview?.tiny_database_demo.explanation}
              </p>
            </div>
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Next Iteration"
            title="Most valuable follow-up"
            action={<Route className="h-5 w-5 text-atlas-amber" />}
          />
          <p className="text-sm leading-6 text-atlas-muted">{overview?.next_best_iteration}</p>
          <div className="mt-5 rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
            <div className="mb-2 flex items-center gap-2">
              <ArrowRight className="h-4 w-4 text-atlas-teal" />
              <p className="text-sm font-semibold text-atlas-text">Resume angle</p>
            </div>
            <p className="text-sm leading-6 text-atlas-muted">
              Atlas now demonstrates local-first AI product architecture plus systems depth:
              storage internals, static code analysis, and an evaluation-centered ML platform loop.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function TrackPanel({ track }: { track: LabTrack }) {
  const Icon = trackIcons[track.id] || FlaskConical;
  return (
    <Panel>
      <SectionTitle
        eyebrow={track.status}
        title={track.title}
        action={<Icon className="h-5 w-5 text-atlas-teal" />}
      />
      <p className="text-sm leading-6 text-atlas-muted">{track.resume_signal}</p>
      <div className="mt-4 rounded-lg border border-atlas-line bg-atlas-bg p-3">
        <p className="mb-2 text-sm font-semibold text-atlas-text">Implementation level</p>
        <p className="text-sm leading-6 text-atlas-muted">{track.implementation_level}</p>
      </div>
      <div className="mt-4 space-y-2">
        {track.shipped.slice(0, 4).map((item) => (
          <div key={item} className="flex gap-2 text-sm leading-6">
            <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-atlas-teal" />
            <span className="text-atlas-muted">{item}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 space-y-2">
        {track.proof_artifacts.map((artifact) => (
          <div key={`${track.id}-${artifact.title}`} className="rounded-md border border-atlas-line bg-atlas-panelSoft p-3">
            <div className="mb-1 flex items-center justify-between gap-2">
              <p className="truncate text-sm font-semibold text-atlas-text">{artifact.title}</p>
              <Badge tone="blue">{artifact.kind}</Badge>
            </div>
            <p className="text-xs leading-5 text-atlas-muted">{artifact.evidence}</p>
            {artifact.path ? (
              <p className="mt-2 break-all text-[11px] text-atlas-muted">{artifact.path}</p>
            ) : null}
          </div>
        ))}
      </div>
    </Panel>
  );
}
