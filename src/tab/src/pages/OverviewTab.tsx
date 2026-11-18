import { useEffect, useState } from "react";
import { Button } from "@fluentui/react-components";
import { api, type Row } from "../api";
import { AnalyzeBar, SectionAnalyze } from "../components/AnalyzeBar";
import { EditableGrid } from "../components/EditableGrid";
import { Expander } from "../components/Expander";
import { SectionPanel } from "../components/SectionPanel";
import type { TabProps } from "./types";

export function OverviewTab(p: TabProps) {
  const { meta, bundle, analyzing, runAnalyze } = p;
  const fields = meta.tab_fields.overview;
  const busy = fields.some((f) => analyzing.has(f));

  return (
    <div>
      <h1 className="tab-title">📊 Overview</h1>
      <AnalyzeBar onAnalyze={() => void runAnalyze(fields, "Overview")} busy={busy} model={bundle.proposal.model} />

      <SectionPanel label="Document Score" section={bundle.sections.document_score} />
      <ClarificationGrid {...p} />
      <SectionPanel label="Summary" section={bundle.sections.summary} />
      <SectionPanel label="Current State" section={bundle.sections.current_state} />
      <SectionPanel label="Target State" section={bundle.sections.target_state} />
      <SectionPanel label="Pain Areas" section={bundle.sections.pain_areas} />
      <SectionPanel label="COE to be involved" section={bundle.sections.coe_involved} />
    </div>
  );
}

function ClarificationGrid({ meta, bundle, setBundle, analyzing, runAnalyze, notify }: TabProps) {
  const field = "clarification_questions";
  const source = bundle.tables[field];
  const [rows, setRows] = useState<Row[]>(source);
  const [saving, setSaving] = useState(false);
  useEffect(() => setRows(source), [source]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.saveTable(bundle.proposal.proposal_id, field, rows);
      setBundle((b) => ({ ...b, tables: { ...b.tables, [field]: r.rows } }));
      notify("Clarification questions saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Expander title="Questions for Clarifications" status={rows.length ? "Ready" : "Not analyzed yet"} defaultOpen
      right={<SectionAnalyze onAnalyze={() => void runAnalyze([field], "Questions for Clarifications")} busy={analyzing.has(field)} />}>
      <div className="caption">
        Editable clarification log. Use Overview Analyze to populate from the RFP. Categories include Volumetrics plus Commercial, Current State, Target State, and more.
      </div>
      {rows.length > 0 && <div className="caption">{rows.length} question row(s) loaded.</div>}
      <EditableGrid
        columns={[
          { key: "number", label: "#", type: "readonly", width: 40 },
          { key: "category", label: "Category", type: "select", options: meta.clarification_categories, width: 150 },
          { key: "question", label: "Question", type: "textarea", rows: 4 },
          { key: "why_asking", label: "Why We're Asking", type: "textarea", rows: 4 },
          { key: "source_context", label: "Source / Context from Discovery", type: "textarea", rows: 4 },
          { key: "priority", label: "Priority", type: "select", options: meta.clarification_priorities, width: 100 },
        ]}
        rows={rows}
        onChange={(r) => setRows(r.map((x, i) => ({ ...x, number: String(i + 1) })))}
        emptyRow={() => ({ number: "", category: "", question: "", why_asking: "", source_context: "", priority: "" })}
      />
      <Button onClick={() => void save()} disabled={saving}>Save Clarification Questions</Button>
    </Expander>
  );
}
