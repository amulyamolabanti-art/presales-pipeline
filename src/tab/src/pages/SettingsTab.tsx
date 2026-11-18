import { useEffect, useState } from "react";
import { Button, Dropdown, Option } from "@fluentui/react-components";
import { api } from "../api";
import { Expander } from "../components/Expander";
import type { TabProps } from "./types";

export function SettingsTab({ meta, bundle, setBundle, notify }: TabProps) {
  const pid = bundle.proposal.proposal_id;
  const [prompts, setPrompts] = useState<Record<string, string>>(bundle.prompts);
  const [busy, setBusy] = useState(false);
  useEffect(() => setPrompts(bundle.prompts), [bundle.prompts]);

  const saveAll = async () => {
    setBusy(true);
    try {
      const out = await api.savePrompts(pid, prompts);
      setBundle((b) => ({ ...b, prompts: out }));
      notify("Context files saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setBusy(false);
    }
  };

  const refresh = async () => {
    setBusy(true);
    try {
      const out = await api.resetPrompts(pid);
      setBundle((b) => ({ ...b, prompts: out }));
      notify("Context files refreshed from Template.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setBusy(false);
    }
  };

  const setModel = async (model: string) => {
    try {
      const p = await api.setModel(pid, model);
      setBundle((b) => ({ ...b, proposal: p }));
    } catch (e) {
      notify((e as Error).message, "err");
    }
  };

  return (
    <div>
      <h1 className="tab-title">⚙️ Settings</h1>

      <h4>Active Pre-Sales User & Circle</h4>
      <div className="caption">Resolved from official SharePoint User Directory. Signed in as <strong>{meta.user.display_name}</strong> (Circle: <strong>{meta.user.department || "Platform"}</strong>).</div>
      <Dropdown
        value={`${meta.user.display_name} (${meta.user.department || "Platform"})`}
        selectedOptions={[meta.user.user_id]}
        onOptionSelect={(_, d) => {
          if (d.optionValue) {
            const url = new URL(window.location.href);
            url.searchParams.set("as", d.optionValue);
            window.location.href = url.toString();
          }
        }}
        style={{ minWidth: 360, marginTop: 6, marginBottom: 12 }}
      >
        <Option value="yasaswini.k">Yasaswini K (Platform)</Option>
        <Option value="surendra.reddy">Surendra Reddy (Data & Insights)</Option>
        <Option value="charishma.m">Charishma M (Testing)</Option>
        <Option value="amulya.n">Amulya N (Salesforce)</Option>
        <Option value="karthik.valluri">Karthik Valluri (Admin)</Option>
      </Dropdown>

      <h4>LLM Model</h4>
      <div className="caption">Model used by Analyze on every tab</div>
      <Dropdown value={bundle.proposal.model || meta.models[0]} selectedOptions={[bundle.proposal.model || meta.models[0]]} onOptionSelect={(_, d) => d.optionValue && void setModel(d.optionValue)} style={{ minWidth: 320 }}>
        {meta.models.map((m) => <Option key={m} value={m}>{m}</Option>)}
      </Dropdown>
      <div className="caption">Backend: {meta.backend}. Analyze returns the stored outputs for this proposal; a model backend is added once Azure OpenAI exists.</div>

      <h4>Edit Section Context Files</h4>
      <div className="caption">
        Your private workspace: proposal <code>{bundle.proposal.name}</code> in <code>data/apa_db.xlsx</code> (sheet Prompts). New proposals are seeded from <code>prompts/</code>.
        Edit instructions below and click Save to update analysis / diagram behavior. Refresh Template Context replaces your context files with a fresh copy from the template.
      </div>
      <div className="row" style={{ margin: "8px 0" }}>
        <Button appearance="primary" style={{ flex: 1, background: "var(--apa-accent)" }} onClick={() => void saveAll()} disabled={busy}>Save All Context Files</Button>
        <Button style={{ flex: 1 }} onClick={() => void refresh()} disabled={busy}>Refresh Template Context</Button>
      </div>
      {meta.prompt_fields.map((f) => (
        <div className="prompt-block" key={f}>
          <label>context_{f}.txt — {meta.labels[f] ?? meta.extra_context_labels[f] ?? f}</label>
          <textarea value={prompts[f] ?? ""} onChange={(e) => setPrompts((p) => ({ ...p, [f]: e.target.value }))} />
        </div>
      ))}

      <Expander title="Effort Matrix DE/BI Guidance">
        <MatrixHelp {...{ meta, bundle, setBundle, notify }} />
      </Expander>

      <h4>Save Section Outputs</h4>
      <Button onClick={() => notify("Section outputs are stored in data/apa_db.xlsx on every Save and Analyze; nothing else to write.")}>Save Section Outputs to Files</Button>
    </div>
  );
}

function MatrixHelp({ bundle, setBundle, notify }: Pick<TabProps, "meta" | "bundle" | "setBundle" | "notify">) {
  const pid = bundle.proposal.proposal_id;
  const [tips, setTips] = useState<Record<string, string>>({});
  const [help, setHelp] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setTips(Object.fromEntries(bundle.effort.state.matrix.map((m) => [m.size, m.tooltip])));
    setHelp(bundle.effort.state.matrix_column_help);
  }, [bundle.effort]);

  const save = async () => {
    setBusy(true);
    try {
      const state = {
        ...bundle.effort.state,
        matrix: bundle.effort.state.matrix.map((m) => ({ ...m, tooltip: tips[m.size] ?? m.tooltip })),
        matrix_column_help: help,
      };
      const r = await api.saveEffort(pid, state);
      setBundle((b) => ({ ...b, effort: r }));
      notify("Effort matrix guidance saved.");
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="caption">Per-size DE/BI guidance (shown in the Effort Reference Matrix) and column help text.</div>
      {bundle.effort.state.matrix.map((m) => (
        <div className="prompt-block" key={m.size}>
          <label>{m.size} — {m.complexity}</label>
          <textarea style={{ height: 70 }} value={tips[m.size] ?? ""} onChange={(e) => setTips((t) => ({ ...t, [m.size]: e.target.value }))} />
        </div>
      ))}
      {Object.keys(bundle.effort.state.matrix_column_help).map((col) => (
        <div className="prompt-block" key={col}>
          <label>Column: {col}</label>
          <textarea style={{ height: 56 }} value={help[col] ?? ""} onChange={(e) => setHelp((h) => ({ ...h, [col]: e.target.value }))} />
        </div>
      ))}
      <Button onClick={() => void save()} disabled={busy}>Save Guidance</Button>
    </div>
  );
}
