import { AnalyzeBar } from "../components/AnalyzeBar";
import { SectionPanel } from "../components/SectionPanel";
import type { TabProps } from "./types";

export function ScopeTab({ meta, bundle, analyzing, runAnalyze }: TabProps) {
  const fields = meta.tab_fields.scope;
  const busy = fields.some((f) => analyzing.has(f));
  return (
    <div>
      <h1 className="tab-title">📋 Scope</h1>
      <AnalyzeBar onAnalyze={() => void runAnalyze(fields, "Scope")} busy={busy} model={bundle.proposal.model} />
      <SectionPanel label="Assumptions" section={bundle.sections.assumptions} />
      <SectionPanel label="Customer Dependencies" section={bundle.sections.customer_dependencies} />
      <SectionPanel label="In scope" section={bundle.sections.in_scope} />
      <SectionPanel label="Out of Scope" section={bundle.sections.out_of_scope} />
    </div>
  );
}
