# AI Proposal Assistant — Teams Personal Tab Frontend (`/src/tab`)

> **Jira Tasks:**  
> - APA-37: Scaffolding, Fluent UI v9 & Strict HTTPS  
> - APA-38: Teams Context, Mock Fallback & Dynamic Theming  
> - APA-39: API Client with Config-Based Base URL & Story 2 Contracts  
> **Status:** Operational  
> **Stack:** React 18, TypeScript, Fluent UI v9 (`@fluentui/react-components`), Microsoft Teams JS SDK v2, Vite, Vitest

This package contains the frontend Teams Personal Tab application for the **AI Proposal Assistant**. In Sprint 0, the application operates locally under a strict HTTPS development server (`https://localhost:53000`) with mock data, dynamic theme switching, and decoupled API client architecture.

---

## 1. Architecture: API Client & Story 2 Integration (APA-39)

The API client module in `/src/tab/src/api` provides a centralized, strongly typed HTTP transport and domain interface for proposal data:

```
+-----------------------------------------------------------------------------------+
|                        React Components (e.g. Dashboard)                          |
+-----------------------------------------------------------------------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
       getOpportunities(options?)             getDashboard(oppId, options?)
                      |                                       |
                      +-------------------+-------------------+
                                          |
                        +----------------------------------+
                        |   ProposalApiClient (Domain)     |
                        |   - Validates opportunityId      |
                        |   - Encodes path parameters      |
                        |   - Validates response schemas   |
                        |   - ZERO silent fallback         |
                        +----------------------------------+
                                          |
                        +----------------------------------+
                        |   HttpClient (HTTP Transport)    |
                        |   - Resolves VITE_API_BASE_URL   |
                        |   - Bounded timeout management   |
                        |   - AbortController cancellation |
                        |   - Typed error classification   |
                        +----------------------------------+
                                          |
                        +----------------------------------+
                        |       Native fetch (HTTP)        |
                        +----------------------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
     [Local Mock API (Port 5000)]                [Production Backend Gateway]
        Story 2 / APA-46 Server                  (Configured via Base URL)
```

### Key Principles
1. **Centralized Configuration:** All API URLs are derived from `VITE_API_BASE_URL`. Individual components never read `import.meta.env` directly.
2. **Safe URL Construction & Encoding:** Paths handle trailing/leading slashes deterministically (`buildUrl`). Opportunity IDs with slashes or spaces are strictly percent-encoded (`encodeURIComponent`).
3. **No Silent Fallback on Failure:** When an HTTP 404, 500, or network error occurs, the client throws a typed error (`ApiHttpError`, `ApiNetworkError`, etc.). It **never silently swaps in fake fixtures** on failure.
4. **Cancellation & Timeout Support:** Every call supports caller `AbortSignal` and configurable request deadlines. Timers and listeners are cleaned up deterministically in `finally` blocks.
5. **Contract Conformance:** Dashboard responses are validated against `/contracts/dashboard/dashboard.schema.json`.

---

## 2. Configuration (`.env` and `VITE_API_BASE_URL`)

### Environment Setup
Create a `.env` or `.env.local` file inside `/src/tab` (template provided in `.env.example`):

```bash
# In /src/tab/.env
VITE_API_BASE_URL=http://localhost:5000
```

### Important Vite Notes
* **Build-Time Injection:** In Vite, variables prefixed with `VITE_` are injected at build/start time.
* **Server Restart Requirement:** If you modify `.env` or `.env.local`, you **must restart the Vite dev server** (`npm run dev`) or re-run `npm run build` for the new URL to take effect.
* **Missing Config Error:** If `VITE_API_BASE_URL` is missing, empty, or uses an unsupported protocol, the client immediately throws `ApiConfigError` with clear setup instructions.

---

## 3. Client Usage Guide (For Dashboard Integration)

Developers (including Yasaswini for dashboard integration) should import from `@/api`:

```typescript
import {
  getOpportunities,
  getDashboard,
  isApiHttpError,
  isApiNetworkError,
  isApiTimeoutError,
  isApiAbortError,
  OpportunitySummary,
  ProposalDashboard,
} from './api';

// 1. Fetching all opportunities
async function loadOpportunities() {
  try {
    const opportunities: OpportunitySummary[] = await getOpportunities();
    console.log(`Loaded ${opportunities.length} opportunities:`, opportunities);
  } catch (error) {
    if (isApiNetworkError(error)) {
      console.error('Cannot connect to mock API server (offline or CORS).');
    }
  }
}

// 2. Fetching dashboard for a specific opportunity
async function loadDashboard(opportunityId: string) {
  const controller = new AbortController();

  try {
    const dashboard: ProposalDashboard = await getDashboard(opportunityId, {
      signal: controller.signal,
      timeoutMs: 8000,
    });

    console.log('Opportunity Client:', dashboard.opportunityMetadata.clientName);
    console.log('KPI Completeness:', dashboard.kpis.completenessScore);
    console.log('Open Gaps:', dashboard.kpis.openGapsCount);
    console.log('Analysis Cards:', dashboard.analysisCards);
  } catch (error) {
    if (isApiHttpError(error) && error.status === 404) {
      console.warn(`Opportunity ${opportunityId} not found in database.`);
    } else if (isApiAbortError(error)) {
      console.log('User navigated away; request cancelled.');
    } else if (isApiTimeoutError(error)) {
      console.error('API request timed out.');
    }
  }
}
```

---

## 4. Contract Specifications: Confirmed vs Provisional

| Endpoint / Field | Source / Authority | Status | Notes |
| :--- | :--- | :--- | :--- |
| `GET /opportunities` | Story 2 Specification (`mock_api.py`) | **Confirmed** | Returns array of `OpportunitySummary` objects. |
| `GET /opportunities/{id}/dashboard` | `/contracts/dashboard/dashboard.schema.json` | **Confirmed** | Returns `ProposalDashboard` matching SQL schema & agent contracts. |
| `opportunityId` | Schema required property | **Confirmed** | Pattern: `^OPP-[0-9]{4}-[0-9A-Za-z_-]+$`. |
| `kpis.completenessScore` | Intake agent output summary | **Confirmed** | Number (0.0 to 100.0). |
| `kpis.estimatedValue` | Business requirement | *Provisional* | Marked "TBD with Srigopal" in schema; optional string. |
| `kpis.winProbability` | Business requirement | *Provisional* | Marked "TBD with Srigopal" in schema; optional string. |
| `POST /assistant/ask` | Story 2 (APA-47) | *Out of Scope* | Chat assistant endpoint; owned by Story 2. |

---

## 5. Mock API Startup & Integration Testing

The mock API server is authored under Story 2 (APA-46). When running Story 2 locally:

```bash
# 1. Start the Story 2 Mock API (from repo root or /src/tab)
python src/tab/mock_api.py

# Expected output:
# [INFO] Mock API Server running at http://localhost:5000
```

### Verified Endpoints:
* `http://localhost:5000/opportunities` $\rightarrow$ Returns 2 seeded opportunities (`OPP-2026-HARBORLINE-01`, `OPP-2026-VELORA-02`).
* `http://localhost:5000/opportunities/OPP-2026-HARBORLINE-01/dashboard` $\rightarrow$ Returns Harborline Claims Modernisation dashboard.
* `http://localhost:5000/opportunities/OPP-2026-VELORA-02/dashboard` $\rightarrow$ Returns Velora Search Managed Services dashboard.
* `http://localhost:5000/opportunities/UNKNOWN/dashboard` $\rightarrow$ Returns HTTP 404 with JSON error body.

---

## 6. Integration Status: Verified vs Pending

* **Unit & Transport Verification: [VERIFIED]**  
  45 automated tests pass in Vitest covering base URL resolution, trailing slash handling, ID encoding, status code evaluation, JSON parsing, error classification, caller cancellation, timeout cleanup, and validation errors.
* **Story 2 Mock API Conformance: [VERIFIED]**  
  Tested live against `mock_api.py` (APA-46) running on `http://localhost:5000`. Requests to `/opportunities` and `/opportunities/OPP-2026-HARBORLINE-01/dashboard` return 200 OK with expected JSON payloads.
* **Remote CI & PR Merge: [PENDING]**  
  Integration is staged on feature branch `feat/apa-39-api-client` awaiting PR creation, GitHub Actions CI validation, and Story 2 PR merge into `main`.

---

## 7. Development & Validation Scripts

| Command | Purpose | Behavior |
| :--- | :--- | :--- |
| `npm test` | **Run Unit & API Tests** | Executes 45 Vitest tests covering API client, Teams context, and UI components. |
| `npm run type-check` | **Type Checking** | Runs `tsc --noEmit` to verify all domain contracts and types. |
| `npm run lint` | **Linting** | Runs ESLint across all `.ts` and `.tsx` source files with `--max-warnings 0`. |
| `npm run build` | **Production Build** | Runs type-checking and compiles optimized bundle into `dist/`. |
| `npm run dev` | **Start Dev Server** | Launches HTTPS dev server on `https://localhost:53000` with strict-port validation. |

---

## 8. Directory Structure

```text
src/tab/
├── .env.example              # Environment variables template (VITE_API_BASE_URL)
├── .eslintrc.cjs             # ESLint configuration for React & TypeScript
├── index.html                # Vite HTML entry point (includes Teams JS SDK v2 CDN)
├── package.json              # Package manifest and npm scripts
├── package-lock.json         # Pinned dependency lockfile
├── tsconfig.json             # TypeScript project compiler configuration
├── tsconfig.node.json        # TypeScript configuration for Vite tooling
├── vite.config.ts            # Vite & Vitest configuration (port 53000, HTTPS, strictPort)
├── README.md                 # Complete operational guide
└── src/
    ├── vite-env.d.ts         # Vite client environment type definitions
    ├── App.tsx               # Root component composing Context & Theme providers
    ├── App.test.tsx          # StarterScreen integration tests
    ├── main.tsx              # React DOM entry point
    ├── api/                  # APA-39: Centralized API Client Module
    │   ├── apiConfig.ts      # Base URL resolution & validation
    │   ├── errors.ts         # Typed error classes (HTTP, Network, Timeout, Abort, Validation)
    │   ├── httpClient.ts     # Reusable fetch transport with timeout & cancellation
    │   ├── types.ts          # Domain contracts (OpportunitySummary, ProposalDashboard)
    │   ├── proposalApiClient.ts # Domain methods (getOpportunities, getDashboard)
    │   ├── index.ts          # Clean public barrel export
    │   └── __tests__/
    │       ├── apiClient.test.ts # Comprehensive transport & domain unit tests
    │       └── liveIntegration.test.ts # Live integration tests against Story 2 mock server
    ├── components/
    │   └── StarterScreen.tsx # Starter screen displaying Teams context & dev switcher
    ├── context/              # APA-38: Teams Context & Mock Fallback
    ├── theme/                # APA-38: Fluent UI Theme Provider & Switcher
    └── test/                 # Test setup and Teams context tests
```
