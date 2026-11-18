# AI Proposal Assistant — Project Context

> **Auto-generated**: 2026-11-14T18:06:00+05:30  
> **Last Updated**: 2026-11-16T22:48:30+05:30  
> This file is the single-source LLM context for the project. Run `python update_context.py` after any code change to refresh it.

---

## 1. Project Overview

| Field | Value |
|-------|-------|
| **Name** | AI Proposal Assistant (Presales AI Solution) |
| **App Name** | `ai-proposal-assistant` |
| **Language/Runtime** | Python 3.12 (bot) + TypeScript on Node.js 22 LTS (tab) |
| **Monorepo** | npm workspaces: `/src/bot`, `/src/orchestrator`, `/src/tab`, `/contracts` |
| **IaC** | Azure Bicep (Flex Consumption Function App, Bot Service, Azure OpenAI, AI Search) |
| **Database** | Excel-backed (`data/apa_db.xlsx` via openpyxl) in prototype; Azure SQL (Entra auth) for prod |
| **Vector Store** | Azure AI Search (planned) |
| **CI/CD** | Branch-protected `main`, PR-only with 1 approval, Jira `APA-___` linked |
| **Toolkit** | Microsoft 365 Agents Toolkit v1.11 |
| **Project ID** | `857bdacf-d24a-4182-821e-663d660f4c29` |

---

## 2. Architecture Diagram (Text)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Microsoft Teams Client                       │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │  Teams Bot    │    │  Teams Personal Tab (React 18)       │   │
│  │  (Chat/Cards) │    │  Fluent UI v9 + Vite HTTPS           │   │
│  └──────┬───────┘    │  https://localhost:53000              │   │
│         │            └──────────────┬───────────────────────┘   │
└─────────┼───────────────────────────┼───────────────────────────┘
          │                           │ /api/* proxy → :3978
          ▼                           ▼
┌────────────────────────────────────────────────────────────────┐
│  Python Bot Server (src/bot/app.py)         port 3978         │
│  ├── Microsoft Teams Apps SDK (microsoft-teams-apps)          │
│  ├── FastAPI (tab_api.py) — REST endpoints for Tab dashboard  │
│  ├── Auth module (SSO mock / Entra OBO)                       │
│  ├── Cards module (Adaptive Cards — intake, RFP selector)     │
│  └── Karthik API (karthik_api/) — full proposal CRUD + AI    │
│       ├── main.py (FastAPI, port 8080 standalone)             │
│       ├── repo.py (Excel DB — openpyxl read/write)            │
│       ├── backends.py (stored-outputs / future Azure OpenAI)  │
│       ├── calc.py (effort, Gantt, WBS calculations)           │
│       └── schema.py (field definitions, labels, columns)      │
└───────────────────────────────┬────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  data/apa_db.xlsx     │
                    │  (Excel workbook DB)  │
                    │  data/seed/           │
                    │  data/docs/           │
                    │  data/diagrams/       │
                    └──────────────────────┘
```

---

## 3. Directory Structure

```
presales-app final/
├── .aava/                  # Agent memory and discovered skills
├── .github/                # PR template, workflows
├── .vscode/                # VS Code launch configs (F5 debugging)
├── appPackage/             # Teams app manifest.json + icons
├── contracts/              # Shared TypeScript types
│   └── dashboard/          # dashboard.schema.json, dashboard.example.json
├── data/                   # Excel DB (apa_db.xlsx), seed outputs, docs, diagrams
├── db/                     # SQL migration scripts (Azure SQL schema)
│   ├── 001_create_tables.sql   # 8 tables: Opportunity, StageHistory, Document, etc.
│   └── 002_seed_data.sql
├── devTools/               # Playground install info and logs
├── env/                    # Environment configs per environment
│   ├── .env.local          # Local dev settings
│   ├── .env.playground     # Playground simulator settings
│   └── .env.dev            # Azure dev settings
├── eval/                   # Evaluation benchmarks
├── infra/                  # Azure Bicep IaC templates
├── local_sharepoint_data/  # Local COE/User directory exports (gitignored)
├── prompts/                # Version-controlled prompt templates (18 context_*.txt files)
│   ├── compliance_agent/   # Compliance agent prompts
│   ├── drafting_agent/     # Drafting agent prompts
│   ├── intake_agent/       # Intake agent prompts
│   ├── publishing_agent/   # Publishing agent prompts
│   └── retrieval_agent/    # Retrieval agent prompts
├── samples/                # Synthetic RFP/RFI documents for testing
│   └── rfp/
├── src/
│   ├── bot/                # Python bot runtime (main app)
│   │   ├── app.py          # Entry point — Teams bot + FastAPI
│   │   ├── config.py       # Config class (env vars)
│   │   ├── tab_api.py      # REST API routes for Tab dashboard
│   │   ├── requirements.txt
│   │   ├── auth/           # SSO service, directory service, circle mapper
│   │   ├── cards/          # Adaptive Card generators + JSON templates
│   │   └── karthik_api/    # Full proposal CRUD + AI analysis backend
│   ├── data/               # Symlinked/shared data store
│   ├── orchestrator/       # AI agent orchestration pipeline (placeholder)
│   └── tab/                # React 18 + Fluent UI v9 Teams Tab
│       ├── package.json    # "ai-proposal-assistant-tab"
│       ├── vite.config.ts  # Dev server on https://localhost:53000
│       ├── src/            # React components
│       └── dist/           # Production build output
├── .env                    # Root env (PORT=3978, SSO_MODE=mock)
├── AI_CODING_RULES.md      # Coding standards for AI agents
├── m365agents.yml          # Main Teams Toolkit manifest
├── m365agents.local.yml    # Local debug configuration
├── m365agents.playground.yml # Playground simulator configuration
└── README.md
```

---

## 4. How to Run Locally

### Option A: Teams Bot + Playground (F5 Debug)

```powershell
# Prerequisites: Python 3.10+, Node.js 20+/22 LTS, VS Code + Teams Toolkit extension

# 1. Create Python venv and install deps
cd "c:\Users\surendra.reddy\Downloads\presales-app-new 1\presales-app final"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r src/bot/requirements.txt

# 2. In VS Code: Ctrl+Shift+D → select "Debug in Microsoft 365 Agents Playground" → F5
# Bot runs at http://localhost:3978
# Playground simulator at http://localhost:56150
```

### Option B: Bot Server Only (Manual)

```powershell
cd "c:\Users\surendra.reddy\Downloads\presales-app-new 1\presales-app final"
.\venv\Scripts\Activate.ps1
cd src/bot
python app.py
# Bot + Tab API available at http://localhost:3978
```

### Option C: Karthik API Standalone (Full Proposal UI)

```powershell
cd "c:\Users\surendra.reddy\Downloads\presales-app-new 1\presales-app final"
.\venv\Scripts\Activate.ps1
pip install fastapi uvicorn pypdf python-docx openpyxl python-multipart python-dotenv
cd src/bot/karthik_api
python -m uvicorn main:app --port 8080 --reload
# API at http://localhost:8080, serves React dist if built
```

### Option D: React Tab Dev Server

```powershell
cd "c:\Users\surendra.reddy\Downloads\presales-app-new 1\presales-app final\src\tab"
npm install
npm run dev
# Tab at https://localhost:53000 (proxies /api/* → http://127.0.0.1:3978)
```

### Option E: Run Both Simultaneously (Full Stack)

```powershell
# Terminal 1: Bot + API server
cd "c:\Users\surendra.reddy\Downloads\presales-app-new 1\presales-app final"
.\venv\Scripts\Activate.ps1
cd src/bot
python app.py

# Terminal 2: React Tab dev server
cd "c:\Users\surendra.reddy\Downloads\presales-app-new 1\presales-app final\src\tab"
npm run dev
```

---

## 5. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3978` | Bot server port |
| `CLIENT_ID` | *(empty)* | Microsoft Entra App client ID |
| `CLIENT_SECRET` | *(empty)* | Microsoft Entra App client secret |
| `TENANT_ID` | *(from toolkit)* | Entra tenant ID |
| `SSO_MODE` | `mock` | `mock` or `entra` — controls SSO behavior |
| `USE_MOCK_SSO` | `true` | Enable mock SSO profiles |
| `MOCK_USER_ID` | `auto` | Default mock persona ID |
| `ACTIVE_USER_EMAIL` | *(empty)* | Override active user email |
| `DEFAULT_CIRCLE` | `Enterprise` | Default business circle |
| `LOCAL_COE_DIRECTORY_PATH` | *(empty)* | Path to local COE directory JSON/CSV |
| `LOCAL_USER_DIRECTORY_PATH` | *(empty)* | Path to local user directory JSON/CSV |
| `AAD_APP_CLIENT_ID` | `= CLIENT_ID` | Entra app client ID for OBO |
| `AAD_APP_CLIENT_SECRET` | `= CLIENT_SECRET` | Entra app secret for OBO |
| `AAD_APP_TENANT_ID` | `= TENANT_ID` | Entra tenant for OBO |
| `AAD_APP_OAUTH_AUTHORITY_HOST` | `https://login.microsoftonline.com` | OAuth authority |

---

## 6. Key Files & Their Roles

### 6.1 Bot Core (`src/bot/`)

| File | Lines | Purpose |
|------|-------|---------|
| **app.py** | 315 | Main entry point. Creates Teams `App`, registers message handlers (`whoami`, `my bids`, `switch`, `intake`), runs on port 3978. Also mounts FastAPI for tab API routes. |
| **config.py** | 54 | `Config` class reads all env vars. `is_mock_sso` property determines mock vs real Entra SSO. |
| **tab_api.py** | 587 | FastAPI routes for the Tab dashboard: `/api/me`, `/api/bids`, `/api/intake/*`, `/api/directories`, `/api/coe/match`. Handles SSO-aware request processing with circle-based bid filtering. |
| **requirements.txt** | 5 | `python-dotenv`, `azure-identity`, `microsoft-teams-apps>=2.0.0a8`, `openpyxl`, `python-multipart` |

### 6.2 Auth Module (`src/bot/auth/`)

| File | Lines | Purpose |
|------|-------|---------|
| **sso_service.py** | 321 | `SSOService` class with mock profile resolution and real Entra OBO flow. `UserProfile` dataclass. Loads `mock_profiles.json`. |
| **directory_service.py** | 359 | Loads COE Directory + User Directory from local SharePoint exports (JSON/CSV) or fallback JSON. `match_coes_from_rfp_text()` applies strict keyword mapping rules. |
| **circle_mapper.py** | 95 | Department → Circle mapping from `circle_mapping.json`. `resolve_circle()`, `filter_bids_for_circle()`. Exports `CIRCLE_*`, `BID_TO_RFP_KEY`, `BID_UI_METADATA`, etc. |
| **mock_profiles.json** | — | Synthetic user profiles with department, circle, persona aliases |
| **circle_mapping.json** | — | Circle definitions, department→circle map, keyword rules, bid metadata, UI metadata |
| **coe_mapping.json** | — | COE directory fallback with strict mapping rules |

### 6.3 Cards Module (`src/bot/cards/`)

| File | Lines | Purpose |
|------|-------|---------|
| **rfp_catalog.py** | 281 | `SAMPLE_RFPS` dict (harborline, cedarbrook, velora), `create_intake_card()`, `create_rfp_selector_card()`, `get_rfp_by_query()` |
| **intake_card.json** | 147 | Adaptive Card v1.5 JSON for RFP intake — shows client info, scope, team, with "Assign bid owner" and "Confirm team" actions |

### 6.4 Karthik API (`src/bot/karthik_api/`)

This is the **full proposal analysis & CRUD API**, running as a standalone FastAPI app or integrated into the bot.

| File | Lines | Purpose |
|------|-------|---------|
| **main.py** | 525 | FastAPI app with all `/api/*` routes: proposals CRUD, sections, tables, effort compute, Gantt, analyze, diagrams, documents upload, prompts, chat. Serves React dist as static files. |
| **schema.py** | 153 | Field definitions: `RFP_FIELDS` (17 fields), `TAB_FIELDS`, `TABLE_FIELDS`, `TABLE_COLUMNS`, `SECTION_LABELS`, complexity/effort defaults, `MODEL_OPTIONS` |
| **repo.py** | 401 | `Db` class — reads/writes `data/apa_db.xlsx` (openpyxl). 16 Excel sheets: Users, Proposals, ProposalAccess, Documents, Sections, ClarificationQuestions, ArchitectureMapping, Roles, WorkBreakdown, EffortMatrix, EffortDistribution, EffortInventory, EffortColumnHelp, GanttSettings, Prompts, ChatMessages, AuditLog. Thread-safe with `_lock`. |
| **backends.py** | 96 | `StoredOutputsBackend` — returns pre-computed analysis from `data/seed/`. No real AI model yet (placeholder for Azure OpenAI). Keyword-based chat over analyzed sections. |
| **calc.py** | 674 | Pure calculations: row normalization, effort estimate math, Gantt scheduling (date arithmetic), WBS↔effort reconciliation, section text → HTML formatter |
| **seed.py** | — | Seed data generator |

### 6.5 Tab Frontend (`src/tab/`)

| Field | Value |
|-------|-------|
| **Package** | `ai-proposal-assistant-tab` v0.1.0 |
| **Framework** | React 18.3 + Fluent UI v9 + Vite 5.4 |
| **Dev server** | `https://localhost:53000` (HTTPS via `@vitejs/plugin-basic-ssl`) |
| **API proxy** | `/api/*` → `http://127.0.0.1:3978` |
| **Charting** | Plotly.js (basic dist) |
| **Tests** | Vitest + @testing-library/react + jsdom |
| **Build** | `tsc && vite build` → `dist/` |

### 6.6 Database Schema (`db/`)

Azure SQL schema (for production):
- **Opportunity** — central bid record (opportunityId, clientName, circle, currentStage, status)
- **StageHistory** — stage transitions
- **Document** — uploaded RFPs, past wins, generated packs
- **Requirement** — extracted requirements from Intake Agent
- **DraftSection** — generated proposal sections from Drafting Agent
- **Gap** — unanswered requirements routed to SMEs
- **ActionItem** — deadline nudges and tasks
- **AuditLog** — every prompt run, card click, approver action

### 6.7 Prompts (`prompts/`)

18 context prompt templates (`context_*.txt`):
`document_score`, `summary`, `current_state`, `target_state`, `pain_areas`, `coe_involved`, `current_state_architecture`, `target_architecture`, `architecture_mapping`, `roles`, `assumptions`, `customer_dependencies`, `in_scope`, `out_of_scope`, `effort_estimate`, `work_breakdown`, `clarification_questions`, plus diagram variants.

5 agent prompt directories: `compliance_agent/`, `drafting_agent/`, `intake_agent/`, `publishing_agent/`, `retrieval_agent/`

---

## 7. API Endpoints Summary

### 7.1 Tab API (tab_api.py, served via bot at :3978)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/me` | Current user profile (SSO-resolved) |
| GET | `/api/bids` | Bids filtered by user's circle |
| POST | `/api/intake/assign-owner` | Assign bid owner to RFP |
| POST | `/api/intake/confirm-team` | Confirm bid team |
| GET | `/api/directories` | Load SharePoint COE/User directories |
| POST | `/api/coe/match` | Match COEs from RFP text |

### 7.2 Karthik API (main.py, standalone at :8080 or integrated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/meta` | User info, backend, model options, field defs |
| GET/POST/DELETE | `/api/proposals[/{id}]` | Proposal CRUD |
| PUT | `/api/proposals/{id}/sections/{field}` | Save section text |
| PUT | `/api/proposals/{id}/tables/{field}` | Save table rows |
| POST | `/api/proposals/{id}/effort/compute` | Recalculate effort (no write) |
| PUT | `/api/proposals/{id}/effort` | Save effort estimate |
| POST | `/api/proposals/{id}/effort/sync` | Sync effort ↔ WBS |
| PUT/GET | `/api/proposals/{id}/gantt[-settings]` | Gantt chart data |
| POST | `/api/proposals/{id}/analyze` | Run AI analysis on fields |
| POST/GET | `/api/proposals/{id}/diagram/{field}` | Architecture diagrams |
| POST | `/api/proposals/{id}/documents` | Upload RFP documents |
| PUT/POST | `/api/proposals/{id}/prompts[/reset]` | Manage prompt templates |
| POST/DELETE | `/api/proposals/{id}/chat` | Chat with proposal context |
| GET | `/healthz` | Health check |

---

## 8. Business Domain Concepts

- **Circle**: Business unit (Financial Services & Insurance, Healthcare & Life Sciences, Retail & Consumer Goods, Enterprise). Users belong to a circle via their department mapping.
- **Bid/Opportunity**: An RFP response project tracked through stages (New → In analysis → Drafting → Submitted).
- **COE (Center of Excellence)**: Specialized teams matched to RFPs by keyword rules.
- **Intake Card**: Adaptive Card for initiating RFP response in Teams.
- **Proposal Sections**: 17 analysis fields (document score, summary, current/target state, pain areas, WBS, effort estimate, etc.).

---

## 9. Key Data Flows

1. **User Authentication**: `config.py` → `sso_service.py` → mock profiles OR Entra OBO → `UserProfile` with circle
2. **RFP Intake**: User types `intake` → `rfp_catalog.py` → Adaptive Card → user picks RFP → `intake_card.json` rendered → assign owner / confirm team → `tab_api.py`
3. **Proposal Analysis**: Upload docs → `main.py /analyze` → `backends.py` (stored outputs or future AI) → sections/tables saved to Excel via `repo.py`
4. **Effort Estimation**: `calc.py` computes T-shirt size × complexity distribution × inventory items → total person-days, auto-reconciles with WBS
5. **Tab Dashboard**: React app fetches `/api/me`, `/api/bids`, renders circle-scoped bid dashboard

---

## 10. Python Dependencies

```
python-dotenv>=1.0.0
azure-identity>=1.12.0
microsoft-teams-apps>=2.0.0a8,<3.0.0
openpyxl>=3.1.2
python-multipart>=0.0.9
# For Karthik API standalone:
fastapi
uvicorn
pypdf          # PDF text extraction
python-docx    # DOCX text extraction
```

---

## 11. Node.js Dependencies (Tab)

**Runtime**: `@fluentui/react-components ^9.57.0`, `@fluentui/react-icons ^2.0.260`, `@microsoft/teams-js ^2.19.0`, `plotly.js-basic-dist-min 2.35.2`, `react ^18.3.1`, `react-dom ^18.3.1`

**Dev**: `vite ^5.4.11`, `typescript ~5.6.3`, `vitest ^2.1.8`, `@vitejs/plugin-react`, `@vitejs/plugin-basic-ssl`, `eslint`, `jsdom`, `@testing-library/react`

---

## 12. File Checksums (for change detection)

<!-- AUTO-UPDATED BY update_context.py — DO NOT EDIT BELOW THIS LINE -->
<!-- CHECKSUMS_START -->
| File | Lines | MD5 | Status |
|------|-------|-----|--------|
| `src/bot/app.py` | 318 | `d1af13bcad…` | ✅ |
| `src/bot/config.py` | 53 | `5cd479ea30…` | ✅ |
| `src/bot/tab_api.py` | 585 | `b269af6e05…` | ✅ |
| `src/bot/requirements.txt` | 6 | `2c81d74114…` | ✅ |
| `src/bot/auth/__init__.py` | 84 | `fbd64986ae…` | ✅ |
| `src/bot/auth/sso_service.py` | 320 | `17a5d5c78c…` | ✅ |
| `src/bot/auth/directory_service.py` | 358 | `27b62bc974…` | ✅ |
| `src/bot/auth/circle_mapper.py` | 94 | `ac6177a6ba…` | ✅ |
| `src/bot/auth/mock_profiles.json` | 43 | `8b932bd561…` | ✅ |
| `src/bot/auth/circle_mapping.json` | 347 | `b561d2bf6f…` | ✅ |
| `src/bot/auth/coe_mapping.json` | 194 | `25bf1f95fb…` | ✅ |
| `src/bot/auth/user_circle_mapping.json` | 52 | `6d19f61878…` | ✅ |
| `src/bot/cards/rfp_catalog.py` | 280 | `4f54e4f69f…` | ✅ |
| `src/bot/cards/intake_card.json` | 146 | `97865f1ab9…` | ✅ |
| `src/bot/karthik_api/main.py` | 525 | `c6ee4b53cb…` | ✅ |
| `src/bot/karthik_api/schema.py` | 153 | `e1e60b0867…` | ✅ |
| `src/bot/karthik_api/repo.py` | 608 | `466e0138c4…` | ✅ |
| `src/bot/karthik_api/backends.py` | 96 | `f292f5c3a7…` | ✅ |
| `src/bot/karthik_api/calc.py` | 674 | `d110178cfa…` | ✅ |
| `src/bot/karthik_api/seed.py` | 103 | `1df91fac88…` | ✅ |
| `src/tab/package.json` | 41 | `1314006f18…` | ✅ |
| `src/tab/vite.config.ts` | 34 | `71ea40dee6…` | ✅ |
| `src/tab/tsconfig.json` | 21 | `3797d0c42a…` | ✅ |
| `contracts/dashboard/dashboard.schema.json` | 131 | `5b68b00d48…` | ✅ |
| `db/001_create_tables.sql` | 106 | `fd7ac450f9…` | ✅ |
| `db/002_seed_data.sql` | 37 | `362cdbd170…` | ✅ |
| `.env` | 6 | `56f72cad52…` | ✅ |
| `m365agents.yml` | 117 | `c0a1389cf7…` | ✅ |
| `m365agents.local.yml` | 74 | `cc9a24865f…` | ✅ |
| `m365agents.playground.yml` | 27 | `8c07af6981…` | ✅ |
| `AI_CODING_RULES.md` | 107 | `ca74933584…` | ✅ |
| `README.md` | 104 | `d3b7c173a1…` | ✅ |
| `contracts/dashboard/dashboard.example.json` | 112 | `e908149177…` | ✅ |
| `prompts/README.md` | 185 | `2b00a12582…` | ✅ |
| `prompts/compliance_agent/test_inputs/sample_draft_section.txt` | 7 | `b181b9ed3c…` | ✅ |
| `prompts/compliance_agent/v1.0.0.md` | 78 | `a91f7beaf9…` | ✅ |
| `prompts/context_architecture_mapping.txt` | 108 | `9e04154f8c…` | ✅ |
| `prompts/context_assumptions.txt` | 315 | `1dbb770c92…` | ✅ |
| `prompts/context_clarification_questions.txt` | 225 | `13611bbb83…` | ✅ |
| `prompts/context_coe_involved.txt` | 59 | `4b68ec8deb…` | ✅ |
| `prompts/context_current_state.txt` | 86 | `e1ad41c107…` | ✅ |
| `prompts/context_current_state_architecture.txt` | 766 | `b65a707d6d…` | ✅ |
| `prompts/context_current_state_architecture_diagram.txt` | 599 | `dc8a1d04e4…` | ✅ |
| `prompts/context_customer_dependencies.txt` | 299 | `a11b27b58f…` | ✅ |
| `prompts/context_document_score.txt` | 314 | `a719231301…` | ✅ |
| `prompts/context_effort_estimate.txt` | 366 | `33a4dd0a68…` | ✅ |
| `prompts/context_in_scope.txt` | 260 | `8ac6d087c5…` | ✅ |
| `prompts/context_out_of_scope.txt` | 299 | `1974b43e83…` | ✅ |
| `prompts/context_pain_areas.txt` | 71 | `dc5f1d01b1…` | ✅ |
| `prompts/context_roles.txt` | 96 | `cbf71dd272…` | ✅ |
| `prompts/context_summary.txt` | 61 | `d5108e4efe…` | ✅ |
| `prompts/context_target_architecture.txt` | 763 | `2fdb568176…` | ✅ |
| `prompts/context_target_architecture_diagram.txt` | 599 | `8799b68ee8…` | ✅ |
| `prompts/context_target_state.txt` | 88 | `733cff3942…` | ✅ |
| `prompts/context_work_breakdown.txt` | 384 | `08c065cd90…` | ✅ |
| `prompts/drafting_agent/test_inputs/sample_requirements.json` | 71 | `8fca99d4fe…` | ✅ |
| `prompts/drafting_agent/v1.0.0.md` | 65 | `a8e9ae1ccb…` | ✅ |
| `prompts/intake_agent/harborline_rfp_excerpt_expected.json` | 81 | `871fe799e4…` | ✅ |
| `prompts/intake_agent/sample_rfp_excerpt_expected.json` | 95 | `046a7c2df6…` | ✅ |
| `prompts/intake_agent/test_inputs/sample_rfp_excerpt.txt` | 18 | `8f6ed4cfd4…` | ✅ |
| `prompts/intake_agent/v1.0.0.md` | 74 | `38e38df668…` | ✅ |
| `prompts/publishing_agent/test_inputs/sample_approved_draft.json` | 28 | `cdf6ebea7b…` | ✅ |
| `prompts/publishing_agent/v1.0.0.md` | 83 | `6f73814e0a…` | ✅ |
| `prompts/retrieval_agent/test_inputs/sample_query.txt` | 1 | `1a372e14b2…` | ✅ |
| `prompts/retrieval_agent/v1.0.0.md` | 79 | `82279713cd…` | ✅ |
| `src/bot/README.md` | 64 | `8a12d07a4c…` | ✅ |
| `src/bot/cards/__init__.py` | 1 | `78134a42a1…` | ✅ |
| `src/bot/karthik_api/__init__.py` | 1 | `3ea94ec258…` | ✅ |
| `src/bot/test_bot.py` | 753 | `95d3787f4d…` | ✅ |
| `src/bot/test_karthik_api.py` | 129 | `fa05578a96…` | ✅ |
| `src/tab/src/App.test.tsx` | 366 | `8fe916211d…` | ✅ |
| `src/tab/src/App.tsx` | 97 | `18003a8772…` | ✅ |
| `src/tab/src/api.ts` | 107 | `468a24ce58…` | ✅ |
| `src/tab/src/components/AnalyzeBar.tsx` | 25 | `41600a49e5…` | ✅ |
| `src/tab/src/components/ChatSection.tsx` | 81 | `53658660b1…` | ✅ |
| `src/tab/src/components/EditableGrid.tsx` | 87 | `308d14f9d4…` | ✅ |
| `src/tab/src/components/Expander.tsx` | 23 | `1a04d058e9…` | ✅ |
| `src/tab/src/components/Gantt.tsx` | 86 | `d412462ae7…` | ✅ |
| `src/tab/src/components/SectionPanel.tsx` | 16 | `2c7cbcd9da…` | ✅ |
| `src/tab/src/main.tsx` | 10 | `2faed4d237…` | ✅ |
| `src/tab/src/pages/ArchitectureTab.tsx` | 195 | `42f841075d…` | ✅ |
| `src/tab/src/pages/EstimatesTab.tsx` | 336 | `4dea18c3b6…` | ✅ |
| `src/tab/src/pages/OverviewTab.tsx` | 103 | `e8c66dd823…` | ✅ |
| `src/tab/src/pages/ProposalsPage.tsx` | 126 | `2b734c9d97…` | ✅ |
| `src/tab/src/pages/ScopeTab.tsx` | 18 | `91b83e0eac…` | ✅ |
| `src/tab/src/pages/SettingsTab.tsx` | 152 | `c78987dfc6…` | ✅ |
| `src/tab/src/pages/Workspace.tsx` | 92 | `59d787a4cf…` | ✅ |
| `src/tab/src/pages/types.ts` | 10 | `b83bf6fe03…` | ✅ |
| `src/tab/src/styles.css` | 173 | `d4fa319a35…` | ✅ |
| `src/tab/src/teams.ts` | 41 | `bc8b778c30…` | ✅ |
| `src/tab/src/test/setup.ts` | 1 | `2b9a2baf78…` | ✅ |
| `src/tab/src/vite-env.d.ts` | 9 | `2ecaa7b5f2…` | ✅ |
<!-- CHECKSUMS_END -->
