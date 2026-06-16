"use client";

import { useEffect, useState } from "react";
import { FileText, FileUp, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getLatestResume, uploadResume, type MemoryItem, type ResumeProfile } from "@/lib/api";

const sectionLabels = {
  education: "Education",
  experience: "Experience",
  projects: "Projects",
  skills: "Skills",
  certifications: "Certifications",
  achievements: "Achievements"
};

export function ResumeUploader() {
  const [resume, setResume] = useState<ResumeProfile | null>(null);
  const [createdMemories, setCreatedMemories] = useState<MemoryItem[]>([]);
  const [status, setStatus] = useState("Load or upload a resume PDF");
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    getLatestResume()
      .then((data) => {
        setResume(data);
        setStatus(data ? "Latest resume loaded" : "No resume uploaded yet");
      })
      .catch((error: Error) => setStatus(error.message));
  }, []);

  async function onUpload(file: File | undefined) {
    if (!file) {
      return;
    }
    setUploading(true);
    setStatus("Parsing resume PDF...");
    try {
      const result = await uploadResume(file);
      setResume(result.resume);
      setCreatedMemories(result.created_memories);
      setStatus(`Parsed ${file.name} and created ${result.created_memories.length} memories`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Panel>
        <SectionTitle
          eyebrow="Upload"
          title="Resume PDF parser"
          action={<Badge tone={resume ? "teal" : "amber"}>{resume ? "Stored" : "Waiting"}</Badge>}
        />
        <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
          <label className="flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-atlas-line bg-atlas-panelSoft p-6 text-center transition hover:border-atlas-teal/60">
            {uploading ? (
              <Loader2 className="mb-3 h-8 w-8 animate-spin text-atlas-teal" />
            ) : (
              <FileUp className="mb-3 h-8 w-8 text-atlas-teal" />
            )}
            <span className="text-sm font-semibold text-atlas-text">Choose a PDF resume</span>
            <span className="mt-1 text-sm text-atlas-muted">
              Atlas stores raw text, structured sections, and cited resume memories.
            </span>
            <input
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(event) => onUpload(event.target.files?.[0])}
            />
          </label>

          <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-4">
            <FileText className="mb-4 h-5 w-5 text-atlas-blue" />
            <p className="text-sm text-atlas-muted">{status}</p>
            {resume ? (
              <div className="mt-4 space-y-2 text-sm">
                <p className="font-semibold text-atlas-text">{resume.filename}</p>
                <p className="text-atlas-muted">{resume.raw_text.length.toLocaleString()} extracted characters</p>
                <p className="text-atlas-muted">{new Date(resume.created_at).toLocaleString()}</p>
              </div>
            ) : null}
          </div>
        </div>
      </Panel>

      {resume ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Object.entries(sectionLabels).map(([key, label]) => {
            const values = resume.structured[key as keyof ResumeProfile["structured"]];
            return (
              <Panel key={key}>
                <SectionTitle title={label} action={<Badge tone="neutral">{values.length}</Badge>} />
                {values.length ? (
                  <div className="space-y-2">
                    {values.map((value) => (
                      <p
                        key={value}
                        className="rounded-md border border-atlas-line bg-atlas-panelSoft px-3 py-2 text-sm leading-6 text-atlas-muted"
                      >
                        {value}
                      </p>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-atlas-muted">No section evidence found yet.</p>
                )}
              </Panel>
            );
          })}
        </div>
      ) : null}

      {createdMemories.length ? (
        <Panel>
          <SectionTitle eyebrow="Memory" title="Created resume memories" />
          <div className="flex flex-wrap gap-2">
            {createdMemories.map((memory) => (
              <Badge key={memory.id} tone="blue">
                {memory.title}
              </Badge>
            ))}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
