import { Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { settingsSections } from "@/lib/data";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Settings
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            System policy
          </h1>
        </div>
        <Button variant="primary">
          <Save className="h-4 w-4" />
          Save
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {settingsSections.map((section) => {
          const Icon = section.icon;

          return (
            <Panel key={section.title}>
              <SectionTitle
                title={section.title}
                action={
                  <div className="flex h-10 w-10 items-center justify-center rounded-md border border-white/10 bg-white/5">
                    <Icon className="h-5 w-5 text-atlas-teal" />
                  </div>
                }
              />
              <div className="space-y-2">
                {section.rows.map((row) => (
                  <div
                    key={row}
                    className="flex items-center justify-between gap-3 rounded-md border border-atlas-line bg-atlas-panelSoft px-3 py-2"
                  >
                    <span className="text-sm text-atlas-muted">{row}</span>
                    <Badge tone="neutral">Set</Badge>
                  </div>
                ))}
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
