"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import { Network, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, SectionTitle } from "@/components/ui/panel";
import { getKnowledgeGraph, type KnowledgeGraph } from "@/lib/api";

export default function KnowledgePage() {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [status, setStatus] = useState("Loading graph...");

  const refresh = useCallback(async () => {
    try {
      const data = await getKnowledgeGraph();
      setGraph(data);
      setStatus(`${data.metrics.nodes || 0} nodes, ${data.metrics.edges || 0} edges`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not load graph");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const flow = useMemo(() => toFlow(graph), [graph]);
  const topEdges = graph?.edges.slice(0, 18) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">
            Personal Knowledge Graph
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
            Skills, projects, goals, notes, repos, decisions, and concepts
          </h1>
        </div>
        <Button onClick={refresh} variant="primary">
          <RefreshCw className="h-4 w-4" />
          Rebuild
        </Button>
      </div>

      <Panel className="min-h-[560px]">
        <SectionTitle
          eyebrow="Graph"
          title="Personal context relationships"
          action={<Badge tone="teal">{status}</Badge>}
        />
        <div className="h-[480px] overflow-hidden rounded-lg border border-atlas-line bg-atlas-bg">
          {flow.nodes.length ? (
            <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView minZoom={0.2}>
              <MiniMap pannable zoomable />
              <Controls />
              <Background />
            </ReactFlow>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-atlas-muted">
              Add memory, decisions, journals, or repos to build the graph.
            </div>
          )}
        </div>
      </Panel>

      <Panel>
        <SectionTitle eyebrow="Evidence" title="Recent graph edges" action={<Network className="h-5 w-5 text-atlas-blue" />} />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {topEdges.map((edge) => (
            <div key={edge.id} className="rounded-lg border border-atlas-line bg-atlas-panelSoft p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <Badge tone="blue">{edge.relation}</Badge>
                <span className="text-xs text-atlas-muted">{Math.round(edge.confidence * 100)}%</span>
              </div>
              <p className="text-sm leading-6 text-atlas-text">
                {labelFor(graph, edge.source)} → {labelFor(graph, edge.target)}
              </p>
              <p className="mt-2 line-clamp-3 text-xs leading-5 text-atlas-muted">
                {edge.evidence}
              </p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function labelFor(graph: KnowledgeGraph | null, id: string) {
  return graph?.nodes.find((node) => node.id === id)?.label || id;
}

function toFlow(graph: KnowledgeGraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!graph) {
    return { nodes: [], edges: [] };
  }

  const nodes = graph.nodes.slice(0, 110).map((node, index) => {
    const col = index % 6;
    const row = Math.floor(index / 6);
    const color =
      node.kind === "skill"
        ? "#42d3b2"
        : node.kind === "decision"
          ? "#f6c760"
          : node.kind === "repo"
            ? "#7aa2ff"
            : "#7f8ea3";
    return {
      id: node.id,
      position: { x: col * 210, y: row * 105 },
      data: { label: `${node.kind}: ${node.label}` },
      style: {
        width: 180,
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
    .slice(0, 180)
    .map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.relation,
      style: { stroke: "#42d3b2" }
    }));
  return { nodes, edges };
}
