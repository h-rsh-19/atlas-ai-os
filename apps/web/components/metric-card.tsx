import type { LucideIcon } from "lucide-react";

import { Panel } from "@/components/ui/panel";

export function MetricCard({
  label,
  value,
  delta,
  icon: Icon
}: {
  label: string;
  value: string;
  delta: string;
  icon: LucideIcon;
}) {
  return (
    <Panel className="min-h-32">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-atlas-muted">{label}</p>
          <p className="mt-3 text-3xl font-semibold text-atlas-text">{value}</p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-white/10 bg-white/5">
          <Icon className="h-5 w-5 text-atlas-teal" />
        </div>
      </div>
      <p className="mt-4 text-xs font-medium text-atlas-muted">{delta}</p>
    </Panel>
  );
}
