import { Button, Spinner } from "@fluentui/react-components";

type Props = { onAnalyze: () => void; busy: boolean; model: string; label?: string };

/** The "Analyze" primary button + "Model: ..." caption shown at the top of each tab. */
export function AnalyzeBar({ onAnalyze, busy, model, label = "Analyze" }: Props) {
  return (
    <div className="row" style={{ margin: "4px 0 8px" }}>
      <span className="spacer" />
      <Button appearance="primary" onClick={onAnalyze} disabled={busy} style={{ minWidth: 140, background: "var(--apa-accent)" }}>
        {busy ? <Spinner size="tiny" /> : label}
      </Button>
      <span className="caption">Model: <code>{model}</code></span>
    </div>
  );
}

/** Small per-section Analyze button (render_section_analyze_button). */
export function SectionAnalyze({ onAnalyze, busy }: { onAnalyze: () => void; busy: boolean }) {
  return (
    <Button appearance="primary" size="small" onClick={(e) => { e.stopPropagation(); onAnalyze(); }} disabled={busy} style={{ background: "var(--apa-accent)" }}>
      {busy ? <Spinner size="extra-tiny" /> : "Analyze"}
    </Button>
  );
}
