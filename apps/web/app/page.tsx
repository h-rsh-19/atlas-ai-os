"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Brain,
  ClipboardCheck,
  FolderGit2,
  Gauge,
  Route,
  Sparkles
} from "lucide-react";

import { MetricCard } from "@/components/metric-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { VoiceCommand } from "@/components/voice-command";
import { getDashboard, type DashboardSummary } from "@/lib/api";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [status, setStatus] = useState("Loading command center...");

  const refresh = useCallback(async () => {
    try {
      const data = await getDashboard();
      setDashboard(data);
      setStatus("Live context loaded");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Dashboard unavailable");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const metrics = dashboard?.metrics || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Command Center
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Atlas personal operating system
          </h1>
        </div>
        <Badge tone="teal">{status}</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Memories"
          value={String(metrics.memories || 0)}
          delta="source-backed context"
          icon={Brain}
        />
        <MetricCard
          label="Symbols"
          value={String(metrics.symbols || 0)}
          delta="indexed code map"
          icon={Route}
        />
        <MetricCard
          label="Approvals"
          value={String(metrics.pending_approvals || 0)}
          delta="pending gates"
          icon={ClipboardCheck}
        />
        <MetricCard
          label="Traces"
          value={String(metrics.traces || 0)}
          delta="observable runs"
          icon={Activity}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_420px]">
        <Panel>
          <SectionTitle
            eyebrow="Today"
            title="Priorities and next move"
            action={<Sparkles className="h-5 w-5 text-atlas-teal" />}
          />
          <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
            <div className="space-y-3">
              {(dashboard?.todays_priorities || []).map((priority, index) => (
                <div
                  key={priority}
                  className="flex gap-3 rounded-lg border border-atlas-line bg-atlas-panelSoft p-3"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-atlas-teal/30 bg-atlas-teal/10 text-sm font-semibold text-atlas-teal">
                    {index + 1}
                  </div>
                  <p className="text-sm leading-6 text-atlas-text">{priority}</p>
                </div>
              ))}
              {!dashboard?.todays_priorities.length ? (
                <p className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-4 text-sm text-atlas-muted">
                  Add goals to your profile to shape daily priorities.
                </p>
              ) : null}
            </div>
            <div className="rounded-lg border border-atlas-line bg-atlas-bg p-4">
              <div className="mb-3 flex items-center gap-2">
                <Gauge className="h-4 w-4 text-atlas-blue" />
                <p className="text-sm font-semibold text-atlas-text">Recommended action</p>
              </div>
              <p className="text-sm leading-6 text-atlas-muted">
                {dashboard?.next_recommended_action || "Load Atlas context to get a next step."}
              </p>
              <Button className="mt-4" variant="primary" onClick={refresh}>
                Refresh
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </Panel>

        <VoiceCommand />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Panel>
          <SectionTitle eyebrow="Projects" title="Current codebases" />
          <div className="space-y-3">
            {(dashboard?.current_projects || []).map((project) => (
              <div key={project.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center gap-2">
                  <FolderGit2 className="h-4 w-4 text-atlas-blue" />
                  <p className="truncate font-semibold text-atlas-text">{project.name}</p>
                  <Badge tone="blue">{project.status}</Badge>
                </div>
                <p className="line-clamp-3 text-sm leading-6 text-atlas-muted">{project.summary}</p>
              </div>
            ))}
            {!dashboard?.current_projects.length ? (
              <p className="text-sm text-atlas-muted">No repositories indexed yet.</p>
            ) : null}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Memory" title="Recent evidence" />
          <div className="space-y-3">
            {(dashboard?.recent_memories || []).map((memory) => (
              <div key={memory.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-semibold text-atlas-text">
                    {memory.title || memory.source_title}
                  </p>
                  <Badge tone="teal">{memory.memory_type}</Badge>
                </div>
                <p className="line-clamp-3 text-sm leading-6 text-atlas-muted">{memory.summary}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Operations" title="Approvals and weak areas" />
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-sm font-semibold text-atlas-text">Pending approvals</p>
              <div className="space-y-2">
                {(dashboard?.pending_approvals || []).map((action) => (
                  <div
                    key={action.id}
                    className="rounded-md border border-atlas-line bg-atlas-panelSoft p-3"
                  >
                    <p className="truncate text-sm text-atlas-text">{action.title}</p>
                    <p className="text-xs text-atlas-muted">{action.tool_name}</p>
                  </div>
                ))}
                {!dashboard?.pending_approvals.length ? (
                  <p className="text-sm text-atlas-muted">No pending gates.</p>
                ) : null}
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold text-atlas-text">Weak areas</p>
              <div className="flex flex-wrap gap-2">
                {(dashboard?.weak_areas || []).map((area) => (
                  <Badge key={area} tone="amber">
                    {area}
                  </Badge>
                ))}
                {!dashboard?.weak_areas.length ? <Badge>No weak areas stored</Badge> : null}
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel>
        <SectionTitle eyebrow="Traceability" title="Recent runs" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(dashboard?.recent_traces || []).map((trace) => (
            <div key={trace.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-atlas-text">
                  {trace.interaction_type}
                </p>
                <Badge tone="blue">{trace.latency_ms} ms</Badge>
              </div>
              <p className="line-clamp-2 text-sm leading-6 text-atlas-muted">
                {trace.user_input}
              </p>
              <p className="mt-2 text-xs text-atlas-muted">
                {trace.retrieved_memories.length} memories · {trace.steps.length} steps
              </p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
