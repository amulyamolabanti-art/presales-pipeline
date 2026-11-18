import { useCallback, useEffect, useState } from "react";
import { Button, Spinner } from "@fluentui/react-components";
import { api, type Bundle, type Meta } from "../api";
import { ChatSection } from "../components/ChatSection";
import { SummaryTab } from "./SummaryTab";
import { ArchitectureTab } from "./ArchitectureTab";
import { EstimatesTab } from "./EstimatesTab";
import { OverviewTab } from "./OverviewTab";
import { ScopeTab } from "./ScopeTab";
import { SettingsTab } from "./SettingsTab";
import type { TabProps } from "./types";

const TABS: [string, string][] = [
  ["Summary", "📋"],
  ["Overview", "📊"],
  ["Scope", "🎯"],
  ["Architecture", "🏗️"],
  ["Estimates", "💰"],
  ["Settings", "⚙️"],
];

type Props = {
  meta: Meta;
  proposalId: string;
  initialTab?: string;
  onSwitch: () => void;
  onLogout?: () => void;
  notify: (t: string, k?: "ok" | "err") => void;
  dark: boolean;
};

export function Workspace({ meta, proposalId, initialTab, onSwitch, notify, dark }: Props) {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [tab, setTab] = useState(TABS.some(([n]) => n === initialTab) ? (initialTab as string) : "Summary");
  const [analyzing, setAnalyzing] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");

  useEffect(() => {
    setBundle(null);
    api.bundle(proposalId).then(setBundle).catch((e) => setError((e as Error).message));
  }, [proposalId]);

  const runAnalyze = useCallback(async (fields: string[], label: string) => {
    setAnalyzing((s) => new Set([...s, ...fields]));
    try {
      const r = await api.analyze(proposalId, fields);
      setBundle(r);
      notify(`${label} analysis complete.`);
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setAnalyzing((s) => { const n = new Set(s); fields.forEach((f) => n.delete(f)); return n; });
    }
  }, [proposalId, notify]);

  if (error) return <div className="page"><div className="err">{error}</div><Button onClick={onSwitch}>Back to proposals</Button></div>;
  if (!bundle) return <div className="page"><Spinner label="Loading proposal..." /></div>;

  const tabProps: TabProps = {
    meta, bundle,
    setBundle: (b) => setBundle((prev) => (typeof b === "function" ? (prev ? b(prev) : prev) : b)),
    analyzing, runAnalyze, notify,
  };

  const rawOwner = bundle.proposal.owner_name || bundle.proposal.owner_user_id || "";
  const ownerDisplay = (() => {
    if (!rawOwner || rawOwner.toLowerCase() === "unknown") return "Unknown";
    const base = rawOwner.includes("@") ? rawOwner.split("@")[0] : rawOwner;
    if (base.includes(".")) {
      return base
        .split(/[._-]+/)
        .filter(Boolean)
        .map((p) => (p.length === 1 ? p.toUpperCase() : p[0].toUpperCase() + p.slice(1).toLowerCase()))
        .join(" ");
    }
    return base;
  })();

  return (
    <div className="page">
      <div className="banner">
        <div>
          <strong>Active Proposal:</strong> <code>{bundle.proposal.name}</code>
          {bundle.proposal.client && <> · {bundle.proposal.client}</>}
          {ownerDisplay && <> · <span className="muted">owner: {ownerDisplay}</span></>}
        </div>
        <span className="spacer" />
        <Button onClick={onSwitch}>Switch Proposal</Button>
      </div>

      <div className="tabbar">
        {TABS.map(([name, icon]) => (
          <button key={name} type="button" className={tab === name ? "active" : ""} onClick={() => setTab(name)}>{icon} {name}</button>
        ))}
      </div>
      <hr className="divider" />
      {bundle.loaded_files.length > 0 && (
        <div className="caption">📁 Loaded files: {bundle.loaded_files.join(", ")}{bundle.cached_chars ? ` | cached text: ${bundle.cached_chars.toLocaleString()} chars` : ""}</div>
      )}

      {tab === "Summary" && <SummaryTab {...tabProps} onSelectTab={(t) => setTab(t)} />}
      {tab === "Overview" && <OverviewTab {...tabProps} />}
      {tab === "Scope" && <ScopeTab {...tabProps} />}
      {tab === "Architecture" && <ArchitectureTab {...tabProps} />}
      {tab === "Estimates" && <EstimatesTab {...tabProps} {...{ dark }} />}
      {tab === "Settings" && <SettingsTab {...tabProps} />}

      <ChatSection proposalId={proposalId} messages={bundle.chat} onMessages={(m) => setBundle((b) => (b ? { ...b, chat: m } : b))} currentTab={tab} />
    </div>
  );
}
