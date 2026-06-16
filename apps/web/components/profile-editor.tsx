"use client";

import { useEffect, useMemo, useState } from "react";
import { Save, UserRound } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getProfile, updateProfile, type UserProfile } from "@/lib/api";

const emptyProfile: UserProfile = {
  id: "default",
  name: "",
  role: "",
  current_goals: [],
  target_roles: [],
  skills: [],
  weaknesses: [],
  preferred_tech_stack: [],
  learning_priorities: []
};

const fields = [
  ["current_goals", "Current Goals"],
  ["target_roles", "Target Roles"],
  ["skills", "Skills"],
  ["weaknesses", "Weaknesses"],
  ["preferred_tech_stack", "Preferred Tech Stack"],
  ["learning_priorities", "Learning Priorities"]
] as const;

export function ProfileEditor() {
  const [profile, setProfile] = useState<UserProfile>(emptyProfile);
  const [status, setStatus] = useState("Loading profile...");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getProfile()
      .then((data) => {
        setProfile(data);
        setStatus("Profile loaded");
      })
      .catch((error: Error) => setStatus(error.message));
  }, []);

  const completion = useMemo(() => {
    const filled = [
      profile.name,
      profile.role,
      ...profile.current_goals,
      ...profile.target_roles,
      ...profile.skills,
      ...profile.weaknesses,
      ...profile.preferred_tech_stack,
      ...profile.learning_priorities
    ].filter(Boolean).length;
    return Math.min(100, Math.round((filled / 16) * 100));
  }, [profile]);

  function updateList(key: (typeof fields)[number][0], value: string) {
    setProfile((current) => ({
      ...current,
      [key]: value
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean)
    }));
  }

  async function saveProfile() {
    setSaving(true);
    try {
      const saved = await updateProfile({
        name: profile.name,
        role: profile.role,
        current_goals: profile.current_goals,
        target_roles: profile.target_roles,
        skills: profile.skills,
        weaknesses: profile.weaknesses,
        preferred_tech_stack: profile.preferred_tech_stack,
        learning_priorities: profile.learning_priorities
      });
      setProfile(saved);
      setStatus("Saved to Atlas memory");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <Panel>
        <SectionTitle
          eyebrow="Identity"
          title="Personal profile"
          action={<Badge tone="teal">{completion}% complete</Badge>}
        />
        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-medium text-atlas-muted">Name</span>
              <input
                className="h-11 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
                value={profile.name}
                onChange={(event) => setProfile({ ...profile, name: event.target.value })}
                placeholder="Your name"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-atlas-muted">Role</span>
              <input
                className="h-11 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none focus:border-atlas-teal/60"
                value={profile.role}
                onChange={(event) => setProfile({ ...profile, role: event.target.value })}
                placeholder="Student / Developer"
              />
            </label>
          </div>

          <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-4">
            <UserRound className="mb-4 h-5 w-5 text-atlas-teal" />
            <p className="text-sm leading-6 text-atlas-muted">
              Atlas turns this profile into searchable memory, so chat answers can cite your goals,
              strengths, weak spots, stack, and learning priorities.
            </p>
            <Button className="mt-4 w-full" variant="primary" onClick={saveProfile} disabled={saving}>
              <Save className="h-4 w-4" />
              {saving ? "Saving..." : "Save Profile"}
            </Button>
            <p className="mt-3 text-xs text-atlas-muted">{status}</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        {fields.map(([key, label]) => (
          <Panel key={key}>
            <SectionTitle title={label} />
            <textarea
              className="min-h-32 w-full resize-y rounded-md border border-atlas-line bg-atlas-bg p-3 text-sm leading-6 text-atlas-text outline-none focus:border-atlas-teal/60"
              value={profile[key].join("\n")}
              onChange={(event) => updateList(key, event.target.value)}
              placeholder={`One ${label.toLowerCase()} item per line`}
            />
          </Panel>
        ))}
      </div>
    </div>
  );
}
