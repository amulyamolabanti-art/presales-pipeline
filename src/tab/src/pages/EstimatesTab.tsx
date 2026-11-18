import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Dropdown, Option, Spinner } from "@fluentui/react-components";
import { api, type EffortPayload, type EffortState, type GanttPhase, type GanttTask, type InventoryRow, type MatrixRow, type Row } from "../api";
import { SectionAnalyze } from "../components/AnalyzeBar";
import { EditableGrid } from "../components/EditableGrid";
import { Expander } from "../components/Expander";
import { GanttChart, phasesToBars, tasksToBars } from "../components/Gantt";
import type { TabProps } from "./types";

const SIZES: [string, string][] = [["xs", "Very Low Complex (XS)"], ["s", "Low Complex (S)"], ["m", "Medium Complex (M)"], ["l", "High Complex (L)"], ["xl", "Complex Epic (XL)"]];

export function EstimatesTab(p: TabProps) {
  return (
    <div>
      <h1 className="tab-title">💰 Estimates</h1>
      <div className="caption">Using model <code>{p.bundle.proposal.model}</code>. Use Analyze inside each section below for Work Breakdown / Effort / Gantt.</div>
      <WorkBreakdownSection {...p} />
      <EffortSection {...p} />
      <GanttSection {...p} />
    </div>
  );
}

// ------------------------------------------------------------------ Work Breakdown

function WorkBreakdownSection({ bundle, setBundle, analyzing, runAnalyze, notify }: TabProps) {
  const field = "work_breakdown";
  const source = bundle.tables[field];
  const [rows, setRows] = useState<Row[]>(source);
  const [saving, setSaving] = useState(false);
  useEffect(() => setRows(source), [source]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.saveTable(bundle.proposal.proposal_id, field, rows);
      setBundle((b) => ({ ...b, tables: { ...b.tables, [field]: r.rows }, effort: r.effort ?? b.effort }));
      notify("Work breakdown saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Expander title="Work Breakdown" status={rows.length ? "Ready" : "Not analyzed yet"}
      right={<SectionAnalyze onAnalyze={() => void runAnalyze([field], "Work Breakdown")} busy={analyzing.has(field)} />}>
      <div className="caption">Editable work breakdown table. Use Analyze to populate from the RFP.</div>
      {rows.length > 0 && <div className="caption">{rows.length} task row(s) loaded.</div>}
      <EditableGrid
        columns={[
          { key: "phase", label: "Phase", type: "text", width: "12%" },
          { key: "task", label: "Task", type: "textarea", rows: 2, width: "16%" },
          { key: "description", label: "Description", type: "textarea", rows: 6, width: "34%" },
          { key: "activity", label: "Activity", type: "text", width: "10%" },
          { key: "pd", label: "PD", type: "text", width: 70 },
          { key: "rfp_section_reference", label: "RFP Section Reference", type: "textarea", rows: 2 },
        ]}
        rows={rows}
        onChange={setRows}
        emptyRow={() => ({ phase: "", task: "", description: "", activity: "", pd: "", rfp_section_reference: "" })}
      />
      <Button onClick={() => void save()} disabled={saving}>Save Work Breakdown</Button>
    </Expander>
  );
}

// ------------------------------------------------------------------ Effort Estimate

function EffortSection({ bundle, setBundle, analyzing, runAnalyze, notify }: TabProps) {
  const field = "effort_estimate";
  const pid = bundle.proposal.proposal_id;
  const [state, setState] = useState<EffortState>(bundle.effort.state);
  const [calc, setCalc] = useState<EffortPayload>(bundle.effort);
  const [saving, setSaving] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const first = useRef(true);

  // Reset local state when the bundle changes (Analyze, Sync, Work Breakdown save).
  useEffect(() => { setState(bundle.effort.state); setCalc(bundle.effort); first.current = true; }, [bundle.effort]);

  // Recompute formula columns (server-side maths) shortly after each edit.
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      api.computeEffort(pid, state).then(setCalc).catch((e) => notify((e as Error).message, "err"));
    }, 300);
    return () => window.clearTimeout(timer.current);
  }, [state, pid, notify]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.saveEffort(pid, state);
      setBundle((b) => ({ ...b, effort: r }));
      notify("Effort estimate saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setSaving(false);
    }
  };

  const sync = async (direction: "effort_to_wbs" | "wbs_to_effort") => {
    setSaving(true);
    try {
      const r = await api.syncEffort(pid, direction, state);
      setBundle((b) => ({ ...b, effort: r.effort, tables: { ...b.tables, work_breakdown: r.work_breakdown } }));
      notify(direction === "effort_to_wbs" ? "Effort inventory scaled to the Work Breakdown total." : "Work Breakdown PD scaled to the Effort Estimate total.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setSaving(false);
    }
  };

  const dist = state.distribution;
  const distRow = useMemo(() => Object.fromEntries(SIZES.map(([k]) => [k, Math.round((dist[k] ?? 0) * 10000) / 100])) as Record<string, number>, [dist]);

  return (
    <Expander title="Effort Estimate" status={calc.effort_total > 0 ? "Ready" : "Not analyzed yet"}
      right={<SectionAnalyze onAnalyze={() => void runAnalyze([field], "Effort Estimate")} busy={analyzing.has(field)} />}>
      <div className="caption">
        Inventory-based estimation with editable formulas. Analyze uses the Effort Estimate prompt and Work Breakdown context. Total PD is kept equal to Work Breakdown Total PD.
      </div>

      <div className="metrics">
        <div className="metric"><div className="l">Work Breakdown PD</div><div className="v">{calc.wbs_total.toFixed(2)}</div></div>
        <div className="metric"><div className="l">Effort Estimate PD</div><div className="v">{calc.effort_total.toFixed(2)}</div></div>
        <div className="metric"><div className="l">Delta</div><div className="v">{calc.delta.toFixed(2)}</div></div>
        <div className="metric"><div className="l">Status</div><div className="v">{calc.matched ? "Matched" : "Mismatch"}</div></div>
      </div>
      {!calc.matched && <div className="warn">Effort Estimate Total PD and Work Breakdown Total PD differ. Use either sync button below to reconcile.</div>}
      <div className="row" style={{ margin: "8px 0" }}>
        <Button style={{ flex: 1 }} onClick={() => void sync("effort_to_wbs")} disabled={saving}>Sync Effort Total to Work Breakdown PD</Button>
        <Button style={{ flex: 1 }} onClick={() => void sync("wbs_to_effort")} disabled={saving}>Sync Work Breakdown with Effort Estimate</Button>
      </div>

      <h5>Effort Reference Matrix</h5>
      <div className="caption">
        Editable reference model. Total PD Effort = (Discovery + Develop + Integration + Deployment) × (1 + Contingency%). Each size has DE/BI Guidance.
      </div>
      <EditableGrid<MatrixRow>
        dynamic={false}
        columns={[
          { key: "size", label: "T Shirt Size", type: "readonly", width: 60 },
          { key: "complexity", label: "Module / Epic Complexity", type: "text", width: 150 },
          { key: "discovery", label: "Discovery & Design", type: "number", width: 90 },
          { key: "develop", label: "Develop", type: "number", width: 80 },
          { key: "integration", label: "Integration / Testing", type: "number", width: 90 },
          { key: "deployment", label: "Deployment + Documentation", type: "number", width: 100 },
          { key: "contingency", label: "Contingency %", type: "number", width: 90 },
          { key: "total_pd", label: "Total PD Effort (Days)", type: "readonly", width: 90 },
          { key: "tooltip", label: "DE/BI Guidance", type: "readonly" },
        ]}
        rows={calc.state.matrix.map((m, i) => ({ ...state.matrix[i], total_pd: m.total_pd }))}
        onChange={(rows) => setState((s) => ({ ...s, matrix: rows }))}
        emptyRow={() => ({ size: "M", complexity: "", discovery: 0, develop: 0, integration: 0, deployment: 0, contingency: 0, total_pd: 0, tooltip: "" })}
      />

      <h5>Complexity Distribution %</h5>
      <EditableGrid<Record<string, number>>
        dynamic={false}
        columns={SIZES.map(([k, l]) => ({ key: k, label: `${l} %`, type: "number" as const }))}
        rows={[distRow]}
        onChange={(rows) => setState((s) => ({ ...s, distribution: Object.fromEntries(SIZES.map(([k]) => [k, Number(rows[0][k] || 0) / 100])) }))}
        emptyRow={() => ({})}
      />

      <h5>Assumed Inventory & Effort</h5>
      <div className="caption">
        Edit Item, Assumed Inventory, and Assumption. Count and Effort columns are formula-driven: Count = Inventory × Distribution%, Effort = Count × Total PD from matrix.
      </div>
      <EditableGrid<InventoryRow>
        columns={[
          { key: "item", label: "Items", type: "text", width: "30%" },
          { key: "inventory", label: "Assumed Inventory", type: "number", width: 110 },
          { key: "assumption", label: "Assumption", type: "textarea", rows: 2 },
        ]}
        rows={state.inventory_rows}
        onChange={(rows) => setState((s) => ({ ...s, inventory_rows: rows }))}
        emptyRow={() => ({ item: "", inventory: 0, assumption: "" })}
      />
      <div className="grid-wrap" style={{ marginTop: 8 }}>
        <table className="grid">
          <thead>
            <tr>
              <th>Items</th><th>Inventory</th>
              {SIZES.map(([k, l]) => <th key={k} colSpan={2}>{l} · {distRow[k]}% · {calc.summary.pd_by_size[k]} PD</th>)}
              <th>Total PD</th>
            </tr>
            <tr>
              <th /><th />
              {SIZES.map(([k]) => [<th key={k + "c"}>Count</th>, <th key={k + "e"}>Effort</th>])}
              <th />
            </tr>
          </thead>
          <tbody>
            {calc.computed_rows.map((r, i) => (
              <tr key={i}>
                <td className="ro">{r.item}</td><td className="num">{r.inventory}</td>
                {SIZES.map(([k]) => [<td key={k + "c"} className="num">{r[`${k}_count`]}</td>, <td key={k + "e"} className="num">{r[`${k}_effort`]}</td>])}
                <td className="num"><strong>{r.total_pd}</strong></td>
              </tr>
            ))}
            <tr className="total">
              <td className="ro">Total</td><td className="num">{Math.round(calc.summary.total_inventory)}</td>
              <td className="ro" colSpan={10} />
              <td className="num">{calc.effort_total.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h5>Project Summary</h5>
      <div className="summary-cols">
        <div><div><strong>Total Inventory:</strong> {Math.round(calc.summary.total_inventory)}</div><div><strong>Discovery &amp; Design:</strong> {calc.summary.discovery.toFixed(2)} PD</div></div>
        <div><div><strong>Development:</strong> {calc.summary.develop.toFixed(2)} PD</div><div><strong>Integration &amp; Testing:</strong> {calc.summary.integration.toFixed(2)} PD</div></div>
        <div><div><strong>Deployment + Documentation:</strong> {calc.summary.deployment.toFixed(2)} PD</div><div><strong>Total Project Effort:</strong> {calc.summary.total_pd.toFixed(2)} PD ({calc.summary.resource_months.toFixed(2)} Resource Months)</div></div>
      </div>
      <div style={{ marginTop: 10 }}><Button onClick={() => void save()} disabled={saving}>Save Effort Estimate</Button></div>
    </Expander>
  );
}

// ------------------------------------------------------------------ Gantt

function GanttSection({ bundle, setBundle, notify, dark }: TabProps & { dark?: boolean }) {
  const pid = bundle.proposal.proposal_id;
  const [start, setStart] = useState(bundle.gantt_settings.project_start);
  const [resources, setResources] = useState(bundle.gantt_settings.resources);
  const [built, setBuilt] = useState<{ tasks: GanttTask[]; phases: GanttPhase[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [phaseFilter, setPhaseFilter] = useState<string | null>(null);
  const [taskFilter, setTaskFilter] = useState<string | null>(null);
  useEffect(() => { setStart(bundle.gantt_settings.project_start); setResources(bundle.gantt_settings.resources); }, [bundle.gantt_settings]);
  // ?gantt=auto builds the chart on open (demo / screenshot shortcut).
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("gantt") === "auto" && !built) void analyze();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persistSettings = async (s: string, r: number) => {
    try {
      const out = await api.saveGanttSettings(pid, s, r);
      setBundle((b) => ({ ...b, gantt_settings: out }));
    } catch (e) {
      notify((e as Error).message, "err");
    }
  };

  const analyze = async () => {
    setBusy(true);
    setPhaseFilter(null);
    setTaskFilter(null);
    try {
      await persistSettings(start, resources);
      const g = await api.gantt(pid, start, resources);
      setBuilt(g);
      if (!g.tasks.length) notify("Work Breakdown table is empty. Populate it first using Work Breakdown → Analyze.", "err");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setBusy(false);
    }
  };

  const phaseOrder = useMemo(() => (built ? built.phases.map((p) => p.phase) : []), [built]);
  const phaseBars = useMemo(() => (built ? phasesToBars(built.phases) : []), [built]);
  const taskBars = useMemo(() => {
    if (!built) return [];
    const rows = phaseFilter ? built.tasks.filter((t) => t.phase === phaseFilter) : built.tasks;
    return tasksToBars(rows);
  }, [built, phaseFilter]);
  const phaseSel = useMemo(() => (phaseFilter ? new Set([phaseFilter]) : undefined), [phaseFilter]);
  const taskSel = useMemo(() => (taskFilter ? new Set([taskFilter]) : undefined), [taskFilter]);
  const onPhaseClick = useCallback((label: string) => { setPhaseFilter((cur) => (cur === label ? null : label)); setTaskFilter(null); }, []);
  const onTaskClick = useCallback((label: string, phase: string) => { setTaskFilter((cur) => (cur === label ? null : label)); setPhaseFilter(phase); }, []);

  return (
    <Expander title="Gantt Chart" status={built ? "Ready" : undefined}
      right={<Button appearance="primary" size="small" style={{ background: "var(--apa-accent)" }} onClick={(e) => { e.stopPropagation(); void analyze(); }} disabled={busy}>{busy ? <Spinner size="extra-tiny" /> : "Analyze"}</Button>}>
      <div className="caption">
        Side-by-side Gantt charts from Work Breakdown. Scheduling uses Dependencies / Parallel / Critical Path from Description, and calendar duration uses
        Number of Resources with 21 working days/month. Click a phase or task bar to correlate both charts.
      </div>
      <div className="gantt-controls">
        <label className="caption">Project start date<br />
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} onBlur={() => void persistSettings(start, resources)} style={{ font: "inherit", padding: 6 }} />
        </label>
        <label className="caption">Number of Resources<br />
          <input type="number" min={1} max={500} value={resources} onChange={(e) => setResources(Math.max(1, Number(e.target.value) || 1))} onBlur={() => void persistSettings(start, resources)} style={{ font: "inherit", padding: 6, width: 120 }} />
        </label>
      </div>

      {!built ? (
        <div className="info">Click Analyze to generate the Gantt chart from the Work Breakdown table.</div>
      ) : built.tasks.length === 0 ? null : (
        <>
          <div className="row" style={{ margin: "6px 0" }}>
            <span className="caption">Focus:</span>
            <Dropdown value={phaseFilter ?? "(All phases)"} selectedOptions={[phaseFilter ?? ""]} onOptionSelect={(_, d) => { setPhaseFilter(d.optionValue || null); setTaskFilter(null); }} style={{ minWidth: 220 }}>
              <Option value="">(All phases)</Option>
              {phaseOrder.map((p) => <Option key={p} value={p}>{p}</Option>)}
            </Dropdown>
            <Dropdown value={taskFilter ?? "(All tasks)"} selectedOptions={[taskFilter ?? ""]} onOptionSelect={(_, d) => setTaskFilter(d.optionValue || null)} style={{ minWidth: 260 }}>
              <Option value="">(All tasks)</Option>
              {taskBars.map((t) => <Option key={t.label} value={t.label}>{t.label}</Option>)}
            </Dropdown>
            {(phaseFilter || taskFilter) && <Button size="small" onClick={() => { setPhaseFilter(null); setTaskFilter(null); }}>Clear</Button>}
          </div>
          <div className="gantt-pair">
            <GanttChart title="Phases" bars={phaseBars} phaseOrder={phaseOrder} selected={phaseSel} onClick={onPhaseClick} dark={dark} />
            <GanttChart title={phaseFilter ? `Tasks · ${phaseFilter}` : "Tasks"} bars={taskBars} phaseOrder={phaseOrder} selected={taskSel} onClick={onTaskClick} dark={dark} />
          </div>
          <div className="grid-wrap" style={{ marginTop: 8 }}>
            <table className="grid">
              <thead><tr><th>#</th><th>Phase</th><th>Task</th><th>PD</th><th>Cal. days</th><th>Start</th><th>Finish</th><th>Dependencies</th><th>Parallel with</th><th>Critical</th></tr></thead>
              <tbody>
                {(phaseFilter ? built.tasks.filter((t) => t.phase === phaseFilter) : built.tasks).map((t) => (
                  <tr key={t.seq} style={{ opacity: taskFilter && taskFilter !== t.task ? 0.5 : 1 }}>
                    <td className="num">{t.seq}</td><td className="ro">{t.phase}</td><td className="ro">{t.task}</td><td className="num">{t.duration_pd}</td>
                    <td className="num">{t.calendar_days}</td><td className="ro">{t.start}</td><td className="ro">{t.finish}</td>
                    <td className="ro">{t.dependencies_text}</td><td className="ro">{t.parallel_with_text}</td><td className="ro">{t.critical_path_text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Expander>
  );
}
