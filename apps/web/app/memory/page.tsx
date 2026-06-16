"use client";

import { useEffect, useState } from "react";
import { Database, FileCheck2, Plus, Search, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  createMemory,
  deleteMemory,
  listMemories,
  searchMemory,
  type MemoryItem,
  type RetrievalHit
} from "@/lib/api";

const memoryTypes = ["resume", "project", "note", "goal", "decision", "learning", "daily log", "interview story"];

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [hits, setHits] = useState<RetrievalHit[]>([]);
  const [status, setStatus] = useState("Loading memory...");
  const [query, setQuery] = useState("What should I learn next?");
  const [form, setForm] = useState({
    title: "Learning checkpoint",
    source_title: "Manual note",
    source_type: "note",
    memory_type: "learning",
    content: "I need to strengthen pgvector retrieval, AI workflow evaluation, and system design storytelling.",
    tags: "learning, retrieval, interviews",
    importance: 0.75
  });

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    try {
      const data = await listMemories();
      setMemories(data);
      setStatus(`${data.length} memories loaded`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Memory load failed");
    }
  }

  async function addMemory() {
    try {
      await createMemory({
        title: form.title,
        source_title: form.source_title,
        source_type: form.source_type,
        memory_type: form.memory_type,
        content: form.content,
        tags: form.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        importance: form.importance
      });
      await refresh();
      setStatus("Memory created with source metadata and embedding");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Create failed");
    }
  }

  async function removeMemory(memoryId: string) {
    try {
      await deleteMemory(memoryId);
      await refresh();
      setStatus("Memory deleted");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Delete failed");
    }
  }

  async function runSearch() {
    try {
      const result = await searchMemory(query);
      setHits(result.hits);
      setStatus(`${result.hits.length} cited retrieval hits`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Search failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">Memory</p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Source-backed context
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Create" title="Add memory" action={<Database className="h-5 w-5 text-atlas-teal" />} />
          <div className="space-y-3">
            <input
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="Memory title"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
                value={form.source_title}
                onChange={(event) => setForm({ ...form, source_title: event.target.value })}
                placeholder="Source title"
              />
              <select
                className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
                value={form.memory_type}
                onChange={(event) => setForm({ ...form, memory_type: event.target.value })}
              >
                {memoryTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
            <textarea
              className="min-h-32 w-full resize-y rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm leading-6 text-atlas-text outline-none focus:border-atlas-teal/60"
              value={form.content}
              onChange={(event) => setForm({ ...form, content: event.target.value })}
              placeholder="Memory content"
            />
            <input
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
              value={form.tags}
              onChange={(event) => setForm({ ...form, tags: event.target.value })}
              placeholder="Comma-separated tags"
            />
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={form.importance}
                onChange={(event) => setForm({ ...form, importance: Number(event.target.value) })}
                className="w-full"
                aria-label="Memory importance"
              />
              <Badge tone="teal">{Math.round(form.importance * 100)}%</Badge>
            </div>
            <Button variant="primary" onClick={addMemory}>
              <Plus className="h-4 w-4" />
              Create Memory
            </Button>
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Retrieve" title="Vector search with citations" />
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="h-10 min-w-0 flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask Atlas to retrieve relevant memory"
            />
            <Button onClick={runSearch}>
              <Search className="h-4 w-4" />
              Search
            </Button>
          </div>

          <div className="mt-4 space-y-3">
            {hits.map((hit) => (
              <div key={hit.memory_id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <p className="font-semibold text-atlas-text">{hit.title}</p>
                  <Badge tone="teal">{hit.score.toFixed(2)}</Badge>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{hit.summary}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {hit.citations.map((citation) => (
                    <Badge key={`${hit.memory_id}-${citation.source_id}`} tone="blue">
                      {citation.title}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel>
        <SectionTitle eyebrow="Vault" title="Memory records" action={<Badge tone="blue">{memories.length} indexed</Badge>} />
        <div className="overflow-x-auto atlas-scrollbar">
          <table className="w-full min-w-[860px] border-separate border-spacing-0">
            <thead>
              <tr className="text-left text-xs uppercase tracking-[0.16em] text-atlas-muted">
                <th className="border-b border-atlas-line pb-3 font-semibold">Memory</th>
                <th className="border-b border-atlas-line pb-3 font-semibold">Source</th>
                <th className="border-b border-atlas-line pb-3 font-semibold">Tags</th>
                <th className="border-b border-atlas-line pb-3 font-semibold">Importance</th>
                <th className="border-b border-atlas-line pb-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {memories.map((row) => (
                <tr key={row.id}>
                  <td className="border-b border-atlas-line py-4 pr-4 align-top">
                    <div className="flex gap-3">
                      <FileCheck2 className="mt-1 h-5 w-5 shrink-0 text-atlas-teal" />
                      <div>
                        <p className="font-semibold text-atlas-text">{row.title || row.source_title}</p>
                        <p className="mt-1 max-w-xl text-sm leading-6 text-atlas-muted">{row.summary}</p>
                      </div>
                    </div>
                  </td>
                  <td className="border-b border-atlas-line py-4 pr-4 align-top">
                    <Badge tone="neutral">{row.memory_type}</Badge>
                    <p className="mt-2 text-sm text-atlas-muted">{row.source_title}</p>
                  </td>
                  <td className="border-b border-atlas-line py-4 pr-4 align-top">
                    <div className="flex flex-wrap gap-2">
                      {row.tags.map((tag) => (
                        <Badge key={tag} tone="blue">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="border-b border-atlas-line py-4 align-top">
                    <Badge tone="teal">{Math.round(row.importance * 100)}%</Badge>
                  </td>
                  <td className="border-b border-atlas-line py-4 align-top">
                    <Button size="icon" variant="ghost" onClick={() => removeMemory(row.id)} aria-label={`Delete ${row.title}`}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
