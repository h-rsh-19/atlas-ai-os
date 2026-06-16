"use client";

import { useCallback, useEffect, useState } from "react";
import { Cloud, Cpu, PlugZap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  listModelProviders,
  listPlugins,
  updatePlugin,
  type ModelProvider,
  type PluginManifest
} from "@/lib/api";

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<PluginManifest[]>([]);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [status, setStatus] = useState("Loading plugin registry...");

  const refresh = useCallback(async () => {
    try {
      const [nextPlugins, nextProviders] = await Promise.all([
        listPlugins(),
        listModelProviders()
      ]);
      setPlugins(nextPlugins);
      setProviders(nextProviders);
      setStatus(`${nextPlugins.length} plugins, ${nextProviders.length} model providers`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load plugins");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function toggle(plugin: PluginManifest) {
    const updated = await updatePlugin(plugin.id, { enabled: !plugin.enabled });
    setPlugins((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    setStatus(`${updated.name} ${updated.enabled ? "enabled" : "disabled"}`);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Plugin Architecture
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Extensible tools, permission scopes, and hybrid model support
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Panel>
          <SectionTitle eyebrow="Plugins" title="Capability registry" action={<PlugZap className="h-5 w-5 text-atlas-teal" />} />
          <div className="grid gap-3 md:grid-cols-2">
            {plugins.map((plugin) => (
              <div key={plugin.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="font-semibold text-atlas-text">{plugin.name}</p>
                  <Badge tone={plugin.enabled ? "teal" : "neutral"}>
                    {plugin.enabled ? "enabled" : "disabled"}
                  </Badge>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{plugin.description}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge tone="blue">{plugin.category}</Badge>
                  {plugin.permission_scopes.map((scope) => (
                    <Badge key={scope}>{scope}</Badge>
                  ))}
                </div>
                <Button className="mt-3" onClick={() => toggle(plugin)}>
                  {plugin.enabled ? "Disable" : "Enable"}
                </Button>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Models" title="Cloud and local providers" />
          <div className="space-y-3">
            {providers.map((provider) => (
              <div key={provider.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {provider.mode === "cloud" ? (
                      <Cloud className="h-4 w-4 text-atlas-blue" />
                    ) : (
                      <Cpu className="h-4 w-4 text-atlas-teal" />
                    )}
                    <p className="text-sm font-semibold text-atlas-text">{provider.name}</p>
                  </div>
                  <Badge tone={provider.mode === "local" ? "teal" : "blue"}>{provider.mode}</Badge>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{provider.notes}</p>
                {provider.endpoint ? (
                  <p className="mt-2 truncate text-xs text-atlas-muted">{provider.endpoint}</p>
                ) : null}
                <Badge className="mt-3" tone="amber">{provider.status}</Badge>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
