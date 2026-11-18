import type { Section } from "../api";
import { Expander } from "./Expander";

/** Overview / Scope section: collapsible formatted panel (render_formatted_section). */
export function SectionPanel({ label, section, defaultOpen = false }: { label: string; section: Section; defaultOpen?: boolean }) {
  const ready = section.content.trim().length > 0;
  return (
    <Expander title={label} status={ready ? "Ready" : "Not analyzed yet"} defaultOpen={defaultOpen}>
      {ready ? (
        <div className="section-content-panel" dangerouslySetInnerHTML={{ __html: section.html }} />
      ) : (
        <div className="caption">Run Analyze to generate {label}.</div>
      )}
    </Expander>
  );
}
