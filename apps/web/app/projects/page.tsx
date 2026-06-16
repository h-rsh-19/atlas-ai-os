"use client";

import { useCallback, useEffect, useState } from "react";
import { FileArchive, FolderGit2, Github, ScanSearch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  connectGithubRepo,
  listProjects,
  uploadRepoZip,
  type RepoProject
} from "@/lib/api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<RepoProject[]>([]);
  const [selected, setSelected] = useState<RepoProject | null>(null);
  const [githubUrl, setGithubUrl] = useState("https://github.com/example/atlas");
  const [status, setStatus] = useState("Loading projects...");

  const refresh = useCallback(async () => {
    try {
      const data = await listProjects();
      setProjects(data);
      setSelected(data[0] || null);
      setStatus(`${data.length} repos indexed`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Project load failed");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function connectGithub() {
    try {
      const project = await connectGithubRepo(githubUrl);
      setProjects((current) => [project, ...current]);
      setSelected(project);
      setStatus("GitHub repo connected");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "GitHub connect failed");
    }
  }

  async function onZip(file: File | undefined) {
    if (!file) {
      return;
    }
    try {
      setStatus("Indexing repository ZIP...");
      const project = await uploadRepoZip(file);
      setProjects((current) => [project, ...current]);
      setSelected(project);
      setStatus(`${project.file_tree.length} files indexed`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "ZIP ingestion failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">Projects</p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Repo ingestion
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Connect" title="GitHub or ZIP" action={<ScanSearch className="h-5 w-5 text-atlas-teal" />} />
          <div className="space-y-3">
            <div className="flex gap-2">
              <input
                className="h-10 min-w-0 flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
                value={githubUrl}
                onChange={(event) => setGithubUrl(event.target.value)}
                aria-label="GitHub URL"
              />
              <Button onClick={connectGithub}>
                <Github className="h-4 w-4" />
                Connect
              </Button>
            </div>
            <label className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-atlas-line bg-atlas-panelSoft p-5 text-center hover:border-atlas-teal/60">
              <FileArchive className="mb-3 h-7 w-7 text-atlas-blue" />
              <span className="text-sm font-semibold text-atlas-text">Upload local repo ZIP</span>
              <span className="mt-1 text-sm text-atlas-muted">
                Extracts tree, languages, README, dependencies, and source previews.
              </span>
              <input
                type="file"
                accept=".zip,application/zip"
                className="hidden"
                onChange={(event) => onZip(event.target.files?.[0])}
              />
            </label>
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Summary"
            title={selected ? selected.name : "No repository selected"}
            action={selected ? <Badge tone="teal">{selected.status}</Badge> : null}
          />
          {selected ? (
            <div className="space-y-4">
              <p className="text-sm leading-6 text-atlas-muted">{selected.summary}</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(selected.language_stats).map(([language, count]) => (
                  <Badge key={language} tone="blue">
                    {language}: {count}
                  </Badge>
                ))}
              </div>
              <div>
                <p className="mb-2 text-sm font-semibold text-atlas-text">Dependency files</p>
                <div className="flex flex-wrap gap-2">
                  {selected.dependency_files.map((file) => (
                    <Badge key={file} tone="amber">
                      {file}
                    </Badge>
                  ))}
                </div>
              </div>
              {selected.readme ? (
                <pre className="max-h-44 overflow-auto rounded-lg border border-atlas-line bg-atlas-bg p-3 text-xs leading-5 text-atlas-muted atlas-scrollbar">
                  {selected.readme}
                </pre>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-atlas-muted">Connect or upload a repo to inspect it.</p>
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Repos" title="Indexed projects" />
          <div className="space-y-3">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => setSelected(project)}
                className="w-full rounded-lg border border-atlas-line bg-atlas-panelSoft p-3 text-left hover:border-atlas-teal/50"
              >
                <div className="mb-2 flex items-center gap-2">
                  <FolderGit2 className="h-4 w-4 text-atlas-blue" />
                  <p className="truncate font-semibold text-atlas-text">{project.name}</p>
                </div>
                <p className="text-xs text-atlas-muted">{project.file_tree.length} files</p>
              </button>
            ))}
          </div>
        </Panel>

        <Panel>
          <SectionTitle eyebrow="File Tree" title={selected ? selected.name : "Select a repo"} />
          <div className="max-h-[520px] overflow-auto atlas-scrollbar">
            {selected?.file_tree.map((file) => (
              <div
                key={file.path}
                className="grid gap-3 border-b border-atlas-line py-2 text-sm md:grid-cols-[1fr_120px_90px]"
              >
                <span className="truncate text-atlas-text">{file.path}</span>
                <span className="text-atlas-muted">{file.language || "file"}</span>
                <span className="text-right text-atlas-muted">{file.size_bytes} B</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
