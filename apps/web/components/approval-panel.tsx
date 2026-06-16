import { Check, ShieldAlert, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { approvalQueue } from "@/lib/data";

export function ApprovalPanel() {
  return (
    <Panel>
      <SectionTitle eyebrow="Approvals" title="Pending actions" />
      <div className="space-y-3">
        {approvalQueue.map((item) => (
          <div key={item.action} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
            <div className="mb-3 flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-atlas-amber" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-atlas-text">{item.action}</p>
                <p className="mt-1 truncate text-xs text-atlas-muted">
                  {item.tool} {"->"} {item.target}
                </p>
              </div>
              <Badge tone={item.risk === "Medium" ? "amber" : "teal"}>{item.risk}</Badge>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" aria-label={`Reject ${item.action}`}>
                <X className="h-4 w-4" />
                Reject
              </Button>
              <Button size="sm" variant="primary" aria-label={`Approve ${item.action}`}>
                <Check className="h-4 w-4" />
                Approve
              </Button>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
