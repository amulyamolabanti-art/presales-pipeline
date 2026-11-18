import { useState, type ReactNode } from "react";
import { ChevronDownRegular, ChevronRightRegular } from "@fluentui/react-icons";

type Props = { title: ReactNode; status?: string; defaultOpen?: boolean; children: ReactNode; right?: ReactNode };

/** Collapsible panel, the equivalent of st.expander("Label · Ready / Not analyzed yet"). */
const EXPAND_ALL = new URLSearchParams(window.location.search).get("expand") === "all";

export function Expander({ title, status, defaultOpen = false, children, right }: Props) {
  const [open, setOpen] = useState(defaultOpen || EXPAND_ALL);
  return (
    <div className="expander">
      <button type="button" className="exp-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? <ChevronDownRegular /> : <ChevronRightRegular />}
        <span style={{ fontWeight: 600 }}>{title}</span>
        {status && <span className={"status-pill" + (status === "Ready" ? " ready" : "")}>{status}</span>}
        <span className="spacer" />
        {right}
      </button>
      {open && <div className="exp-body">{children}</div>}
    </div>
  );
}
