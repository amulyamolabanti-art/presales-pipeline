import { Button } from "@fluentui/react-components";
import { AddRegular, DeleteRegular } from "@fluentui/react-icons";

export type Column = {
  key: string;
  label: string;
  type?: "text" | "textarea" | "select" | "number" | "readonly";
  options?: string[];
  width?: string | number;
  rows?: number;
};

type Props<T extends Record<string, unknown>> = {
  columns: Column[];
  rows: T[];
  onChange: (rows: T[]) => void;
  emptyRow: () => T;
  dynamic?: boolean;          // allow add / delete rows (num_rows="dynamic")
  footer?: React.ReactNode;   // optional total row etc.
};

/** Editable table, the equivalent of st.data_editor. Edits stay local until the caller saves. */
export function EditableGrid<T extends Record<string, unknown>>({ columns, rows, onChange, emptyRow, dynamic = true, footer }: Props<T>) {
  const update = (i: number, key: string, value: unknown) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, [key]: value } : r));
    onChange(next);
  };
  const remove = (i: number) => onChange(rows.filter((_, idx) => idx !== i));
  const add = () => onChange([...rows, emptyRow()]);

  return (
    <div>
      <div className="grid-wrap">
        <table className="grid">
          <thead>
            <tr>
              {columns.map((c) => <th key={c.key} style={{ width: c.width }}>{c.label}</th>)}
              {dynamic && <th style={{ width: 36 }} />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => {
                  const v = row[c.key];
                  const s = v === undefined || v === null ? "" : String(v);
                  if (c.type === "readonly") return <td key={c.key} className={typeof v === "number" ? "num" : "ro"}>{s}</td>;
                  if (c.type === "select") {
                    const opts = c.options ?? [];
                    return (
                      <td key={c.key}>
                        <select value={s} onChange={(e) => update(i, c.key, e.target.value)}>
                          <option value="">—</option>
                          {!opts.includes(s) && s && <option value={s}>{s}</option>}
                          {opts.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      </td>
                    );
                  }
                  if (c.type === "textarea") {
                    return <td key={c.key}><textarea rows={c.rows ?? 3} value={s} onChange={(e) => update(i, c.key, e.target.value)} /></td>;
                  }
                  if (c.type === "number") {
                    return <td key={c.key}><input type="number" step="any" value={s} onChange={(e) => update(i, c.key, e.target.value === "" ? "" : Number(e.target.value))} /></td>;
                  }
                  return <td key={c.key}><input type="text" value={s} onChange={(e) => update(i, c.key, e.target.value)} /></td>;
                })}
                {dynamic && (
                  <td style={{ textAlign: "center" }}>
                    <Button appearance="subtle" size="small" icon={<DeleteRegular />} onClick={() => remove(i)} title="Delete row" />
                  </td>
                )}
              </tr>
            ))}
            {footer}
          </tbody>
        </table>
      </div>
      {dynamic && (
        <div className="grid-actions">
          <Button size="small" icon={<AddRegular />} onClick={add}>Add row</Button>
          <span className="muted">{rows.length} row(s)</span>
        </div>
      )}
    </div>
  );
}
