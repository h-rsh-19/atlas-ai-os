"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, FileSearch, Play, ShieldCheck, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { sendChat, type Citation, type ProviderRun, type RetrievalHit } from "@/lib/api";

export function CommandCenter() {
  const [message, setMessage] = useState(
    "What should I learn next, based on my profile, resume, and Atlas project?"
  );
  const [context, setContext] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [retrieved, setRetrieved] = useState<RetrievalHit[]>([]);
  const [provider, setProvider] = useState<ProviderRun | null>(null);
  const [status, setStatus] = useState("Grounded chat ready");

  async function runChat() {
    setStatus("Retrieving memory...");
    try {
      const response = await sendChat(message, context);
      setAnswer(response.answer);
      setCitations(response.citations);
      setRetrieved(response.retrieved_memories);
      setProvider(response.provider || null);
      setStatus(`${response.retrieved_memories.length} memories retrieved`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Chat failed");
    }
  }

  return (
    <Panel className="min-h-[430px]">
      <SectionTitle
        eyebrow="Command"
        title="Context-aware chat"
        action={<Badge tone="teal">{status}</Badge>}
      />

      <div className="rounded-lg border border-atlas-line bg-[#0e151d] p-3">
        <textarea
          className="h-32 w-full resize-none rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none transition placeholder:text-atlas-muted focus:border-atlas-teal/50"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          aria-label="Atlas command"
        />
        <textarea
          className="mt-3 h-20 w-full resize-none rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm text-atlas-text outline-none transition placeholder:text-atlas-muted focus:border-atlas-teal/50"
          value={context}
          onChange={(event) => setContext(event.target.value)}
          placeholder="Optional work log or extra context for resume bullets"
          aria-label="Optional context"
        />

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge tone="blue">Project: Atlas</Badge>
          <Badge tone="teal">Memory: cited</Badge>
          <Badge tone="amber">Tools: gated</Badge>
          <Badge tone="neutral">Trace: on</Badge>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="primary" onClick={runChat}>
            <Play className="h-4 w-4" />
            Ask Atlas
          </Button>
          <Button>
            <FileSearch className="h-4 w-4" />
            Inspect Evidence
          </Button>
          <Button>
            <ShieldCheck className="h-4 w-4" />
            Approval Policy
          </Button>
        </div>
      </div>

      {answer ? (
        <div className="mt-4 rounded-lg border border-atlas-line bg-atlas-panelSoft p-4">
          {provider?.fallback_used ? (
            <div className="mb-3 flex items-start gap-2 rounded-md border border-atlas-amber/30 bg-atlas-amber/10 p-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-atlas-amber" />
              <div>
                <p className="text-sm font-semibold text-atlas-amber">
                  Provider failed, deterministic fallback used.
                </p>
                <p className="mt-1 text-xs leading-5 text-atlas-muted">
                  {provider.fallback_reason || `${provider.provider}:${provider.model}`}
                </p>
              </div>
            </div>
          ) : null}
          <p className="whitespace-pre-line text-sm leading-6 text-atlas-text">{answer}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {citations.map((citation) => (
              <Badge key={`${citation.source_id}-${citation.snippet}`} tone="blue">
                {citation.title}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {[
          {
            icon: Sparkles,
            label: "Reasoning",
            value: "Memory grounded",
            tone: "text-atlas-blue"
          },
          {
            icon: FileSearch,
            label: "Evidence",
            value: `${retrieved.length || 0} retrieved`,
            tone: "text-atlas-teal"
          },
          {
            icon: CheckCircle2,
            label: "Action",
            value: "1 approval queued",
            tone: "text-atlas-amber"
          }
        ].map((item) => {
          const Icon = item.icon;

          return (
            <div key={item.label} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <Icon className={`mb-3 h-5 w-5 ${item.tone}`} />
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-atlas-muted">
                {item.label}
              </p>
              <p className="mt-1 text-sm font-semibold text-atlas-text">{item.value}</p>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
