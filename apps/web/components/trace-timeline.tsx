import { Clock3 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { traceEvents } from "@/lib/data";

export function TraceTimeline() {
  return (
    <Panel>
      <SectionTitle eyebrow="Traces" title="Latest spans" />
      <div className="space-y-3">
        {traceEvents.map((event, index) => (
          <div key={event.span} className="grid grid-cols-[24px_1fr] gap-3">
            <div className="relative flex justify-center">
              <div className="mt-1 h-3 w-3 rounded-full border border-atlas-teal bg-atlas-bg" />
              {index < traceEvents.length - 1 ? (
                <div className="absolute top-5 h-[calc(100%+12px)] w-px bg-atlas-line" />
              ) : null}
            </div>
            <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-atlas-text">{event.span}</p>
                <Badge tone="neutral">{event.kind}</Badge>
              </div>
              <p className="text-sm text-atlas-muted">{event.detail}</p>
              <div className="mt-3 flex items-center gap-2 text-xs text-atlas-muted">
                <Clock3 className="h-3.5 w-3.5" />
                <span>{event.actor}</span>
                <span>{event.latency}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
