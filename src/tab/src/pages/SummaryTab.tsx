import { useRef, useState } from "react";
import {
  DocumentTextRegular,
  DocumentBulletListRegular,
  PeopleTeamRegular,
  PersonRegular,
  ChatRegular,
  CheckmarkCircleFilled,
  ArrowRightRegular,
  ShieldRegular,
  ScalesRegular,
  DataTrendingRegular,
  BookmarkRegular,
} from "@fluentui/react-icons";
import { api } from "../api";
import type { TabProps } from "./types";

interface SummaryTabProps extends TabProps {
  onSelectTab?: (tab: string) => void;
}

export function SummaryTab({ bundle, setBundle, notify, onSelectTab }: SummaryTabProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  // Calculate dynamic metrics or fallback to standard presentation values
  const rfpDocsCount = bundle.documents?.length || 1;
  const loadedFilesCount = bundle.loaded_files?.length || 1;
  const complianceCount = bundle.tables?.clarification_questions?.length || 18;
  const queriesCount = bundle.chat?.length || 1;
  const marketingInfoCount = 37;

  // Progress computation
  const totalSections = Object.keys(bundle.sections || {}).length;
  const completedSections = Object.values(bundle.sections || {}).filter(
    (s) => s.content && s.content.trim().length > 0
  ).length;
  const progressPct = totalSections > 0 ? Math.min(100, Math.max(45, Math.round((completedSections / totalSections) * 100))) : 86;

  const upload = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setUploading(true);
    try {
      const r = await api.upload(bundle.proposal.proposal_id, files);
      setBundle((b) => ({
        ...b,
        documents: r.documents,
        loaded_files: r.loaded_files,
        cached_chars: r.cached_chars,
      }));
      if (r.errors.length) {
        notify("Some files could not be read: " + r.errors.join("; "), "err");
      } else {
        notify(`${r.loaded_files.length} RFP document(s) uploaded and indexed.`);
      }
    } catch (e) {
      notify((e as Error).message, "err");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const nav = (target: string) => {
    if (onSelectTab) {
      onSelectTab(target);
    }
  };

  return (
    <div className="summary-container">
      {/* 1. Header Bar: Title + Core Progress */}
      <div className="summary-dashboard-header">
        <div className="summary-title-col">
          <div className="summary-title-row">
            <h1 className="summary-heading">Volume Metric Dashboard</h1>
            <span className="summary-star" title="Active Proposal">⭐</span>
          </div>
          <p className="summary-subheading">Key metrics from your active proposal.</p>
        </div>

        <div className="summary-progress-col">
          <div className="progress-label-row">
            <span className="progress-label">Core Progress</span>
            <span className="progress-percentage">{progressPct}%</span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      </div>

      {/* 2. Top Metric Cards (5 Cards) */}
      <div className="metric-cards-grid">
        <div className="kpi-metric-card">
          <div className="kpi-icon-row">
            <DocumentBulletListRegular className="kpi-icon icon-blue" />
            <span className="kpi-value">{rfpDocsCount}</span>
          </div>
          <div className="kpi-title">RFP Response in Create</div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-icon-row">
            <DocumentTextRegular className="kpi-icon icon-green" />
            <span className="kpi-value">{marketingInfoCount}</span>
          </div>
          <div className="kpi-title">Marketing Core Info</div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-icon-row">
            <PeopleTeamRegular className="kpi-icon icon-teal" />
            <span className="kpi-value">{complianceCount}</span>
          </div>
          <div className="kpi-title">Compliance Check</div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-icon-row">
            <PersonRegular className="kpi-icon icon-blue" />
            <span className="kpi-value">{loadedFilesCount}</span>
          </div>
          <div className="kpi-title">Volume Entered</div>
        </div>

        <div className="kpi-metric-card">
          <div className="kpi-icon-row">
            <ChatRegular className="kpi-icon icon-purple" />
            <span className="kpi-value">{queriesCount}</span>
          </div>
          <div className="kpi-title">Queries for Ask AI</div>
        </div>
      </div>

      {/* 3. RFP Document Uploader (Moved from Overview Tab) */}
      <div className="uploader-section">
        <div className="uploader">
          <span style={{ fontWeight: 600 }}>Upload RFP documents (PDF / TXT / DOCX)</span>
          <input
            ref={fileRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.doc"
            onChange={(e) => void upload(e.target.files)}
            disabled={uploading}
          />
          {uploading && <span>Reading & parsing documents...</span>}
        </div>
      </div>

      {/* 4. Analysis Summary (6 Cards) */}
      <div className="analysis-summary-section">
        <h2 className="section-title">Analysis Summary</h2>
        <div className="analysis-cards-grid">
          {/* Card 1: Volume Summary */}
          <div className="analysis-card" onClick={() => nav("Overview")}>
            <div className="analysis-card-header">
              <DocumentTextRegular className="card-header-icon icon-blue" />
              <span className="analysis-card-title color-blue">Volume Summary</span>
            </div>
            <p className="analysis-card-desc">
              View overall content vs volume progress, including word count, use of AI, and volume completion %.
            </p>
            <div className="analysis-card-footer">
              <span className="footer-link">Go to details <ArrowRightRegular className="arrow-icon" /></span>
            </div>
          </div>

          {/* Card 2: Gaps */}
          <div className="analysis-card" onClick={() => nav("Overview")}>
            <div className="analysis-card-header">
              <DocumentBulletListRegular className="card-header-icon icon-green" />
              <span className="analysis-card-title color-green">Gaps</span>
            </div>
            <p className="analysis-card-desc">
              See volume vs. total missing info, by the zone, section and sub-section.
            </p>
            <div className="analysis-card-footer">
              <span className="footer-link">Go to Gaps <ArrowRightRegular className="arrow-icon" /></span>
            </div>
          </div>

          {/* Card 3: Inconsistencies */}
          <div className="analysis-card" onClick={() => nav("Scope")}>
            <div className="analysis-card-header">
              <ScalesRegular className="card-header-icon icon-purple" />
              <span className="analysis-card-title color-purple">Inconsistencies</span>
            </div>
            <p className="analysis-card-desc">
              See use of words or content that conflicts, or use of conflicting templates.
            </p>
            <div className="analysis-card-footer">
              <span className="footer-link">Go to details <ArrowRightRegular className="arrow-icon" /></span>
            </div>
          </div>

          {/* Card 4: Compliance */}
          <div className="analysis-card" onClick={() => nav("Overview")}>
            <div className="analysis-card-header">
              <ShieldRegular className="card-header-icon icon-amber" />
              <span className="analysis-card-title color-amber">Compliance</span>
            </div>
            <p className="analysis-card-desc">
              See compliance status (100% – 0%) for compliance areas &amp; improvement %.
            </p>
            <div className="analysis-card-footer">
              <span className="footer-link">Go to details <ArrowRightRegular className="arrow-icon" /></span>
            </div>
          </div>

          {/* Card 5: Topic Heatmap with Node Graph Visual */}
          <div className="analysis-card" onClick={() => nav("Architecture")}>
            <div className="analysis-card-header">
              <DataTrendingRegular className="card-header-icon icon-teal" />
              <span className="analysis-card-title color-teal">Topic Heatmap</span>
            </div>
            <div className="heatmap-graphic-wrapper">
              <div className="node-graph-box">
                <div className="node-circle node-blue">3</div>
                <div className="node-line-horizontal" />
                <div className="node-col">
                  <div className="node-circle node-grey">1</div>
                  <div className="node-line-vertical" />
                  <div className="node-circle node-green">4</div>
                </div>
                <div className="node-line-horizontal" />
                <div className="node-col">
                  <div className="node-circle node-blue">2</div>
                  <div className="node-line-vertical" />
                  <div className="node-circle node-blue">5</div>
                </div>
              </div>
            </div>
            <div className="analysis-card-footer">
              <span className="footer-link">Go to heatmap <ArrowRightRegular className="arrow-icon" /></span>
            </div>
          </div>

          {/* Card 6: Themes */}
          <div className="analysis-card" onClick={() => nav("Scope")}>
            <div className="analysis-card-header">
              <BookmarkRegular className="card-header-icon icon-blue" />
              <span className="analysis-card-title color-blue">Themes</span>
            </div>
            <p className="analysis-card-desc">
              View primary, finalist &amp; volume vs. submitted RFP, with similarity score.
            </p>
            <div className="analysis-card-footer">
              <span className="footer-link">Go to details <ArrowRightRegular className="arrow-icon" /></span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Bottom Split Section: Recent Alerts & Quick Links */}
      <div className="summary-bottom-row">
        {/* Left: Recent Alerts */}
        <div className="bottom-panel recent-alerts-card">
          <h3 className="bottom-panel-title">Recent Alerts</h3>
          <div className="alerts-list">
            <div className="alert-item">
              <CheckmarkCircleFilled className="alert-check-icon" />
              <span className="alert-text">17 new compliance alerts</span>
              <span className="alert-time">Apr 26, 9:14 AM</span>
            </div>
            <div className="alert-item">
              <CheckmarkCircleFilled className="alert-check-icon" />
              <span className="alert-text">4 volume gap alerts</span>
              <span className="alert-time">Apr 24, 8:21 AM</span>
            </div>
            <div className="alert-item">
              <CheckmarkCircleFilled className="alert-check-icon" />
              <span className="alert-text">&quot;-&quot; character in Overview &amp; P</span>
              <span className="alert-time">Apr 23, 4:17 PM</span>
            </div>
          </div>
          <div className="bottom-panel-footer">
            <button type="button" className="panel-footer-btn" onClick={() => nav("Overview")}>
              Go to Alerts <ArrowRightRegular className="arrow-icon" />
            </button>
          </div>
        </div>

        {/* Right: Quick Links */}
        <div className="bottom-panel quick-links-card">
          <h3 className="bottom-panel-title">Quick Links</h3>
          <div className="quick-links-columns">
            <div className="quick-links-col">
              <div className="quick-link-row" onClick={() => nav("Overview")}>
                <DocumentTextRegular className="link-icon icon-blue" />
                <span>Volume Summary</span>
              </div>
              <div className="quick-link-row" onClick={() => nav("Overview")}>
                <PersonRegular className="link-icon icon-blue" />
                <span>Gaps &amp; Missing Info</span>
              </div>
              <div className="quick-link-row" onClick={() => nav("Overview")}>
                <ShieldRegular className="link-icon icon-blue" />
                <span>Compliance Alerts</span>
              </div>
              <button type="button" className="view-all-link" onClick={() => nav("Overview")}>
                View all <ArrowRightRegular className="arrow-icon" />
              </button>
            </div>

            <div className="quick-links-col">
              <div className="quick-link-row" onClick={() => nav("Overview")}>
                <ScalesRegular className="link-icon icon-purple" />
                <span>Inconsistencies</span>
              </div>
              <div className="quick-link-row" onClick={() => nav("Architecture")}>
                <ShieldRegular className="link-icon icon-amber" />
                <span>Topic Heatmap</span>
              </div>
              <div className="quick-link-row" onClick={() => nav("Overview")}>
                <ChatRegular className="link-icon icon-teal" />
                <span>Ask AI</span>
              </div>
              <button type="button" className="view-all-link" onClick={() => nav("Scope")}>
                View all <ArrowRightRegular className="arrow-icon" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
