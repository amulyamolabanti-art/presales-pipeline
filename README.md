# Presales AI Solution (AI Proposal Assistant)

Sprint 0 baseline repository for the Presales AI Assistant solution.

---

## Technology Stack

- **Language / Runtime:** TypeScript on Node.js 22 LTS
- **Monorepo Architecture:** npm workspaces (`/src/bot`, `/src/orchestrator`, `/src/tab`, `/contracts`)
- **Infrastructure as Code:** Azure Bicep (Flex Consumption Function App, Azure Bot Service, Azure OpenAI, AI Search)
- **Database / Vector Store:** Azure SQL (Entra ID-only auth) & Azure AI Search

---

## Governance & Contribution Rules

- **Branch Protection Policy:** Direct pushes and commits to `main` are restricted.
- **Rule:** **PR only, 1 approval required** from the designated Code Owner (Track A / Track B Lead) prior to merging.
- **Pull Request Template:** Follow `.github/pull_request_template.md` and link the relevant Jira ticket (`APA-___`).

---

## Repository Structure

- `/infra` — Bicep baseline infrastructure manifests and `.bicepparam` files
- `/src/bot` — Microsoft Teams bot runtime and adapter (Python Teams App SDK scaffold)
- `/src/orchestrator` — AI agent orchestration and workflow pipeline
- `/src/tab` — Teams Tab frontend application (React 18 + Fluent UI v9 on Vite HTTPS)
- `/db` — Database migration scripts and schema definitions
- `/prompts` — Version-controlled prompt templates and system prompts
- `/eval` — Evaluation benchmarks and test harnesses
- `/contracts` — Shared TypeScript type definitions and API interfaces
- `/samples/rfp` — Synthetic RFP/RFI documents for local benchmarking and prototype testing
- `/env` — Baseline environment configuration templates (`.env.local`, `.env.playground`, `.env.dev`)

---

## Getting Started & Local Development

### 1. Prerequisites

- **Python 3.10+** (used for `/src/bot` runtime)
- **Node.js 20+ / 22 LTS** (used for Microsoft 365 Agents Toolkit tooling and front-end build pipelines)
- **VS Code** with the **Teams Toolkit / Microsoft 365 Agents Toolkit** extension

---

### 2. Initial Setup

1. **Clone the repository and open in VS Code:**
   ```bash
   git clone https://github.com/surendrareddy-alt/presales-app.git
   cd presales-app
   code .
   ```

2. **Configure Python Virtual Environment:**
   From the repository root:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r src/bot/requirements.txt
   ```

3. **Environment Files:**
   Baseline environment configurations are committed in `/env`:
   - `env/.env.local` — Local development settings
   - `env/.env.playground` — Playground simulator settings
   - `env/.env.dev` — Azure dev environment settings
   User secrets and individual tenant overrides are stored in `env/.env.*.user` files (which are gitignored).

---

### 3. Running & Debugging Locally (Zero-Cloud Blocker)

The bot is configured to run locally without requiring Azure cloud provisioning:

1. In VS Code, navigate to the **Run and Debug** panel (`Ctrl + Shift + D`).
2. Select **`Debug in Microsoft 365 Agents Playground`** from the configuration dropdown.
3. Press **`F5`** (or click the green Run arrow).
4. Teams Toolkit will launch:
   - The Python bot server on `http://localhost:3978`
   - The Microsoft 365 Agents Playground web simulator on `http://localhost:56150`
5. In the Playground browser window, send `hello` or `hi` to verify the bot responds:
   > *"Hello! How can I assist you today?"*

---

### 4. Teams Personal Tab Workspace (`/src/tab`)

- **Jira Task:** APA-37 (React 18 + Fluent UI v9 Starter Project)
- **Local Dev Server:** Runs strictly on **`https://localhost:53000`** over local HTTPS via Vite.
- **Commands:**
  ```bash
  cd src/tab
  npm install
  npm run dev          # Launch HTTPS dev server at https://localhost:53000
  npm run build        # Build production bundle into dist/
  npm test             # Run Vitest component tests non-interactively
  npm run type-check   # TypeScript compiler type-check
  npm run lint         # ESLint check
  ```
- Detailed setup instructions, certificate trust guides, and troubleshooting are documented in [`src/tab/README.md`](src/tab/README.md).
