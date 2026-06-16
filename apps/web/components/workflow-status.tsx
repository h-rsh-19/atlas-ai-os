import { ArrowRight, CircleDashed } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { activeWorkflows } from "@/lib/data";

export function WorkflowStatus() {
  return (
    <Panel>
      <SectionTitle eyebrow="Workflows" title="Active runs" />
      <div className="space-y-3">
        {activeWorkflows.map((workflow) => (
          <div key={workflow.name} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-atlas-text">{workflow.name}</p>
                <p className="mt-1 text-xs text-atlas-muted">{workflow.owner}</p>
              </div>
              <Badge tone={workflow.status === "Ready" ? "teal" : workflow.status === "Waiting" ? "amber" : "blue"}>
                {workflow.status}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-sm text-atlas-muted">
              <CircleDashed className="h-4 w-4 shrink-0 text-atlas-blue" />
              <span className="min-w-0 flex-1 truncate">{workflow.next}</span>
              <ArrowRight className="h-4 w-4 shrink-0" />
            </div>
            <p className="mt-2 text-xs text-atlas-muted">{workflow.evidence}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}
