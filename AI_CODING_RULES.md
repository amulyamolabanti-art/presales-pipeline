# AI‑Assisted Coding Rules (Human‑Centric Version)

> **Sprint 0 | S0‑CM‑03 | Backlog: CM‑04**  
> Status: **Active** — Effective from 2026‑11‑05  
> Applies to: All contributors to the `ai‑proposal‑assistant` repository  
> Reviewed at: 9 Nov 2026 Sprint 0 Check‑in  
> Next review: Sprint 1 planning

---

## Why These Rules Exist

Our team writes code and maintains prompts **by hand**.  
Even though we do not rely on external AI generators for code or prompts, we still need clear guidelines to keep client data and secrets safe and to ensure a disciplined review process.

---

## Rule 1 — No Client Data in Prompts or Code

> ⚠️ **Never include client‑specific information** in any file that is version‑controlled.

**Client data includes**:
- Client names, company identifiers, contact details
- Opportunity IDs, deal values, pricing information
- Any excerpt from a real RFP or client communication
- Custom configuration values that belong to a specific client

**What to do instead:**
- Replace real values with placeholders such as `[CLIENT_NAME]`, `[OPPORTUNITY_ID]`, `[DEAL_VALUE]`.
- Keep test data in `prompts/*/test_inputs/` anonymised.

---

## Rule 2 — No Secrets in the Repository

> ⛔ **Never commit credentials, API keys, tokens, connection strings, or certificates**.

**If a secret is accidentally added:**
1. Remove it immediately and commit the fix.
2. Rotate the secret (create a new one) as soon as possible.
3. Notify the AI Engineering Lead and your manager.

All real secrets must live in **Azure Key Vault** and be accessed at runtime, never stored in source code or configuration files.

---

## Rule 3 — IT Governance Gate (Items #47‑#49)

Three IT items must be cleared before any **production** deployment:

| IT Item | Description | Status |
|---|---|---|
| **#47** | Data Processing Agreement with any external service provider | ⏳ Pending |
| **#48** | Information‑security risk assessment for the solution | ⏳ Pending |
| **#49** | GDPR / data‑residency compliance review | ⏳ Pending |

**Until approved:**
- All work is limited to the local development environment (e.g., the Microsoft 365 Agents Playground).
- Prompt files must have `it_clearance: pending` in their front‑matter.
- No production‑ready code may be merged that relies on external AI services.

---

## Rule 4 — Prompt Changes Require PR Review

All modifications inside `prompts/` must go through a Pull Request and be approved by **at least two reviewers** (domain reviewer and safety reviewer). See the updated [`prompts/README.md`](../prompts/README.md) for the full checklist.

---

## Rule 5 — Human‑Reviewed Code

Every line of code that enters the repository must be **understood and approved** by the author:
- Verify that no hidden client data or secrets are introduced.
‑‑ Review any authentication or data‑access logic carefully.
- Ensure that code follows the existing architecture (see `README.md`).

---

## Rule 6 — Approved Tooling Only

The team may use the following developer tools for **manual** work:
- **VS Code** with the Microsoft 365 Agents Toolkit extension (for local simulation)
- **Git** and **GitHub** for version control and PR workflows
- **Static analysis** tools (e.g., `flake8`, `eslint`) that run locally

Any other AI‑assisted coding assistants (e.g., Copilot, Gemini chat) are **not permitted** for this repository until the IT items are approved.

---

## Rule 7 — Incident Reporting

If client data or a secret is ever exposed, follow these steps immediately:
1. Stop the activity that caused the leak.
2. Rotate the secret (if applicable).
3. Notify the AI Engineering Lead and your manager.
4. Log the incident in the security‑incident tracker (Teams `#security‑incidents` channel).

---

## Acknowledgement

By contributing to this repository, you confirm that you have read and will follow these rules.  
Questions? Raise a discussion in `#ai-proposal-assistant` on Teams or open an issue in the repo.

---

*This document is version‑controlled; any change requires a PR approved by the AI Engineering Lead and the Pre‑sales Lead.*
