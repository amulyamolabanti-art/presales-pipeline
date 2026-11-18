import { useEffect, useState } from "react";
import { Button, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, Input, Label, Radio, RadioGroup, Spinner } from "@fluentui/react-components";
import { api, type Meta, type ProposalRow } from "../api";

type Props = { meta: Meta; initialMode?: "new" | "existing"; onOpen: (id: string) => void; notify: (t: string, k?: "ok" | "err") => void };

/** Proposal selection (his "Select Proposal" dialog) shown as a page that doubles as the proposal list. */
export function ProposalsPage({ meta, initialMode, onOpen, notify }: Props) {
  const [rows, setRows] = useState<ProposalRow[] | null>(null);
  const [mode, setMode] = useState<"new" | "existing">(initialMode ?? "existing");
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<ProposalRow | null>(null);

  useEffect(() => {
    if (initialMode) setMode(initialMode);
  }, [initialMode]);

  const load = () => api.proposals().then((r) => {
    setRows(r);
    if (!selected && r.length) setSelected(r[0].proposal_id);
    if (!initialMode && r.length === 0) setMode("new");
  }).catch((e) => notify((e as Error).message, "err"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, []);

  const cleaned = name.trim();
  const duplicate = !!rows?.some((r) => r.name.trim().toLowerCase() === cleaned.toLowerCase());
  const canContinue = mode === "new" ? cleaned.length > 0 && !duplicate : !!selected;

  const go = async () => {
    setBusy(true);
    try {
      if (mode === "new") {
        const p = await api.createProposal(cleaned, client);
        onOpen(p.proposal_id);
      } else {
        onOpen(selected);
      }
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (p: ProposalRow) => {
    try {
      await api.deleteProposal(p.proposal_id);
      setConfirmDelete(null);
      await load();
      notify(`Deleted ${p.name}.`);
    } catch (e) {
      notify((e as Error).message, "err");
    }
  };

  return (
    <div className="page no-chat">
      <div className="login-wrap" style={{ maxWidth: 760 }}>
        <div className="login-title">AI Proposal Assistant</div>
        <div className="login-subtitle">Signed in as {meta.user.display_name} · {meta.backend}</div>
        <h4 style={{ marginTop: 0 }}>Choose how you want to proceed</h4>
        <div className="caption">Each proposal is stored in the Excel workbook. All analysis outputs, tables, prompts and diagrams stay inside that proposal.</div>
        <RadioGroup layout="horizontal" value={mode} onChange={(_, d) => setMode(d.value as "new" | "existing")}>
          <Radio value="new" label="New Proposal" />
          <Radio value="existing" label="Existing Proposal" />
        </RadioGroup>

        {mode === "new" ? (
          <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
            <Label>Proposal Name</Label>
            <Input value={name} onChange={(_, d) => setName(d.value)} placeholder="e.g. Acme Crew Scheduling RFP" />
            <Label>Client (optional)</Label>
            <Input value={client} onChange={(_, d) => setClient(d.value)} placeholder="Client name" />
            {duplicate && <div className="warn">A proposal with this name already exists. Choose a different name, or switch to Existing Proposal.</div>}
          </div>
        ) : rows === null ? (
          <Spinner size="small" label="Loading proposals..." />
        ) : rows.length === 0 ? (
          <div className="info" style={{ marginTop: 8 }}>No existing proposals found. Create a new proposal instead.</div>
        ) : (
          <table className="proposal-list">
            <thead><tr><th /><th>Proposal</th><th>Client</th><th>Owner</th><th>Status</th><th>Sections ready</th><th>Updated</th><th /></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.proposal_id} onClick={() => setSelected(r.proposal_id)} onDoubleClick={() => onOpen(r.proposal_id)}>
                  <td><input type="radio" checked={selected === r.proposal_id} onChange={() => setSelected(r.proposal_id)} /></td>
                  <td><strong>{r.name}</strong></td>
                  <td>{r.client}</td>
                  <td>{r.owner_name}</td>
                  <td>{r.status}</td>
                  <td>{r.sections_ready} / {r.sections_total}</td>
                  <td className="muted">{String(r.updated_at).replace("T", " ").slice(0, 16)}</td>
                  <td><Button size="small" appearance="subtle" onClick={(e) => { e.stopPropagation(); setConfirmDelete(r); }}>Delete</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="row" style={{ marginTop: 16 }}>
          <span className="spacer" />
          <Button appearance="primary" style={{ background: "var(--apa-accent)" }} disabled={!canContinue || busy} onClick={() => void go()}>
            {mode === "new" ? "Create & Continue" : "Load & Continue"}
          </Button>
        </div>
      </div>

      <Dialog open={!!confirmDelete} onOpenChange={(_, d) => !d.open && setConfirmDelete(null)}>
        <DialogSurface>
          <DialogBody>
            <DialogTitle>Delete proposal</DialogTitle>
            <DialogContent>Delete <strong>{confirmDelete?.name}</strong> and all of its sections, tables, prompts and chat? This cannot be undone.</DialogContent>
            <DialogActions>
              <Button onClick={() => setConfirmDelete(null)}>Cancel</Button>
              <Button appearance="primary" onClick={() => confirmDelete && void remove(confirmDelete)}>Delete</Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </div>
  );
}
