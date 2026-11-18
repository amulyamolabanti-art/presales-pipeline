# `/prompts` — Agent Prompt Library

> **Sprint 0 | S0-CM-03 | Backlog: CM-04**  
> Owner: Pre-sales Engineering Team  
> Last updated: 2026-11-05

---

## Purpose

This directory contains **every system prompt** used by the AI agents inside the **AI Proposal Assistant**.  
Keeping prompts here — not scattered across source code — means:

- Changes are **visible in git diff**, reviewable in PRs, and fully auditable.
- Each prompt is **versioned independently** so agents can be rolled back without a code deploy.
- **Test inputs** ship alongside prompts so reviewers can replay expected behaviour before merging.

---

## Directory Layout

```
prompts/
├── README.md                        ← You are here
├── intake_agent/
│   ├── v1.0.0.md                    ← System prompt (current)
│   └── test_inputs/
│       └── sample_rfp_excerpt.txt   ← Representative input for manual / automated testing
├── retrieval_agent/
│   ├── v1.0.0.md
│   └── test_inputs/
│       └── sample_query.txt
├── drafting_agent/
│   ├── v1.0.0.md
│   └── test_inputs/
│       └── sample_requirements.json
├── compliance_agent/
│   ├── v1.0.0.md
│   └── test_inputs/
│       └── sample_draft_section.txt
└── publishing_agent/
    ├── v1.0.0.md
    └── test_inputs/
        └── sample_approved_draft.txt
```

---

## Prompt File Format

Every prompt file (`vX.Y.Z.md`) must include the following YAML front-matter block at the top:

```yaml
---
agent:        <agent name>          # e.g. intake_agent
version:      <semver>              # e.g. 1.0.0
status:       draft | review | stable
author:       <name>
date:         YYYY-MM-DD
model_target: <model name>          # e.g. gpt-4o, gemini-1.5-pro
it_clearance: pending | approved    # reflects IT items #47–#49
change_log:
  - version: 1.0.0
    date: YYYY-MM-DD
    summary: Initial prompt
---
```

The body of the file is the **raw system prompt text** fed to the model at runtime.

---

## Versioning Convention

| Semver part | When to bump |
| :---------- | :----------- |
| **PATCH** (0.0.**x**) | Wording/typo fixes that do not change agent behaviour |
| **MINOR** (0.**x**.0) | New instructions added; backward-compatible behaviour change |
| **MAJOR** (**x**.0.0) | Breaking change — different output schema, role, or tone |

Always create a **new file** for a new version. Do **not** overwrite the previous version.  
The runtime loader picks the highest stable version by default.

---

## Test Inputs

Every prompt directory must contain a `test_inputs/` subdirectory with at least one representative input.

| Test file | Purpose |
| :-------- | :------ |
| `sample_*.txt / .json` | Minimal realistic input that exercises the prompt's core logic |
| `edge_case_*.txt` *(optional)* | Inputs that stress boundary conditions (empty RFP, missing fields, etc.) |

**Run test inputs manually during development:**

```bash
# Example — pipe a test input through the prompt locally
python src/agents/run_prompt.py \
  --prompt prompts/intake_agent/v1.0.0.md \
  --input  prompts/intake_agent/test_inputs/sample_rfp_excerpt.txt
```

---

## How Prompts Are Reviewed in Pull Requests

### 1. Raise a PR with only prompt changes
Keep prompt-only changes in a **dedicated branch** (`feat/prompt-<agent>-v<version>`) so reviewers can focus on the text without code noise.

### 2. Required reviewers
Every prompt PR needs **at least two approvals**:

| Reviewer role | Who |
| :------------ | :-- |
| **Domain reviewer** | Bid Owner or Pre-sales Lead (Rukul / Prince / Ajit) — validates correctness of instructions |
| **AI safety reviewer** | AI Engineering Lead — validates no data-leakage risks, grounding rules, hallucination guards |

### 3. PR checklist (copy into PR description)

```
## Prompt PR Checklist

### Content
- [ ] Front-matter is complete and accurate (agent, version, status, author, date, model_target)
- [ ] `change_log` entry added with a plain-English summary of what changed and why
- [ ] New version file created — previous version file untouched

### Safety & Compliance
- [ ] Prompt contains NO client names, client data, or real opportunity details
- [ ] Prompt contains NO secrets, API keys, tokens, or connection strings
- [ ] `it_clearance` field is set correctly (pending / approved)
  - If pending: prompt is merged only to `develop` branch; NOT deployed to production
    until IT items #47, #48, and #49 are approved
- [ ] Prompt instructions do NOT instruct the model to bypass grounding or hallucination guards

### Testing
- [ ] At least one test input file exists in `test_inputs/`
- [ ] Test input was run locally and the sample output is pasted in the PR description
- [ ] No sensitive data appears in the sample output pasted in the PR

### Housekeeping
- [ ] Branch name follows convention: `feat/prompt-<agent>-v<version>`
- [ ] PR title follows: `[Prompt] <agent_name>: v<version> — <one-line summary>`
```

### 4. Merge rules
- Squash-merge into `develop`; rebase into `main` only after IT clearance is fully approved.
- Do not force-push to any branch containing a released prompt version.

### 5. Deployment gate
> ⚠️ IT items #47, #48, and #49 must be approved before any prompt is loaded in the
> production environment.  
> Until approved, prompts are tested only in the local Microsoft 365 Agents Playground.

---

## Quick Reference — Adding a New Prompt Version

```bash
# 1. Branch off develop
git checkout develop
git pull
git checkout -b feat/prompt-drafting_agent-v1.1.0

# 2. Copy previous version as starting point
cp prompts/drafting_agent/v1.0.0.md prompts/drafting_agent/v1.1.0.md

# 3. Edit the new file — bump version in front-matter, add change_log entry

# 4. Add or update test inputs
#    prompts/drafting_agent/test_inputs/sample_requirements.json

# 5. Run test locally and capture output
python src/agents/run_prompt.py \
  --prompt prompts/drafting_agent/v1.1.0.md \
  --input  prompts/drafting_agent/test_inputs/sample_requirements.json > /tmp/output_v1.1.0.txt

# 6. Open PR — paste /tmp/output_v1.1.0.txt into PR description
```

---

*For questions about this process, raise a discussion in `#ai-proposal-assistant` on Teams
or tag `@AI-Engineering` in your PR.*
