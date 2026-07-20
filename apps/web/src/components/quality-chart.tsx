"use client";

import * as echarts from "echarts";
import { useEffect, useRef } from "react";

import type { QualityTrend } from "@/lib/types";

export function QualityChart({ data }: { data: QualityTrend[] }) {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!element.current) return;
    const chart = echarts.init(element.current);
    chart.setOption({
      color: ["#147a52", "#e5a52c", "#5277aa"],
      tooltip: { trigger: "axis" },
      legend: { data: ["互动", "候选", "发布"], bottom: 0 },
      grid: { top: 20, left: 38, right: 18, bottom: 48 },
      xAxis: {
        type: "category",
        data: data.map((item) => item.date.slice(5)),
        axisLine: { lineStyle: { color: "#dfe8e2" } },
      },
      yAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf1ee" } } },
      series: [
        { name: "互动", type: "line", smooth: true, data: data.map((item) => item.interactions), areaStyle: { opacity: 0.08 } },
        { name: "候选", type: "bar", data: data.map((item) => item.candidates), barMaxWidth: 18 },
        { name: "发布", type: "line", smooth: true, data: data.map((item) => item.published) },
      ],
    });
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [data]);
  return <div className="quality-chart" ref={element} />;
}
