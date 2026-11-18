# Evaluation Benchmark & Golden Set (`/eval`)



## 1. Purpose of the Golden Set
The Golden Set is Ascendion's ground-truth benchmark suite for the **AI Proposal Assistant**. It evaluates whether the AI:
1. **Accurately answers client questions** using only retrieved source RFP documents.
2. **Cites exact sources** (document name, section number, and page).
3. **Refuses to hallucinate** by returning *"Not found in sources"* whenever a requirement is missing from the RFP.

---

## 2. File Directory
* `golden_set_template.json` — The official JSON schema definition.
* `golden_set_questions.json` — 15 drafted evaluation questions formatted for programmatic test runners .
* `golden_set_questions.csv` — Excel-ready spreadsheet for pre-sales reviewer sessions.

---

## 3. Schema Structure

Each test case contains the following required fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | string | Unique test case identifier (e.g., `GT-001`) |
| `rfp_id` | string | ID of the source RFP (e.g., `SAMPLE-RFP-01-HARBORLINE`) |
| `category` | string | Domain (`Security & Compliance`, `Cloud Architecture`, `SLA & Support`, `Pricing & Commercial`, `Timeline & Milestones`, `Negative / Refusal Test`) |
| `question` | string | Question asked by a bid reviewer or solution architect |
| `expected_answer` | string | Ground-truth factual answer |
| `expected_source` | string | Exact citation (document name, section, page) |
| `is_not_found` | boolean | `true` for refusal trap questions; `false` for standard grounded questions |
| `reviewer_notes` | string | Review comments and sign-off notes |

---

## 4. Current Test Case Distribution (15 Questions)
* **Security & Compliance:** 3 test cases (`GT-001`, `GT-003`, `GT-007`)
* **Cloud Architecture:** 3 test cases (`GT-002`, `GT-006`, `GT-010`)
* **SLA & Support:** 3 test cases (`GT-004`, `GT-005`, `GT-012`)
* **Timeline & Milestones:** 2 test cases (`GT-008`, `GT-011`)
* **Pricing & Commercial:** 1 test case (`GT-009`)
* **Negative / Trap Questions (`is_not_found = true`):** 3 test cases (`GT-013`, `GT-014`, `GT-015`)
