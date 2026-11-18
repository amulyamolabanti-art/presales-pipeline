# Infrastructure as Code (Bicep Baseline & Modular Architecture)

This directory contains the Bicep modular infrastructure templates and environment parameter files for the **Proposal AI / Presales Assistant** solution.

---

## 1. Directory Structure

```text
/infra
├── modules/
│   ├── document-intelligence.bicep     # Document Intelligence (FormRecognizer, keyless, IP-restricted)
│   ├── keyvault.bicep                  # Key Vault (Entra RBAC, keyless, IP-restricted)
│   ├── openai.bicep                    # Azure OpenAI Service (keyless, IP-restricted)
│   ├── search.bicep                    # Azure AI Search (GA, keyless, IP-restricted)
│   ├── sql.bicep                       # Azure SQL Logical Server + Serverless DB (Entra-only auth, IP firewall)
│   └── storage.bicep                   # Storage Account (OAuth-only, keyless, IP-restricted, app containers)
├── main.bicep                          # Core orchestrator baseline template composing all modules
├── main.dev.bicepparam                 # Bicep parameters for Development
├── main.prod.bicepparam                # Bicep parameters for Production
└── README.md                           # Architecture, naming, tagging, and deployment guide
```

*(Note: Per repository standards, native `.bicepparam` parameter files are used; compiled ARM JSON parameter files are not checked in).*

---

## 2. Naming Conventions (Azure Cloud Adoption Framework)

Resources are structured following standard Microsoft Azure naming patterns:
`<resource-type>-<workload>-<environment>-<location>`

| Resource Type | Resource Prefix | Dev Example | Notes |
| :--- | :--- | :--- | :--- |
| **Resource Group** | `rg-` | `rg-proposal-ai-dev` | Provisioned by IT Platform Team |
| **User Managed Identity** | `id-` | `id-proposal-ai-dev-eastus2` | Keyless / passwordless auth |
| **Azure Bot Service** | `bot-` | `bot-proposal-ai-dev-eastus2` | Global registration + Teams channel |
| **Functions Flex Plan**| `plan-` | `plan-proposal-ai-dev-eastus2` | Flex Consumption (`FC1` SKU) |
| **Function App** | `func-` | `func-proposal-ai-dev-eastus2` | Linux runtime on Node.js 22 |
| **Key Vault** | `kv-` | `kv-proposal-ai-dev-001` | Entra RBAC enabled, key-based auth disabled (max 24 chars) |
| **Storage Account** | `st` | `stproposaldeveastus2001` | OAuth-only, shared key access disabled, suffix `001` preserved |
| **Azure OpenAI Service** | `oai-` | `oai-proposal-ai-dev-eastus2` | Keyless auth (`disableLocalAuth: true`), IP-restricted |
| **Azure AI Search (GA)**| `srch-` | `srch-proposal-ai-dev-eastus2` | GA API (`2023-11-01`), keyless auth (`disableLocalAuth: true`), IP-restricted |
| **Document Intelligence**| `di-` | `di-proposal-ai-dev-eastus2` | FormRecognizer, keyless auth (`disableLocalAuth: true`), IP-restricted |
| **Azure SQL Server** | `sql-` | `sql-proposal-ai-dev-eastus2-001` | Entra ID-only auth (no local SQL passwords), corporate IP firewall |
| **Azure SQL Database** | `sqldb-` | `sqldb-proposal-ai-dev` | Serverless General Purpose (`GP_S_Gen5_1`), auto-pause enabled |
| **Log Analytics** | `log-` | `log-proposal-ai-dev-eastus2` | Centralized log workspace |
| **Application Insights** | `appi-` | `appi-proposal-ai-dev-eastus2` | Telemetry & diagnostics |

### Storage Account Name Calculation Rule
Azure Storage accounts require 3–24 lowercase alphanumeric characters. To prevent the `001` suffix from ever being truncated:
```bicep
var cleanWorkload = take(replace(replace(workloadName, '-', ''), 'ai', ''), 8) // 'proposal' (8 chars)
var storageBase = take('st${cleanWorkload}${environment}${cleanLocation}', 18)  // max 18 chars
var storageAccountName = '${storageBase}${instanceSuffix}'                     // 18 + 3 = 21 chars (Dev)
```
- **Dev example:** `stproposaldeveastus2001` (21 characters)
- **Prod example:** `stproposalprodeastus2001` (22 characters)
- The suffix `001` is guaranteed to stay intact across all environments and regions.

---

## 3. Security Architecture (Zero-Trust & Passwordless Baseline)

Per enterprise security policy:
1. **Key-Based Authentication Disabled**:
   - **Storage Account**: `allowSharedKeyAccess: false` and `defaultToOAuthAuthentication: true` (disables account keys; forces Entra ID tokens).
   - **Key Vault**: `enableRbacAuthorization: true` (disables legacy access policies; governed strictly via Entra ID RBAC).
   - **Azure OpenAI**: `disableLocalAuth: true` (API keys disabled; Entra ID bearer tokens required).
   - **Document Intelligence**: `disableLocalAuth: true` (API keys disabled; Entra ID bearer tokens required).
   - **Azure AI Search**: `disableLocalAuth: true` and `aadOrApiKey` with `http401WithBearerChallenge` (API keys disabled).
   - **Azure SQL**: `administrators.azureADOnlyAuthentication: true` (local SQL authentication completely disabled; no local admin passwords).
2. **Network Perimeter Hardening**:
   - All modules implement default-deny network access (`defaultAction: 'Deny'` or firewall rule whitelists).
   - Ingress is restricted to corporate IP CIDR ranges parameterized in `corporateIpRanges` / `sqlCorporateFirewallRules`.
   - `bypass: 'AzureServices'` / `allowAzureServices: true` ensures authenticated Azure platform services (e.g. Function App, Bot Service) communicate securely with downstream resources.
3. **Role Assignments (RBAC)**:
   - The User-Assigned Managed Identity (`id-...`) is granted least-privilege roles across provisioned modules:
     - `Storage Blob Data Owner` on Storage Account
     - `Key Vault Secrets User` on Key Vault
     - `Cognitive Services OpenAI User` on Azure OpenAI
     - `Search Index Data Contributor` on Azure AI Search
     - `Cognitive Services User` on Document Intelligence

---

## 4. Tagging Strategy

Every resource inherits standard governance tags combined with environment-specific overrides:

| Tag | Purpose | Dev Value | Prod Value |
| :--- | :--- | :--- | :--- |
| `Environment` | Tier classification | `dev` | `prod` |
| `Project` | Project identity | `Proposal AI` | `Proposal AI` |
| `Workload` | Application component | `AI Proposal Assistant` | `AI Proposal Assistant` |
| `ManagedBy` | Infrastructure management tool | `Bicep` | `Bicep` |
| `Owner` | Responsible team | `Presales Dev Team` | `Presales Operations` |
| `CostCenter` | Billing attribution | `Presales-Innovation-Dev` | `Presales-Production` |

---

## 5. Offline Verification (Build & Lint)

Run offline validation without connecting to an Azure subscription:

```bash
# 1. Lint all modular Bicep templates
bicep lint infra/modules/openai.bicep
bicep lint infra/modules/search.bicep
bicep lint infra/modules/sql.bicep
bicep lint infra/modules/storage.bicep
bicep lint infra/modules/keyvault.bicep
bicep lint infra/modules/document-intelligence.bicep

# 2. Lint and build main template to verify compilation
bicep lint infra/main.bicep
bicep build infra/main.bicep

# 3. Validate parameter compilation
bicep build-params infra/main.dev.bicepparam
bicep build-params infra/main.prod.bicepparam
```

---

## 6. Deployment & RBAC (Once Resource Group Exists)

Once IT / Azure platform provisions `rg-proposal-ai-dev` (region to confirm with IT, e.g., East US 2):

### RBAC Pre-requisites
- Contributor access on `rg-proposal-ai-dev` for `sg-proposal-ai-dev`.

### Deployment Command (Azure CLI)
```bash
# Dry-run What-If preview
az deployment group what-if \
  --resource-group rg-proposal-ai-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.dev.bicepparam

# Execute deployment
az deployment group create \
  --resource-group rg-proposal-ai-dev \
  --template-file infra/main.bicep \
  --parameters infra/main.dev.bicepparam
```
