import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import type { Bundle, Meta, ProposalRow } from './api';

vi.mock('@microsoft/teams-js', () => ({
  app: {
    initialize: vi.fn().mockRejectedValue(new Error('Teams host unavailable')),
    getContext: vi.fn(),
    registerOnThemeChangeHandler: vi.fn(),
    notifySuccess: vi.fn(),
  },
}));

const mockMeta: Meta = {
  user: {
    user_id: 'unknown',
    display_name: 'Unknown',
    email: '',
    role: 'guest',
    department: '',
  },
  backend: 'stored-outputs (no model)',
  models: ['gemini-2.5-pro'],
  fields: [
    'document_score', 'summary', 'current_state', 'target_state', 'pain_areas', 'coe_involved',
    'assumptions', 'customer_dependencies', 'in_scope', 'out_of_scope',
    'current_state_architecture', 'target_architecture', 'work_breakdown', 'effort_estimate',
  ],
  labels: {
    document_score: 'Document Score',
    summary: 'Summary',
    current_state: 'Current State',
    target_state: 'Target State',
    pain_areas: 'Pain Areas',
    coe_involved: 'COE to be involved',
    assumptions: 'Assumptions',
    customer_dependencies: 'Customer Dependencies',
    in_scope: 'In Scope',
    out_of_scope: 'Out of Scope',
    current_state_architecture: 'Current State Architecture',
    target_architecture: 'Target State Architecture',
    architecture_mapping: 'Current State to Target State Architecture Mapping',
    roles: 'Roles',
    work_breakdown: 'Work Breakdown',
    effort_estimate: 'Effort Estimate',
  },
  tab_fields: {
    overview: ['document_score', 'summary', 'current_state', 'target_state', 'pain_areas', 'coe_involved'],
    scope: ['assumptions', 'customer_dependencies', 'in_scope', 'out_of_scope'],
    architecture: ['current_state_architecture', 'target_architecture', 'architecture_mapping', 'roles'],
    estimates: ['work_breakdown', 'effort_estimate'],
    settings: [],
  },
  table_columns: {
    architecture_mapping: { current_state: 'Current State', target_state: 'Target State', remark: 'Remark' },
    roles: { role: 'Role', experience: 'Exp', skills: 'Skills', description: 'Description' },
    clarification_questions: { number: '#', category: 'Category', question: 'Question' },
    work_breakdown: { phase: 'Phase', task: 'Task', description: 'Description', activity: 'Activity', pd: 'PD' },
  },
  clarification_categories: ['Volumetrics', 'Commercial', 'Current State', 'Target State'],
  clarification_priorities: ['High', 'Medium', 'Low'],
  prompt_fields: ['summary', 'current_state', 'target_state'],
  extra_context_labels: {},
};

const mockProposals: ProposalRow[] = [
  {
    proposal_id: 'p_fb4a3d00b2',
    name: 'ARMS Platform RFP',
    client: "St. Luke's Medical Center",
    owner_user_id: 'yasaswini.k',
    owner_name: 'Yasaswini K',
    status: 'In Progress',
    model: 'gemini-2.5-pro',
    seed_key: 'ARMS',
    created_at: '2026-11-12T16:21:11',
    updated_at: '2026-11-12T16:21:11',
    sections_ready: 17,
    sections_total: 17,
    documents: 1,
  },
  {
    proposal_id: 'p_844cdb41ee',
    name: 'Cirrium Cloud Modernization',
    client: 'Cirrium Global',
    owner_user_id: 'surendra.reddy',
    owner_name: 'Surendra Reddy',
    status: 'Draft',
    model: 'gemini-2.5-pro',
    seed_key: 'Cirrium',
    created_at: '2026-11-12T17:53:07',
    updated_at: '2026-11-12T17:53:07',
    sections_ready: 12,
    sections_total: 17,
    documents: 2,
  },
];

const mockBundle: Bundle = {
  proposal: mockProposals[0],
  documents: [{ doc_id: 'd1', file_name: 'RFP_ARMS_Document.pdf', chars: 15420 }],
  loaded_files: ['RFP_ARMS_Document.pdf'],
  cached_chars: 15420,
  sections: {
    document_score: { content: '| Requirement | Score |\n|---|---|\n| Architecture | 95% |', html: '<table>...</table>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    summary: { content: 'Executive Summary for ARMS healthcare platform.', html: '<p>Summary</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    current_state: { content: 'Current EHR client-server monolith.', html: '<p>Current</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    target_state: { content: 'Target cloud-native microservices.', html: '<p>Target</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    pain_areas: { content: 'High data synchronization latency.', html: '<p>Pain</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    coe_involved: { content: 'Data & Insights, Cloud & Platform COE.', html: '<p>COE</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    assumptions: { content: 'Client provides VPN access.', html: '<p>Assumptions</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    customer_dependencies: { content: 'Firewall rules opened within 14 days.', html: '<p>Deps</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    in_scope: { content: 'Data ingestion, ETL, analytics dashboard.', html: '<p>InScope</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    out_of_scope: { content: 'Legacy hardware decommissioning.', html: '<p>OutScope</p>', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    current_state_architecture: { content: 'Legacy on-premise relational database and client frontends.', html: '', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
    target_architecture: { content: 'Azure Lakehouse with Spark streaming and Power BI.', html: '', status: 'Ready', model: 'gemini-2.5-pro', updated_at: '2026-11-12' },
  },
  tables: {
    architecture_mapping: [
      { current_state: 'On-prem SQL Server', target_state: 'Azure SQL Managed Instance', remark: 'Zero-downtime replication' },
      { current_state: 'SOAP Web Services', target_state: 'REST APIs & Event Hub', remark: 'Microservice containerization' },
    ],
    roles: [
      { role: 'Lead Solution Architect', experience: '12+ yrs', skills: 'Azure, Lakehouse', description: 'Technical governance' },
    ],
    clarification_questions: [
      { number: '1', category: 'Commercial', question: 'What is the target delivery timeline?', why_asking: 'Resource planning', source_context: 'Section 4.2', priority: 'High' },
    ],
    work_breakdown: [
      { phase: 'Discovery', task: 'Source System Profiling', description: 'Analyze clinical schemas', activity: 'Architecture', pd: '15', rfp_section_reference: 'Section 2.1' },
    ],
  },
  effort: {
    state: {
      matrix: [
        { size: 'M', complexity: 'Medium Complex', discovery: 2, develop: 5, integration: 3, deployment: 2, contingency: 1, total_pd: 13, tooltip: 'Medium task' },
      ],
      distribution: { xs: 0.1, s: 0.3, m: 0.4, l: 0.15, xl: 0.05 },
      inventory_rows: [{ item: 'Clinical Ingestion Pipelines', inventory: 8, assumption: 'FHIR compliant' }],
      matrix_column_help: {},
    },
    computed_rows: [],
    summary: { total_inventory: 8, discovery: 16, develop: 40, integration: 24, deployment: 16, total_pd: 104, resource_months: 5, pd_by_size: { m: 104 } },
    wbs_total: 15,
    effort_total: 104,
    delta: 89,
    matched: false,
  },
  gantt_settings: { project_start: '2026-12-01', resources: 4 },
  diagrams: {
    current_state_architecture: '/api/proposals/p_fb4a3d00b2/diagrams/current_state_architecture',
    target_architecture: '/api/proposals/p_fb4a3d00b2/diagrams/target_architecture',
  },
  prompts: {
    summary: 'Analyze RFP summary...',
  },
  chat: [
    { role: 'assistant', content: 'Hello! I can answer questions about this proposal.', created_at: '2026-11-12T16:22:00' },
  ],
};

function setupFetchMocks(customProposals = mockProposals, customBundle = mockBundle, customMeta = mockMeta) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes('/api/meta')) {
      return new Response(JSON.stringify(customMeta), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/api/proposals') && !url.includes('/p_')) {
      return new Response(JSON.stringify(customProposals), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/api/proposals/p_')) {
      return new Response(JSON.stringify(customBundle), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return new Response(JSON.stringify({ error: 'Endpoint not mocked' }), { status: 404 });
  });
}

describe('AI Proposal Assistant RFP Analyzer Tab (Karthik Parity)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it('renders top identity bar with Unknown user when outside Teams', async () => {
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText('AI Proposal Assistant').length).toBeGreaterThan(0);
    });

    expect(screen.getByText('Unknown')).toBeInTheDocument();
    expect(screen.queryByText('Platform')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /New Proposal/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Dark$/i })).toBeInTheDocument();
  });

  it('renders Teams user display name and department when running inside Teams', async () => {
    const teams = await import('@microsoft/teams-js');
    vi.mocked(teams.app.initialize).mockResolvedValueOnce(undefined as never);
    vi.mocked(teams.app.getContext).mockResolvedValueOnce({
      user: {
        id: 'u-123',
        userPrincipalName: 'yasaswini.k@presales.example',
        displayName: 'Yasaswini K',
      },
      app: { theme: 'light' },
    } as never);

    const teamsMeta: Meta = {
      ...mockMeta,
      user: {
        user_id: 'yasaswini.k',
        display_name: 'Yasaswini K',
        email: 'yasaswini.k@presales.example',
        role: 'user',
        department: 'Platform',
      },
    };

    setupFetchMocks(mockProposals, mockBundle, teamsMeta);
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText('AI Proposal Assistant').length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      expect(screen.getAllByText('Yasaswini K').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Platform')).toBeInTheDocument();
  });

  it('renders ProposalsPage list table with proposals, client names, owners, and sections count', async () => {
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('ARMS Platform RFP')).toBeInTheDocument();
    });

    expect(screen.getByText("St. Luke's Medical Center")).toBeInTheDocument();
    expect(screen.getByText('Cirrium Cloud Modernization')).toBeInTheDocument();
    expect(screen.getByText('Cirrium Global')).toBeInTheDocument();
    expect(screen.getByText('Surendra Reddy')).toBeInTheDocument();
    expect(screen.getByText('17 / 17')).toBeInTheDocument();
    expect(screen.getByText('12 / 17')).toBeInTheDocument();
  });

  it('navigates to Workspace on proposal select and renders Active Proposal banner and Switch button', async () => {
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('ARMS Platform RFP')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('ARMS Platform RFP'));
    fireEvent.click(screen.getByRole('button', { name: /Load & Continue/i }));

    await waitFor(() => {
      expect(screen.getByText(/Active Proposal:/i)).toBeInTheDocument();
    });

    expect(screen.getByText('Switch Proposal')).toBeInTheDocument();
    expect(screen.getByText(/Loaded files: RFP_ARMS_Document\.pdf/i)).toBeInTheDocument();
  });

  it('renders all 6 top tabs (Summary, Overview, Scope, Architecture, Estimates, Settings)', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Summary/i })).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /Overview/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Scope/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Architecture/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Estimates/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Settings/i })).toBeInTheDocument();
  });

  it('renders Summary tab with Volume Metric Dashboard and KPI cards by default', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Volume Metric Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Core Progress')).toBeInTheDocument();
    expect(screen.getByText('RFP Response in Create')).toBeInTheDocument();
    expect(screen.getByText('Marketing Core Info')).toBeInTheDocument();
    expect(screen.getByText('Compliance Check')).toBeInTheDocument();
    expect(screen.getByText('Volume Entered')).toBeInTheDocument();
    expect(screen.getByText('Queries for Ask AI')).toBeInTheDocument();
    expect(screen.getByText('Analysis Summary')).toBeInTheDocument();
  });

  it('renders Overview tab with Document Score, Clarification Questions, and COE to be involved', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Overview/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Overview/i }));

    await waitFor(() => {
      expect(screen.getByText('Document Score')).toBeInTheDocument();
    });

    expect(screen.getByText('Questions for Clarifications')).toBeInTheDocument();
    expect(screen.getByText('Summary')).toBeInTheDocument();
    expect(screen.getAllByText('Current State').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Target State').length).toBeGreaterThan(0);
    expect(screen.getByText('Pain Areas')).toBeInTheDocument();
    expect(screen.getByText('COE to be involved')).toBeInTheDocument();
  });

  it('renders Architecture tab with Current/Target State, Diagram buttons, and Architecture Mapping grid', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Architecture/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Architecture/i }));

    await waitFor(() => {
      expect(screen.getAllByText('Current State Architecture').length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText('Target State Architecture').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: /Diagram/i }).length).toBeGreaterThan(0);
    expect(screen.getByText(/Current State to Target State Architecture Mapping/i)).toBeInTheDocument();
    expect(screen.getByText('On-prem SQL Server')).toBeInTheDocument();
    expect(screen.getByText('Azure SQL Managed Instance')).toBeInTheDocument();
    expect(screen.getByText('Zero-downtime replication')).toBeInTheDocument();
    expect(screen.getByText('Roles')).toBeInTheDocument();
  });

  it('renders Estimates tab with Work Breakdown, Effort Estimate, and Gantt settings', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Estimates/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Estimates/i }));

    await waitFor(() => {
      expect(screen.getByText('Work Breakdown')).toBeInTheDocument();
    });

    expect(screen.getByText('Effort Estimate')).toBeInTheDocument();
    expect(screen.getByText('Gantt Chart')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Work Breakdown'));
    await waitFor(() => {
      expect(screen.getByText('Source System Profiling')).toBeInTheDocument();
    });
  });

  it('renders Settings tab with model selection and prompt template editor', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Settings/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Settings/i }));

    await waitFor(() => {
      expect(screen.getByText('LLM Model')).toBeInTheDocument();
    });

    expect(screen.getByText('Edit Section Context Files')).toBeInTheDocument();
  });

  it('renders pinned ChatSection with query textarea and assistant greeting', async () => {
    sessionStorage.setItem('apa.proposal', 'p_fb4a3d00b2');
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Ask about this RFP/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Hello! I can answer questions about this proposal/i)).toBeInTheDocument();
  });

  it('toggles theme between Light and Dark', async () => {
    setupFetchMocks();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Dark$/i })).toBeInTheDocument();
    });

    const darkBtn = screen.getByRole('button', { name: /^Dark$/i });
    fireEvent.click(darkBtn);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Light$/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^Light$/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Dark$/i })).toBeInTheDocument();
    });
  });
});
