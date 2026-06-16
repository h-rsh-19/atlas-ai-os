import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { contextStack } from "@/lib/data";

export function ContextStack() {
  return (
    <Panel>
      <SectionTitle eyebrow="Memory" title="Context stack" />
      <div className="space-y-3">
        {contextStack.map((item) => (
          <div key={item.title} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="h-4 w-4 shrink-0 text-atlas-teal" />
                <p className="truncate text-sm font-semibold text-atlas-text">{item.title}</p>
              </div>
              <Badge tone="neutral">{item.confidence}</Badge>
            </div>
            <p className="mb-2 text-xs font-medium text-atlas-blue">{item.type}</p>
            <p className="text-sm leading-6 text-atlas-muted">{item.snippet}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}
