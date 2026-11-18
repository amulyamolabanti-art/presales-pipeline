# Technical Specification: Spoke VNet, Subnets & Hub Peering (Network Team Ticket)

**Project:** Presales AI Solution / AI Proposal Assistant  
**Sprint 0 Task:** S0-SR-05 | **Backlog Story:** SR-03  
**Target Recipient:** Karthik Valluri (`karthik.valluri@ascendion.com`), IT Azure Platform / Network Team  
**Date:** November 2026  

---

## 1. Overview & Business Context

This specification outlines the networking requirements for the **Proposal AI** workload spoke virtual network (`vnet-proposal-ai-dev`). 

In later development phases (W9–W10), all AI platform and data services (Azure OpenAI, Azure AI Search, Azure SQL, Document Intelligence, Storage, Key Vault) will be isolated behind Azure Private Endpoints and peered to the central Ascendion corporate hub network. Raising this change ticket in Sprint 0 ensures the enterprise network team has sufficient lead time for IP allocation, peering configuration, and firewall routing.

---

## 2. Spoke Virtual Network Architecture

- **Proposed Resource Group:** `rg-proposal-ai-dev` (or network-dedicated resource group as per IT policy)
- **VNet Name:** `vnet-proposal-ai-dev-{location}` (e.g., `eastus2`, region to confirm with IT Platform Team)
- **Proposed Address Space:** **`/24` CIDR block (256 IP addresses)**
  - *Network Team Action:* Allocate a non-overlapping `/24` prefix from the enterprise cloud address pool (e.g. `10.240.10.0/24`).

```
Spoke VNet (10.240.x.0/24 - 256 Total IPs)
├── snet-app   (10.240.x.0/26)    --> 64 IPs (Functions Flex Consumption VNet Integration)
├── snet-pe    (10.240.x.64/26)   --> 64 IPs (Private Endpoints for Data & AI Services)
├── snet-apim  (10.240.x.128/27)  --> 32 IPs (API Management / Application Gateway Ingress WAF)
└── Available  (10.240.x.160/27+) --> 96 IPs (Reserved for future expansion / DR parity)
```

---

## 3. Subnet Allocations & Service Delegations

| Subnet Name | Proposed CIDR | Total / Usable IPs | Service Delegation | Purpose |
| :--- | :---: | :---: | :---: | :--- |
| **`snet-app`** | `10.240.x.0/26` | 64 / 59 | **`Microsoft.Web/serverfarms`** | Outbound VNet integration for Azure Functions Flex Consumption (Node.js 22 runtime). |
| **`snet-pe`** | `10.240.x.64/26` | 64 / 59 | **None** | Dedicated private endpoints for all AI and data services. Private Endpoint Network Policies enabled. |
| **`snet-apim`** | `10.240.x.128/27` | 32 / 27 | **None** | Ingress API Management / Application Gateway WAF endpoint. |
| *Spare / Expansion* | `10.240.x.160/27`+ | 96 / 91 | — | Reserved for production scaling or disaster recovery. |

---

## 4. Azure Private DNS Zones & Resolution

The following **7 Azure Private DNS Zones** must be linked to `vnet-proposal-ai-dev` and the central hub DNS infrastructure to enable seamless name resolution:

| Service | Target Private Endpoint | Required Azure Private DNS Zone |
| :--- | :--- | :--- |
| **Azure OpenAI** | `oai-proposal-ai-dev-*` | `privatelink.openai.azure.com` |
| **Azure AI Search** | `srch-proposal-ai-dev-*` | `privatelink.search.windows.net` |
| **Document Intelligence** | `di-proposal-ai-dev-*` | `privatelink.cognitiveservices.azure.com` |
| **Key Vault** | `kv-proposal-ai-dev-*` | `privatelink.vaultcore.azure.net` |
| **Storage Account (Blobs)** | `stproposaldev*` | `privatelink.blob.core.windows.net` |
| **Storage Account (Queues)** | `stproposaldev*` | `privatelink.queue.core.windows.net` |
| **Azure SQL Database** | `sql-proposal-ai-dev-*` | `privatelink.database.windows.net` |

*Note: Central DNS forwarders in the Hub must resolve these private zones for workstations connected via corporate VPN/ExpressRoute.*

---

## 5. Egress Needs (Outbound Firewall Allow-list)

Outbound internet egress from `snet-app` will be forced through the Hub Azure Firewall or central NAT Gateway (`0.0.0.0/0` UDR). The following outbound endpoints must be allow-listed on port **443 (HTTPS)**:

| Destination FQDN / Endpoint | Port | Protocol | Purpose / Description |
| :--- | :---: | :---: | :--- |
| **`graph.microsoft.com`** | 443 | HTTPS | Microsoft Graph API (SharePoint RFP intake, mailbox, and Teams change notifications). |
| **`login.microsoftonline.com`** | 443 | HTTPS | Microsoft Entra ID authentication, token acquisition, and Managed Identity federation. |
| **`*.botframework.com`** | 443 | HTTPS | Microsoft Teams bot channel messaging service (`smba.trafficmanager.net`, `api.botframework.com`). |
| **`management.azure.com`** | 443 | HTTPS | Azure Resource Manager (ARM) metadata and runtime health probes. |
| **`*.blob.core.windows.net`** | 443 | HTTPS | Azure deployment package storage (if not routed over private endpoint). |

---

## 6. Key Architectural Constraints & Ingress Rules

1. **Bot Messaging Endpoint (Public Ingress):**
   - Microsoft Teams cloud services require public HTTPS accessibility to invoke the bot webhook.
   - The Azure Bot Service messaging endpoint (`/api/messages`) must remain accessible from the internet or be protected via an internet-facing **Application Gateway / APIM with WAF** in front of the private spoke.
2. **Data Services Isolation:**
   - Azure OpenAI, Search, SQL, and Storage will have public network access strictly disabled once private cut-over occurs in W9.
3. **Hub Peering:**
   - Two-way VNet peering: `hub-vnet` $\leftrightarrow$ `vnet-proposal-ai-dev`
   - Allow forwarded traffic and use remote gateways (if hub hosts VPN / ExpressRoute gateway).
