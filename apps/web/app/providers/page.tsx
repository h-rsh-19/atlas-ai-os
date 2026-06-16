"use client";

import { useCallback, useEffect, useState } from "react";
import { Cloud, Cpu, DatabaseZap, RefreshCw, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getProviderHealth, type ProviderHealthItem, type ProviderHealthResponse } from "@/lib/api";

function toneFor(check: ProviderHealthItem) {
  if (check.active && check.reachable !== false && check.configured) {
    return "teal" as const;
  }
  if (!check.configured || check.reachable === false) {
    return "rose" as const;
  }
  return "blue" as const;
}

function iconFor(check: ProviderHealthItem) {
  if (check.provider_type === "cloud") {
    return <Cloud className="h-4 w-4 text-atlas-blue" />;
  }
  if (check.provider_type === "embedding") {
    return <DatabaseZap className="h-4 w-4 text-atlas-teal" />;
  }
  return <Cpu className="h-4 w-4 text-atlas-teal" />;
}

export default function ProvidersPage() {
  const [health, setHealth] = useState<ProviderHealthResponse | null>(null);
  const [status, setStatus] = useState("Loading provider health...");

  const refresh = useCallback(async () => {
    try {
      setStatus("Checking providers...");
      const response = await getProviderHealth();
      setHealth(response);
      setStatus(`${response.generation_provider} generation, ${response.embedding_provider} embeddings`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Provider health unavailable");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Provider Runtime
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Model and embedding health
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="blue">{status}</Badge>
          <Button variant="secondary" size="sm" onClick={refresh}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Active mode" title="Runtime selection" />
          <div className="space-y-3">
            <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-atlas-teal" />
                <p className="text-sm font-semibold text-atlas-text">Generation</p>
              </div>
              <Badge tone="teal">{health?.generation_provider || "unknown"}</Badge>
            </div>
            <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center gap-2">
                <DatabaseZap className="h-4 w-4 text-atlas-teal" />
                <p className="text-sm font-semibold text-atlas-text">Embeddings</p>
              </div>
              <Badge tone="blue">{health?.embedding_provider || "unknown"}</Badge>
            </div>
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Health checks" title="Configured providers" />
          <div className="grid gap-3 md:grid-cols-2">
            {(health?.checks || []).map((check) => (
              <div key={check.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2">
                    {iconFor(check)}
                    <div className="min-w-0">
                      <p className="text-sm font-semibold leading-5 text-atlas-text">{check.name}</p>
                      <p className="mt-1 break-all text-xs leading-5 text-atlas-muted">
                        {check.model || "No model"}
                      </p>
                    </div>
                  </div>
                  <Badge tone={toneFor(check)}>{check.status}</Badge>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{check.details}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge tone={check.active ? "teal" : "neutral"}>
                    {check.active ? "active" : "standby"}
                  </Badge>
                  <Badge tone={check.configured ? "blue" : "rose"}>
                    {check.configured ? "configured" : "missing"}
                  </Badge>
                  {check.reachable !== null && check.reachable !== undefined ? (
                    <Badge tone={check.reachable ? "teal" : "rose"}>
                      {check.reachable ? "reachable" : "unreachable"}
                    </Badge>
                  ) : null}
                  {check.latency_ms ? <Badge>{check.latency_ms}ms</Badge> : null}
                </div>
                {check.endpoint ? (
                  <p className="mt-3 truncate text-xs text-atlas-muted">{check.endpoint}</p>
                ) : null}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
