"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, Eraser, EyeOff, LockKeyhole, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  exportMemory,
  forgetMemory,
  getPrivacySettings,
  listMemories,
  redactPreview,
  updatePrivacySettings,
  type MemoryExport,
  type MemoryItem,
  type PrivacySettings
} from "@/lib/api";

export default function PrivacyPage() {
  const [settings, setSettings] = useState<PrivacySettings | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [previewText, setPreviewText] = useState("Email person@example.com with token: sk-demo1234567890");
  const [redacted, setRedacted] = useState("");
  const [exported, setExported] = useState<MemoryExport | null>(null);
  const [forgetQuery, setForgetQuery] = useState("");
  const [status, setStatus] = useState("Loading privacy controls...");

  const refresh = useCallback(async () => {
    try {
      const [nextSettings, nextMemories] = await Promise.all([
        getPrivacySettings(),
        listMemories()
      ]);
      setSettings(nextSettings);
      setMemories(nextMemories);
      setStatus("Local-first privacy controls loaded");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load privacy controls");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const exportHref = useMemo(() => {
    if (!exported) {
      return "";
    }
    return `data:application/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(exported, null, 2)
    )}`;
  }, [exported]);

  async function saveSettings() {
    if (!settings) {
      return;
    }
    const updated = await updatePrivacySettings({
      allowed_folders: settings.allowed_folders,
      blocked_folders: settings.blocked_folders,
      redaction_patterns: settings.redaction_patterns,
      local_only: settings.local_only,
      memory_export_enabled: settings.memory_export_enabled
    });
    setSettings(updated);
    setStatus("Privacy settings saved");
  }

  async function runRedaction() {
    const result = await redactPreview(previewText);
    setRedacted(result.redacted_text);
    setStatus(`${result.replacements.length} redaction rules matched`);
  }

  async function runExport() {
    const result = await exportMemory(true);
    setExported(result);
    setStatus(`${result.memories.length} memories exported with redaction`);
  }

  async function forget(payload: { memory_id?: string; query?: string }) {
    const result = await forgetMemory(payload);
    setStatus(`Forgot ${result.deleted_count} memories`);
    await refresh();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Local-First Privacy
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Permission scopes, redaction, export, and forget controls
          </h1>
        </div>
        <Badge tone="teal">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Scopes" title="Allowed and blocked folders" action={<LockKeyhole className="h-5 w-5 text-atlas-teal" />} />
          {settings ? (
            <div className="space-y-3">
              <LabeledTextarea
                label="Allowed folders"
                value={settings.allowed_folders.join("\n")}
                onChange={(value) =>
                  setSettings({ ...settings, allowed_folders: splitLines(value) })
                }
              />
              <LabeledTextarea
                label="Blocked folders"
                value={settings.blocked_folders.join("\n")}
                onChange={(value) =>
                  setSettings({ ...settings, blocked_folders: splitLines(value) })
                }
              />
              <LabeledTextarea
                label="Redaction regex patterns"
                value={settings.redaction_patterns.join("\n")}
                onChange={(value) =>
                  setSettings({ ...settings, redaction_patterns: splitLines(value) })
                }
              />
              <label className="flex items-center justify-between rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text">
                Local-only mode
                <input
                  type="checkbox"
                  checked={settings.local_only}
                  onChange={(event) =>
                    setSettings({ ...settings, local_only: event.target.checked })
                  }
                />
              </label>
              <label className="flex items-center justify-between rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text">
                Allow memory export
                <input
                  type="checkbox"
                  checked={settings.memory_export_enabled}
                  onChange={(event) =>
                    setSettings({ ...settings, memory_export_enabled: event.target.checked })
                  }
                />
              </label>
              <Button onClick={saveSettings} variant="primary" className="w-full">
                <Save className="h-4 w-4" />
                Save privacy settings
              </Button>
            </div>
          ) : null}
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Redaction" title="Sensitive data preview" action={<EyeOff className="h-5 w-5 text-atlas-blue" />} />
          <div className="grid gap-3 lg:grid-cols-2">
            <textarea
              className="min-h-52 rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none"
              value={previewText}
              onChange={(event) => setPreviewText(event.target.value)}
              aria-label="Text to redact"
            />
            <pre className="min-h-52 overflow-auto whitespace-pre-wrap rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm leading-6 text-atlas-muted atlas-scrollbar">
              {redacted || "Run redaction to preview sanitized text."}
            </pre>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button onClick={runRedaction}>
              <EyeOff className="h-4 w-4" />
              Preview redaction
            </Button>
            <Button onClick={runExport}>
              <Download className="h-4 w-4" />
              Export memory
            </Button>
            {exportHref ? (
              <a
                className="inline-flex h-10 items-center rounded-md border border-atlas-line px-3 text-sm font-semibold text-atlas-text"
                download="atlas-memory-export.json"
                href={exportHref}
              >
                Download JSON
              </a>
            ) : null}
          </div>
        </Panel>
      </div>

      <Panel>
        <SectionTitle eyebrow="Forget This" title="Delete memory with explicit user action" action={<Eraser className="h-5 w-5 text-atlas-rose" />} />
        <div className="mb-4 flex gap-2">
          <input
            className="h-10 min-w-0 flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
            value={forgetQuery}
            onChange={(event) => setForgetQuery(event.target.value)}
            placeholder="Forget memories matching a word or phrase"
            aria-label="Forget query"
          />
          <Button
            variant="primary"
            onClick={() => forget({ query: forgetQuery })}
            disabled={!forgetQuery.trim()}
          >
            Forget query
          </Button>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {memories.slice(0, 12).map((memory) => (
            <div key={memory.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-atlas-text">
                  {memory.title || memory.source_title}
                </p>
                <Badge>{memory.memory_type}</Badge>
              </div>
              <p className="line-clamp-3 text-sm leading-6 text-atlas-muted">{memory.summary}</p>
              <Button
                className="mt-3"
                variant="ghost"
                onClick={() => forget({ memory_id: memory.id })}
              >
                <Eraser className="h-4 w-4" />
                Forget
              </Button>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function LabeledTextarea({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold uppercase tracking-[0.16em] text-atlas-muted">
        {label}
      </span>
      <textarea
        className="min-h-24 w-full rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function splitLines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}
