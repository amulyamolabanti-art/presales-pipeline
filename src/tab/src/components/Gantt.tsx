import { useEffect, useRef } from "react";
import Plotly from "plotly.js-basic-dist-min";
import type { GanttPhase, GanttTask } from "../api";

type Bar = { label: string; phase: string; start: string; finish: string; duration_pd: number; extra: string };

const PALETTE = ["#1f5b7a", "#e07b39", "#2e8b57", "#8e5ea2", "#c0392b", "#17a2b8", "#b8860b", "#6c757d", "#d63384", "#20c997"];

type Props = {
  title: string;
  bars: Bar[];
  phaseOrder: string[];
  selected?: Set<string>;     // labels to keep at full opacity (others dimmed)
  onClick?: (label: string, phase: string) => void;
  dark?: boolean;
};

/** One Plotly timeline (equivalent of px.timeline in build_gantt_figure): horizontal bars from Start to Finish, colored by Phase. */
export function GanttChart({ title, bars, phaseOrder, selected, onClick, dark }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const colorOf = (phase: string) => PALETTE[Math.max(phaseOrder.indexOf(phase), 0) % PALETTE.length];
    const categories = bars.map((b) => b.label);
    const traces = phaseOrder
      .filter((p) => bars.some((b) => b.phase === p))
      .map((phase) => {
        const rows = bars.filter((b) => b.phase === phase);
        return {
          type: "bar" as const,
          orientation: "h" as const,
          name: phase,
          y: rows.map((r) => r.label),
          base: rows.map((r) => r.start),
          x: rows.map((r) => new Date(r.finish).getTime() - new Date(r.start).getTime()),
          marker: { color: colorOf(phase), opacity: rows.map((r) => (selected && selected.size ? (selected.has(r.label) ? 1 : 0.25) : 1)) },
          customdata: rows.map((r) => [r.phase, r.label, r.start, r.finish, r.duration_pd, r.extra]),
          hovertemplate: "<b>%{customdata[1]}</b><br>Phase: %{customdata[0]}<br>Start: %{customdata[2]}<br>Finish: %{customdata[3]}<br>Duration (PD): %{customdata[4]}<br>%{customdata[5]}<extra></extra>",
        };
      });
    const height = Math.min(480, Math.max(280, 26 * Math.max(bars.length, 1) + 100));
    const fg = dark ? "#e6edf2" : "#1f2d36";
    const layout = {
      title: { text: title, font: { size: 14, color: fg } },
      height,
      margin: { l: 10, r: 10, t: 50, b: 20 },
      barmode: "overlay" as const,
      xaxis: { type: "date" as const, title: { text: "Timeline" }, color: fg, gridcolor: dark ? "#2d3a44" : "#e3ebf0" },
      yaxis: { type: "category" as const, categoryorder: "array" as const, categoryarray: categories, autorange: "reversed" as const, automargin: true, color: fg },
      legend: { title: { text: "Phase" }, font: { color: fg } },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      hovermode: "closest" as const,
      dragmode: false as const,
    };
    const config = { scrollZoom: false, displaylogo: false, responsive: true, modeBarButtonsToRemove: ["zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "select2d", "lasso2d"] as never[] };
    void Plotly.react(el, traces as never, layout as never, config as never).then(() => {
      const anyEl = el as unknown as { removeAllListeners?: (ev: string) => void; on: (ev: string, cb: (d: { points: { customdata: unknown[] }[] }) => void) => void };
      anyEl.removeAllListeners?.("plotly_click");
      if (onClick) {
        anyEl.on("plotly_click", (d) => {
          const cd = d.points?.[0]?.customdata as string[] | undefined;
          if (cd) onClick(cd[1], cd[0]);
        });
      }
    });
    return () => { /* keep the element; Plotly.react reuses it */ };
  }, [bars, phaseOrder, selected, onClick, title, dark]);

  return <div ref={ref} style={{ width: "100%" }} />;
}

// eslint-disable-next-line react-refresh/only-export-components
export function tasksToBars(tasks: GanttTask[]): Bar[] {
  return tasks.map((t) => ({
    label: t.task, phase: t.phase, start: t.start, finish: t.finish, duration_pd: t.duration_pd,
    extra: `Dependencies: ${t.dependencies_text}<br>Parallel: ${t.parallel_with_text}<br>Critical path: ${t.critical_path_text}`,
  }));
}

// eslint-disable-next-line react-refresh/only-export-components
export function phasesToBars(phases: GanttPhase[]): Bar[] {
  return phases.map((p) => ({ label: p.phase, phase: p.phase, start: p.start, finish: p.finish, duration_pd: p.duration_pd, extra: `${p.task_count} task(s)` }));
}
