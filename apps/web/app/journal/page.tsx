"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpenCheck, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  createJournalEntry,
  getJournalSummary,
  listJournalEntries,
  type JournalEntry,
  type JournalSummary
} from "@/lib/api";

export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [summary, setSummary] = useState<JournalSummary | null>(null);
  const [status, setStatus] = useState("Loading journal...");
  const [form, setForm] = useState({
    built: "Implemented trace logging and workflow progress for Atlas.",
    problems: "Needed to keep traces useful without adding opaque autonomy.",
    decisions: "Stored every AI run with retrieved memories, prompt version, steps, and assumptions.",
    skills_used: "FastAPI, TypeScript, SQLite, AI product design",
    next_tasks: "Add repo ingestion, improve career workflows"
  });

  const refresh = useCallback(async () => {
    const [entryData, summaryData] = await Promise.all([listJournalEntries(), getJournalSummary()]);
    setEntries(entryData);
    setSummary(summaryData);
    setStatus(`${entryData.length} journal entries`);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function saveEntry() {
    try {
      await createJournalEntry({
        built: form.built,
        problems: form.problems,
        decisions: form.decisions,
        skills_used: splitLines(form.skills_used),
        next_tasks: splitLines(form.next_tasks)
      });
      await refresh();
      setStatus("Journal saved and converted into memory");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Journal save failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">Journal</p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Project progress intelligence
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Daily Log" title="Capture progress" />
          <div className="space-y-3">
            {(["built", "problems", "decisions"] as const).map((key) => (
              <textarea
                key={key}
                className="min-h-24 w-full resize-y rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm leading-6 text-atlas-text outline-none"
                value={form[key]}
                onChange={(event) => setForm({ ...form, [key]: event.target.value })}
                aria-label={key}
              />
            ))}
            <input
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={form.skills_used}
              onChange={(event) => setForm({ ...form, skills_used: event.target.value })}
              aria-label="Skills used"
            />
            <input
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={form.next_tasks}
              onChange={(event) => setForm({ ...form, next_tasks: event.target.value })}
              aria-label="Next tasks"
            />
            <Button variant="primary" onClick={saveEntry}>
              <Plus className="h-4 w-4" />
              Save Journal Entry
            </Button>
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Atlas Output"
            title="Weekly summary, bullets, stories, insights"
            action={<BookOpenCheck className="h-5 w-5 text-atlas-teal" />}
          />
          {summary ? (
            <div className="space-y-4">
              <p className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3 text-sm leading-6 text-atlas-muted">
                {summary.weekly_summary}
              </p>
              <SummaryList title="Resume Bullets" values={summary.resume_bullets} />
              <SummaryList title="Interview Stories" values={summary.interview_stories} />
              <SummaryList title="Learning Insights" values={summary.learning_insights} />
            </div>
          ) : (
            <p className="text-sm text-atlas-muted">Save an entry to generate progress artifacts.</p>
          )}
        </Panel>
      </div>

      <Panel>
        <SectionTitle eyebrow="History" title="Saved journal entries" />
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="font-semibold text-atlas-text">{entry.entry_date}</p>
                <Badge tone="teal">{entry.skills_used.length} skills</Badge>
              </div>
              <p className="text-sm leading-6 text-atlas-muted">{entry.built}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function SummaryList({ title, values }: { title: string; values: string[] }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold text-atlas-text">{title}</p>
      <div className="space-y-2">
        {values.map((value) => (
          <p
            key={value}
            className="rounded-md border border-atlas-line bg-atlas-panelSoft px-3 py-2 text-sm leading-6 text-atlas-muted"
          >
            {value}
          </p>
        ))}
      </div>
    </div>
  );
}

function splitLines(value: string) {
  return value
    .split(/,|\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}
