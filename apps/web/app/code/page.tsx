"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node
} from "@xyflow/react";
import { GitBranch, Network, ScanLine, SearchCode, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import {
  analyzeCodebase,
  getCodeGraph,
  getCodeRisks,
  listCodeSymbols,
  listProjects,
  type CodeGraph,
  type CodeRiskReport,
  type CodeSymbol,
  type RepoProject
} from "@/lib/api";

export default function CodeIntelPage() {
  const [projects, setProjects] = useState<RepoProject[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [symbols, setSymbols] = useState<CodeSymbol[]>([]);
  const [graph, setGraph] = useState<CodeGraph | null>(null);
  const [risks, setRisks] = useState<CodeRiskReport | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("Load a repository to analyze code.");

  const selected = projects.find((project) => project.id === selectedId) || null;

  const loadProjectAnalysis = useCallback(async (projectId: string) => {
    try {
      const [nextSymbols, nextGraph, nextRisks] = await Promise.all([
        listCodeSymbols(projectId, query),
        getCodeGraph(projectId),
        getCodeRisks(projectId)
      ]);
      setSymbols(nextSymbols);
      setGraph(nextGraph);
      setRisks(nextRisks);
      setStatus(`${nextSymbols.length} symbols loaded`);
    } catch {
      setSymbols([]);
      setGraph(null);
      setRisks(null);
      setStatus("Run analysis to generate symbols, graph, and risks.");
    }
  }, [query]);

  const refreshProjects = useCallback(async () => {
    try {
      const data = await listProjects();
      setProjects(data);
      const first = data[0]?.id || "";
      setSelectedId((current) => current || first);
      if (first) {
        await loadProjectAnalysis(first);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load projects");
    }
  }, [loadProjectAnalysis]);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  useEffect(() => {
    if (selectedId) {
      loadProjectAnalysis(selectedId);
    }
  }, [loadProjectAnalysis, selectedId]);

  async function runAnalysis() {
    if (!selectedId) {
      return;
    }
    try {
      setStatus("Analyzing repository...");
      const result = await analyzeCodebase(selectedId);
      setSymbols(result.symbols);
      setGraph(result.graph);
      setRisks(result.risk_report);
      setProjects((current) =>
        current.map((project) => (project.id === result.project.id ? result.project : project))
      );
      setStatus(
        `${result.symbols.length} symbols, ${result.graph.edges.length} graph edges, ` +
          `${result.risk_report.risks.length} risks`
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Analysis failed");
    }
  }

  async function searchSymbols() {
    if (!selectedId) {
      return;
    }
    const results = await listCodeSymbols(selectedId, query);
    setSymbols(results);
    setStatus(`${results.length} matching symbols`);
  }

  const flow = useMemo(() => toFlow(graph), [graph]);
  const topRisks = risks?.risks.slice(0, 12) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Code Intelligence
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Symbols, graph, and risk evidence
          </h1>
        </div>
        <Badge tone="blue">{status}</Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
        <Panel>
          <SectionTitle eyebrow="Repository" title="Analysis target" action={<ScanLine className="h-5 w-5 text-atlas-teal" />} />
          <div className="space-y-3">
            <select
              className="h-10 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
              aria-label="Repository"
            >
              <option value="">Select a repository</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <Button onClick={runAnalysis} className="w-full" disabled={!selectedId}>
              <Network className="h-4 w-4" />
              Analyze codebase
            </Button>
            {selected ? (
              <div className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                <div className="mb-2 flex items-center gap-2">
                  <GitBranch className="h-4 w-4 text-atlas-blue" />
                  <p className="truncate font-semibold text-atlas-text">{selected.name}</p>
                </div>
                <p className="text-sm leading-6 text-atlas-muted">{selected.summary}</p>
              </div>
            ) : (
              <p className="text-sm text-atlas-muted">
                Upload a repository ZIP on Projects, then analyze it here.
              </p>
            )}
          </div>
        </Panel>

        <Panel className="min-h-[460px]">
          <SectionTitle
            eyebrow="Graph"
            title="File, symbol, import, and call relationships"
            action={<Badge tone="teal">{graph?.parser_provider || "not analyzed"}</Badge>}
          />
          <div className="h-[390px] overflow-hidden rounded-lg border border-atlas-line bg-atlas-bg">
            {flow.nodes.length ? (
              <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView minZoom={0.2}>
                <MiniMap pannable zoomable />
                <Controls />
                <Background />
              </ReactFlow>
            ) : (
              <div className="flex h-full items-center justify-center p-6 text-center text-sm text-atlas-muted">
                Run analysis to render the dependency and symbol graph.
              </div>
            )}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <Panel>
          <SectionTitle eyebrow="Symbols" title="Searchable code map" action={<SearchCode className="h-5 w-5 text-atlas-blue" />} />
          <div className="mb-4 flex gap-2">
            <input
              className="h-10 min-w-0 flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 text-sm text-atlas-text outline-none"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search functions, classes, routes, files"
              aria-label="Search symbols"
            />
            <Button onClick={searchSymbols} disabled={!selectedId}>
              Search
            </Button>
          </div>
          <div className="max-h-[520px] overflow-auto atlas-scrollbar">
            {symbols.map((symbol) => (
              <div
                key={symbol.id}
                className="grid gap-3 border-b border-atlas-line py-3 text-sm md:grid-cols-[1fr_100px_120px]"
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-atlas-text">{symbol.name}</p>
                  <p className="truncate text-xs text-atlas-muted">
                    {symbol.file_path}:{symbol.line_start}
                  </p>
                  {symbol.evidence ? (
                    <p className="mt-1 truncate text-xs text-atlas-muted">{symbol.evidence}</p>
                  ) : null}
                </div>
                <Badge tone={symbol.kind === "route" ? "amber" : "neutral"}>{symbol.kind}</Badge>
                <span className="text-right text-atlas-muted">{symbol.language || "source"}</span>
              </div>
            ))}
            {!symbols.length ? (
              <p className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-4 text-sm text-atlas-muted">
                No symbols loaded yet.
              </p>
            ) : null}
          </div>
        </Panel>

        <Panel>
          <SectionTitle
            eyebrow="Risk Report"
            title={risks ? `${risks.risks.length} findings` : "Not generated"}
            action={<ShieldAlert className="h-5 w-5 text-atlas-amber" />}
          />
          {risks ? (
            <div className="space-y-3">
              <p className="text-sm leading-6 text-atlas-muted">{risks.summary}</p>
              {topRisks.map((risk) => (
                <div key={risk.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-atlas-text">{risk.title}</p>
                    <Badge tone={risk.severity === "high" ? "rose" : risk.severity === "medium" ? "amber" : "blue"}>
                      {risk.severity}
                    </Badge>
                  </div>
                  <p className="text-sm leading-6 text-atlas-muted">{risk.detail}</p>
                  <p className="mt-2 truncate text-xs text-atlas-muted">
                    {risk.file_path || "repo"}{risk.line ? `:${risk.line}` : ""} · {risk.evidence}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-atlas-muted">
              Run analysis to generate deterministic risks with file evidence.
            </p>
          )}
        </Panel>
      </div>
    </div>
  );
}

function toFlow(graph: CodeGraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!graph) {
    return { nodes: [], edges: [] };
  }

  const nodes = graph.nodes.slice(0, 90).map((node, index) => {
    const col = index % 5;
    const row = Math.floor(index / 5);
    const color =
      node.kind === "file"
        ? "#42d3b2"
        : node.kind === "external_module"
          ? "#7aa2ff"
          : "#f6c760";
    return {
      id: node.id,
      position: { x: col * 230, y: row * 110 },
      data: { label: `${node.kind}: ${node.label}` },
      style: {
        width: 190,
        border: `1px solid ${color}`,
        borderRadius: 8,
        background: "#111820",
        color: "#edf2f7",
        fontSize: 12,
        padding: 8
      }
    };
  });

  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .slice(0, 140)
    .map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.relation,
      animated: edge.relation === "calls",
      style: { stroke: edge.relation === "imports" ? "#7aa2ff" : "#42d3b2" }
    }));

  return { nodes, edges };
}
