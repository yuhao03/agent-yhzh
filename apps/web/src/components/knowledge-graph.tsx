"use client";

import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

import type { KnowledgeGraph as KnowledgeGraphData } from "@/lib/types";

export function KnowledgeGraph({ graph }: { graph: KnowledgeGraphData }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;

    const instance = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({
          data: { id: node.id, label: node.label, type: node.knowledge_type },
        })),
        ...graph.edges.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            inferred: edge.inferred,
          },
        })),
      ],
      layout: { name: "cose", animate: false, fit: false, padding: 42 },
      minZoom: 0.45,
      maxZoom: 1.6,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-wrap": "ellipsis",
            "text-max-width": "110px",
            "font-size": 10,
            color: "#243a31",
            "text-valign": "bottom",
            "text-margin-y": 8,
            width: 36,
            height: 36,
            "background-color": "#31a56f",
            "border-width": 5,
            "border-color": "#dff4e9",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "line-color": "#a7beb2",
            "target-arrow-color": "#a7beb2",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            color: "#75857d",
            "text-background-color": "#f7faf8",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
          },
        },
        {
          selector: "edge[inferred]",
          style: { "line-style": "dashed", opacity: 0.65 },
        },
      ],
    });
    instance.zoom(1);
    instance.center();

    return () => instance.destroy();
  }, [graph]);

  if (!graph.nodes.length) {
    return (
      <div className="empty-state">
        <div><strong>图谱目前为空</strong>知识从零开始，发布第一条审核通过的知识后，这里会出现节点。</div>
      </div>
    );
  }

  return <div className="knowledge-graph" ref={container} />;
}
