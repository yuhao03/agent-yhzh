"use client";

import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

import type { CategoryOption, KnowledgeGraph as KnowledgeGraphData } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  ecommerce_product_copy: "#31a56f",
  ecommerce_listing: "#4478b8",
  ecommerce_marketing: "#e0972f",
  ecommerce_service: "#c25e8e",
  ecommerce_analysis: "#7a5fc7",
  general: "#6d7f76",
};

export function KnowledgeGraph({
  graph,
  categories = [],
  onSelectNode,
}: {
  graph: KnowledgeGraphData;
  categories?: CategoryOption[];
  onSelectNode?: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const onSelectRef = useRef(onSelectNode);

  useEffect(() => {
    onSelectRef.current = onSelectNode;
  }, [onSelectNode]);

  useEffect(() => {
    if (!container.current) return;

    const instance = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.knowledge_type,
            color: CATEGORY_COLORS[node.category] ?? CATEGORY_COLORS.general,
          },
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
            "background-color": "data(color)" as const,
            "border-width": 5,
            "border-color": "#eef5f0",
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
          selector: "edge[?inferred]",
          style: { "line-style": "dashed", opacity: 0.65 },
        },
      ],
    });
    instance.zoom(1);
    instance.center();
    instance.on("tap", "node", (event) => {
      onSelectRef.current?.(event.target.id() as string);
    });

    return () => instance.destroy();
  }, [graph]);

  if (!graph.nodes.length) {
    return (
      <div className="empty-state">
        <div><strong>图谱目前为空</strong>知识从零开始，发布第一条审核通过的知识后，这里会出现节点。</div>
      </div>
    );
  }

  return (
    <div className="knowledge-graph-wrap">
      <div className="knowledge-graph" ref={container} />
      <div className="graph-legend">
        {Object.entries(CATEGORY_COLORS).map(([slug, color]) => (
          <span className="graph-legend-item" key={slug}>
            <i style={{ background: color }} />
            {categories.find((category) => category.slug === slug)?.name ?? slug}
          </span>
        ))}
        <span className="graph-legend-hint">点击节点可查看知识详情</span>
      </div>
    </div>
  );
}
