import { useEffect, useState } from "react";
import { Button, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, DialogTrigger, Spinner } from "@fluentui/react-components";
import { api, type Row } from "../api";
import { AnalyzeBar, SectionAnalyze } from "../components/AnalyzeBar";
import { EditableGrid } from "../components/EditableGrid";
import { Expander } from "../components/Expander";
import type { TabProps } from "./types";

export function ArchitectureTab(p: TabProps) {
  const { meta, bundle, analyzing, runAnalyze } = p;
  const fields = meta.tab_fields.architecture;
  const busy = fields.some((f) => analyzing.has(f));
  const [dialogImg, setDialogImg] = useState<{ title: string; url: string } | null>(null);

  return (
    <div>
      <h1 className="tab-title">🏗️ Architecture</h1>
      <AnalyzeBar onAnalyze={() => void runAnalyze(fields, "Architecture")} busy={busy} model={bundle.proposal.model} />

      <ArchitectureField {...p} label="Current State Architecture" field="current_state_architecture" onDiagram={setDialogImg} />
      <ArchitectureField {...p} label="Target State Architecture" field="target_architecture" onDiagram={setDialogImg} />
      <MappingSection {...p} />
      <RolesSection {...p} />

      <Dialog open={!!dialogImg} onOpenChange={(_, d) => !d.open && setDialogImg(null)}>
        <DialogSurface style={{ maxWidth: 1100 }}>
          <DialogBody>
            <DialogTitle>{dialogImg?.title}</DialogTitle>
            <DialogContent>{dialogImg && <img src={dialogImg.url} alt={dialogImg.title} style={{ width: "100%" }} />}</DialogContent>
            <DialogActions><DialogTrigger disableButtonEnhancement><Button appearance="primary">Close</Button></DialogTrigger></DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}

type FieldProps = TabProps & { label: string; field: string; onDiagram: (d: { title: string; url: string }) => void };

/** Blue label block with a Diagram button + text area (render_architecture_section_with_diagram). */
function ArchitectureField({ bundle, setBundle, label, field, onDiagram, notify }: FieldProps) {
  const section = bundle.sections[field];
  const [text, setText] = useState(section.content);
  const [generating, setGenerating] = useState(false);
  useEffect(() => setText(section.content), [section.content]);

  const saveIfChanged = async () => {
    if (text === section.content) return;
    try {
      const s = await api.saveSection(bundle.proposal.proposal_id, field, text);
      setBundle((b) => ({ ...b, sections: { ...b.sections, [field]: s } }));
    } catch (e) {
      notify((e as Error).message, "err");
    }
  };

  const diagram = async () => {
    setGenerating(true);
    try {
      await saveIfChanged();
      const r = await api.diagram(bundle.proposal.proposal_id, field);
      setBundle((b) => ({ ...b, diagrams: { ...b.diagrams, [field]: r.url } }));
      onDiagram({ title: `${label} — stored diagram`, url: r.url });
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="field-row">
      <div>
        <div className="field-label">{label}</div>
        <Button className="diagram-btn" style={{ width: "100%" }} onClick={() => void diagram()} disabled={generating}>
          {generating ? <Spinner size="tiny" /> : "Diagram"}
        </Button>
      </div>
      <textarea style={{ height: 280 }} value={text} onChange={(e) => setText(e.target.value)} onBlur={() => void saveIfChanged()} placeholder={`Run Analyze to generate ${label}.`} />
    </div>
  );
}

function MappingSection({ bundle, setBundle, analyzing, runAnalyze, notify }: TabProps) {
  const field = "architecture_mapping";
  const source = bundle.tables[field];
  const [rows, setRows] = useState<Row[]>(source);
  const [saving, setSaving] = useState(false);
  useEffect(() => setRows(source), [source]);
  const cur = bundle.diagrams.current_state_architecture;
  const tgt = bundle.diagrams.target_architecture;

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.saveTable(bundle.proposal.proposal_id, field, rows);
      setBundle((b) => ({ ...b, tables: { ...b.tables, [field]: r.rows } }));
      notify("Architecture mapping saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Expander title="Current State to Target State Architecture Mapping" status={rows.length ? "Ready" : "Not analyzed yet"} defaultOpen>
      <div className="caption">
        Compare the last generated diagrams side by side (kept until you click Diagram again), then review/edit the technology mapping matrix.
        Use Architecture Analyze (or Mapping Analyze) after Current/Target architecture text is ready.
      </div>
      <div className="diagram-pair">
        <div>
          <strong>Current State Architecture</strong>
          {cur ? <img src={cur} alt="Current State Architecture" /> : <div className="info">No Current State diagram yet. Click Diagram under Current State Architecture.</div>}
        </div>
        <div>
          <strong>Target State Architecture</strong>
          {tgt ? <img src={tgt} alt="Target State Architecture" /> : <div className="info">No Target State diagram yet. Click Diagram under Target State Architecture.</div>}
        </div>
      </div>
      <div className="row">
        <div>
          <h5>Mapping Matrix</h5>
          <div className="caption">Columns: Current State (technology stack), Target State (technology stack), Remark (Migrating / Replacing / Retaining / Discarding / etc.).</div>
        </div>
        <span className="spacer" />
        <SectionAnalyze onAnalyze={() => void runAnalyze([field], "Mapping")} busy={analyzing.has(field)} />
      </div>
      {rows.length > 0 && <div className="caption">{rows.length} mapping row(s) loaded.</div>}
      <EditableGrid
        columns={[
          { key: "current_state", label: "Current State", type: "textarea", rows: 3, width: "28%" },
          { key: "target_state", label: "Target State", type: "textarea", rows: 3, width: "28%" },
          { key: "remark", label: "Remark", type: "textarea", rows: 3 },
        ]}
        rows={rows}
        onChange={setRows}
        emptyRow={() => ({ current_state: "", target_state: "", remark: "" })}
      />
      <Button onClick={() => void save()} disabled={saving}>Save Architecture Mapping</Button>
    </Expander>
  );
}

function RolesSection({ bundle, setBundle, analyzing, runAnalyze, notify }: TabProps) {
  const field = "roles";
  const source = bundle.tables[field];
  const [rows, setRows] = useState<Row[]>(source);
  const [saving, setSaving] = useState(false);
  useEffect(() => setRows(source), [source]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.saveTable(bundle.proposal.proposal_id, field, rows);
      setBundle((b) => ({ ...b, tables: { ...b.tables, [field]: r.rows } }));
      notify("Roles saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Expander title="Roles" status={rows.length ? "Ready" : "Not analyzed yet"} defaultOpen>
      <div className="caption">
        Delivery roles required for this RFP. Analyze uses In Scope, Target State, Architecture, Architecture Mapping, Assumptions, Dependencies, and related sections.
        Use Architecture Analyze or the Roles Analyze button.
      </div>
      <div className="row">
        <div>
          <h5>Role Matrix</h5>
          <div className="caption">Columns: Role | Exp | Skills | Description</div>
        </div>
        <span className="spacer" />
        <SectionAnalyze onAnalyze={() => void runAnalyze([field], "Roles")} busy={analyzing.has(field)} />
      </div>
      {rows.length > 0 && <div className="caption">{rows.length} role row(s) loaded.</div>}
      <EditableGrid
        columns={[
          { key: "role", label: "Role", type: "text", width: "18%" },
          { key: "experience", label: "Exp", type: "text", width: 90 },
          { key: "skills", label: "Skills", type: "textarea", rows: 3, width: "30%" },
          { key: "description", label: "Description", type: "textarea", rows: 3 },
        ]}
        rows={rows}
        onChange={setRows}
        emptyRow={() => ({ role: "", experience: "", skills: "", description: "" })}
      />
      <Button onClick={() => void save()} disabled={saving}>Save Roles</Button>
    </Expander>
  );
}
