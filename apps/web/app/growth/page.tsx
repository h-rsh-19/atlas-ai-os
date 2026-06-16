"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, Map, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getSkillTree, getTimeline, type SkillTreeItem, type TimelineEvent } from "@/lib/api";

export default function GrowthPage() {
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [skills, setSkills] = useState<SkillTreeItem[]>([]);
  const [status, setStatus] = useState("Loading growth map...");

  const refresh = useCallback(async () => {
    try {
      const [events, tree] = await Promise.all([getTimeline(), getSkillTree()]);
      setTimeline(events);
      setSkills(tree.skills);
      setStatus(`${events.length} timeline events, ${tree.skills.length} skills`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load growth map");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const grouped = useMemo(() => {
    return skills.reduce<Record<string, SkillTreeItem[]>>((acc, skill) => {
      acc[skill.category] ||= [];
      acc[skill.category].push(skill);
      return acc;
    }, {});
  }, [skills]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Timeline Of You
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Project growth, skill evidence, and weekly momentum
          </h1>
        </div>
        <Badge tone="teal">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_440px]">
        <Panel>
          <SectionTitle eyebrow="Skill Tree" title="Evidence-backed growth map" action={<Map className="h-5 w-5 text-atlas-teal" />} />
          <div className="space-y-5">
            {Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <div className="mb-3 flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-atlas-blue" />
                  <h2 className="font-semibold text-atlas-text">{category}</h2>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {items.map((skill) => (
                    <div key={skill.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="font-semibold text-atlas-text">{skill.name}</p>
                        <Badge tone="blue">Level {skill.level}</Badge>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-atlas-bg">
                        <div
                          className="h-full rounded-full bg-atlas-teal"
                          style={{ width: `${skill.progress}%` }}
                        />
                      </div>
                      <p className="mt-2 text-xs text-atlas-muted">{skill.progress}% progress</p>
                      <p className="mt-2 text-sm leading-6 text-atlas-muted">{skill.next_action}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {skill.evidence.slice(0, 4).map((item) => (
                          <Badge key={item}>{item}</Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="Timeline" title="Recent growth events" action={<CalendarDays className="h-5 w-5 text-atlas-blue" />} />
          <div className="max-h-[760px] space-y-3 overflow-auto atlas-scrollbar">
            {timeline.map((event) => (
              <div key={event.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <Badge tone={toneFor(event.event_type)}>{event.event_type}</Badge>
                  <span className="text-xs text-atlas-muted">
                    {new Date(event.occurred_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-sm font-semibold text-atlas-text">{event.title}</p>
                <p className="mt-2 line-clamp-4 text-sm leading-6 text-atlas-muted">
                  {event.summary}
                </p>
              </div>
            ))}
            {!timeline.length ? (
              <p className="text-sm text-atlas-muted">
                Add journals, workflows, decisions, or repo analysis to build your timeline.
              </p>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function toneFor(kind: string): "teal" | "amber" | "blue" | "rose" | "neutral" {
  if (kind === "decision") {
    return "amber";
  }
  if (kind === "project") {
    return "blue";
  }
  if (kind === "workflow") {
    return "teal";
  }
  if (kind === "artifact") {
    return "rose";
  }
  return "neutral";
}
