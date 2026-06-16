"use client";

import { useCallback, useEffect, useState } from "react";
import { GitBranch, Plus, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  createDecision,
  listDecisions,
  updateDecision,
  type DecisionEntry
} from "@/lib/api";

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<DecisionEntry[]>([]);
  const [title, setTitle] = useState("Choose local-first privacy mode");
  const [decision, setDecision] = useState("Keep Atlas usable with local files and explicit folder scopes.");
  const [alternatives, setAlternatives] = useState("Cloud-only assistant\nManual notes");
  const [tradeoffs, setTradeoffs] = useState("More user trust\nMore local implementation work");
  const [reason, setReason] = useState("Atlas should be credible on privacy, not just AI features.");
  const [tags, setTags] = useState("privacy, architecture");
  const [status, setStatus] = useState("Loading decisions...");

  const refresh = useCallback(async () => {
    try {
      const data = await listDecisions();
      setDecisions(data);
      setStatus(`${data.length} decisions stored`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load decisions");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function create() {
    const entry = await createDecision({
      title,
      decision,
      alternatives: splitLines(alternatives),
      tradeoffs: splitLines(tradeoffs),
      reason,
      tags: splitComma(tags)
    });
    setDecisions((current) => [entry, ...current]);
    setStatus("Decision stored as structured journal and memory");
  }

  async function saveResult(entry: DecisionEntry, result: string) {
    const updated = await updateDecision(entry.id, { result });
    setDecisions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    setStatus("Decision result updated");
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Decision Journal
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Technical choices, alternatives, tradeoffs, and later results
          </h1>
        </div>
        <Badge tone="amber">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="New Decision" title="Capture the reasoning" action={<GitBranch className="h-5 w-5 text-atlas-teal" />} />
          <div className="space-y-3">
            <Input value={title} onChange={setTitle} label="Title" />
            <Textarea value={decision} onChange={setDecision} label="Decision" />
            <Textarea value={alternatives} onChange={setAlternatives} label="Alternatives" />
            <Textarea value={tradeoffs} onChange={setTradeoffs} label="Tradeoffs" />
            <Textarea value={reason} onChange={setReason} label="Reason" />
            <Input value={tags} onChange={setTags} label="Tags" />
            <Button onClick={create} variant="primary" className="w-full">
              <Plus className="h-4 w-4" />
              Store decision
            </Button>
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="History" title="Decisions with evidence" />
          <div className="space-y-3">
            {decisions.map((entry) => (
              <DecisionCard key={entry.id} entry={entry} onSaveResult={saveResult} />
            ))}
            {!decisions.length ? (
              <p className="text-sm text-atlas-muted">
                Store decisions as you build Atlas to grow stronger engineering judgment.
              </p>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function DecisionCard({
  entry,
  onSaveResult
}: {
  entry: DecisionEntry;
  onSaveResult: (entry: DecisionEntry, result: string) => void;
}) {
  const [result, setResult] = useState(entry.result || "");

  return (
    <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold text-atlas-text">{entry.title}</p>
        <Badge tone="blue">{entry.memory_id ? "memory linked" : "structured"}</Badge>
      </div>
      <p className="text-sm leading-6 text-atlas-muted">{entry.decision}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <List title="Alternatives" items={entry.alternatives} />
        <List title="Tradeoffs" items={entry.tradeoffs} />
      </div>
      <p className="mt-3 text-sm leading-6 text-atlas-muted">
        <span className="font-semibold text-atlas-text">Reason:</span> {entry.reason}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {entry.tags.map((tag) => (
          <Badge key={tag}>{tag}</Badge>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          className="h-10 min-w-0 flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
          value={result}
          onChange={(event) => setResult(event.target.value)}
          placeholder="Result later"
          aria-label="Decision result"
        />
        <Button onClick={() => onSaveResult(entry, result)}>
          <Save className="h-4 w-4" />
          Save
        </Button>
      </div>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-atlas-muted">
        {title}
      </p>
      <ul className="space-y-1 text-sm text-atlas-muted">
        {items.map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}

function Input({
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
      <input
        className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Textarea({
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

function splitComma(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
