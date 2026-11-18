"""Constants ported from Srigopal's rfp_core.py so labels, columns and defaults match his app."""

RFP_FIELDS = [
    "document_score",
    "clarification_questions",
    "summary",
    "current_state",
    "target_state",
    "pain_areas",
    "coe_involved",
    "current_state_architecture",
    "target_architecture",
    "architecture_mapping",
    "roles",
    "assumptions",
    "customer_dependencies",
    "in_scope",
    "out_of_scope",
    "work_breakdown",
    "effort_estimate",
]

TAB_FIELDS = {
    "overview": [
        "document_score",
        "clarification_questions",
        "summary",
        "current_state",
        "target_state",
        "pain_areas",
        "coe_involved",
    ],
    "scope": ["assumptions", "customer_dependencies", "in_scope", "out_of_scope"],
    "architecture": [
        "current_state_architecture",
        "target_architecture",
        "architecture_mapping",
        "roles",
    ],
    "estimates": ["work_breakdown", "effort_estimate"],
}

TABLE_FIELDS = {"clarification_questions", "architecture_mapping", "roles", "work_breakdown"}
STRUCTURED_FIELDS = TABLE_FIELDS | {"effort_estimate"}
TEXT_FIELDS = [f for f in RFP_FIELDS if f not in STRUCTURED_FIELDS]
# Rendered as formatted HTML panels (Overview + Scope); architecture texts are plain text areas.
FORMATTED_DISPLAY_FIELDS = {
    "document_score", "summary", "current_state", "target_state", "pain_areas", "coe_involved",
    "assumptions", "customer_dependencies", "in_scope", "out_of_scope",
}

SECTION_LABELS = {
    "document_score": "Document Score",
    "clarification_questions": "Questions for Clarifications",
    "summary": "Summary",
    "current_state": "Current State",
    "target_state": "Target State",
    "pain_areas": "Pain Areas",
    "coe_involved": "COE to be involved",
    "current_state_architecture": "Current State Architecture",
    "target_architecture": "Target State Architecture",
    "architecture_mapping": "Current State to Target State Architecture Mapping",
    "roles": "Roles",
    "assumptions": "Assumptions",
    "customer_dependencies": "Customer Dependencies",
    "in_scope": "In scope",
    "out_of_scope": "Out of Scope",
    "work_breakdown": "Work Breakdown",
    "effort_estimate": "Effort Estimate",
}

DIAGRAM_FIELDS = {
    "current_state_architecture": "current_state_architecture_diagram",
    "target_architecture": "target_architecture_diagram",
}
EXTRA_CONTEXT_FIELDS = {
    "current_state_architecture_diagram": "Current State Architecture Diagram",
    "target_architecture_diagram": "Target State Architecture Diagram",
}
PROMPT_FIELDS = RFP_FIELDS + list(EXTRA_CONTEXT_FIELDS)

WORK_BREAKDOWN_COLUMNS = {
    "phase": "Phase",
    "task": "Task",
    "description": "Description",
    "activity": "Activity",
    "pd": "PD",
    "rfp_section_reference": "RFP Section Reference",
}
CLARIFICATION_CATEGORIES = [
    "Commercial", "Current State", "Differentiators", "Evaluation", "Next Steps", "Non-Functional",
    "Scope & Outcomes", "Target State", "Team & Governance", "Timeline", "Volumetrics",
]
CLARIFICATION_PRIORITIES = ["High", "Medium", "Low"]
CLARIFICATION_COLUMNS = {
    "number": "#",
    "category": "Category",
    "question": "Question",
    "why_asking": "Why We're Asking",
    "source_context": "Source / Context from Discovery",
    "priority": "Priority",
}
ARCHITECTURE_MAPPING_COLUMNS = {"current_state": "Current State", "target_state": "Target State", "remark": "Remark"}
ROLES_COLUMNS = {"role": "Role", "experience": "Exp", "skills": "Skills", "description": "Description"}

TABLE_COLUMNS = {
    "clarification_questions": CLARIFICATION_COLUMNS,
    "architecture_mapping": ARCHITECTURE_MAPPING_COLUMNS,
    "roles": ROLES_COLUMNS,
    "work_breakdown": WORK_BREAKDOWN_COLUMNS,
}
TABLE_SHEETS = {
    "clarification_questions": "ClarificationQuestions",
    "architecture_mapping": "ArchitectureMapping",
    "roles": "Roles",
    "work_breakdown": "WorkBreakdown",
}

COMPLEXITY_KEYS = ("xs", "s", "m", "l", "xl")
DEFAULT_COMPLEXITY_DISTRIBUTION = {"xs": 0.30, "s": 0.30, "m": 0.30, "l": 0.05, "xl": 0.05}
COMPLEXITY_LABELS = {
    "xs": "Very Low Complex (XS)",
    "s": "Low Complex (S)",
    "m": "Medium Complex (M)",
    "l": "High Complex (L)",
    "xl": "Complex Epic (XL)",
}
DEFAULT_EFFORT_MATRIX_COLUMN_HELP = {
    "T Shirt Size": "Data Engg/BI sizing bucket for a deliverable unit (pipeline, mapping set, model table, API, dashboard, DQ rule, etc.).",
    "Module / Epic Complexity": "Complexity label used when classifying inventory items for BI/analytics delivery.",
    "Discovery & Design": "Data Engg/BI: source profiling, KPI/metric definition, data contracts, STM design, semantic model design, and dashboard wireframes.",
    "Develop": "Data Engg/BI: build ETL/ELT pipelines, transformations, dimensional/fact models, semantic layers, APIs, and Tableau/Power BI visuals.",
    "Integration / Testing": "Data Engg/BI: end-to-end data validation, reconciliation, SIT for pipelines/APIs, dashboard data accuracy checks, and regression of KPI logic.",
    "Deployment + Documentation": "Data Engg/BI: promote jobs/models/dashboards across environments, configure schedules/security, and publish runbooks/lineage/support notes.",
    "Contingency %": "Buffer for Data Engg/BI uncertainty (late source changes, KPI churn, data quality surprises, environment delays).",
    "Total PD Effort (Days)": "Total person-days for one inventory unit of this size: (Discovery + Develop + Integration + Deployment) × (1 + Contingency%).",
    "DE/BI Guidance": "Hover or read this guidance for what this size typically means in Data Engineering / BI delivery.",
}
DEFAULT_EFFORT_MATRIX = [
    {"size": "XL", "complexity": "Complex Epic", "discovery": 0.5, "develop": 3.0, "integration": 1.0, "deployment": 0.5, "contingency": 0.0, "total_pd": 5.0,
     "tooltip": "Data Engg/BI XL: multi-source enterprise pipeline or complex domain model (many entities, heavy SCD/CDC, advanced KPI logic) plus rich executive dashboards with cross-domain joins, row-level security, and significant reconciliation effort."},
    {"size": "L", "complexity": "High Complex", "discovery": 0.5, "develop": 2.0, "integration": 1.0, "deployment": 0.5, "contingency": 0.0, "total_pd": 4.0,
     "tooltip": "Data Engg/BI L: substantial pipeline/API with non-trivial transformations, slowly changing dimensions, or multi-fact models; dashboards with parameters, drill paths, and formal data-quality/reconciliation controls."},
    {"size": "M", "complexity": "Medium Complex", "discovery": 0.5, "develop": 1.0, "integration": 1.0, "deployment": 0.5, "contingency": 0.0, "total_pd": 3.0,
     "tooltip": "Data Engg/BI M: standard source-to-target pipeline or subject-area model (moderate transforms, clear grain); typical operational/analytical dashboard with validated KPIs and routine integration testing."},
    {"size": "S", "complexity": "Low Complex", "discovery": 0.5, "develop": 0.75, "integration": 0.5, "deployment": 0.25, "contingency": 0.0, "total_pd": 2.0,
     "tooltip": "Data Engg/BI S: simple ingest/transform for a known source, light mapping changes, or a focused report/view extension on an existing semantic model with limited test scope."},
    {"size": "XS", "complexity": "Very Low Complex", "discovery": 0.25, "develop": 0.5, "integration": 0.5, "deployment": 0.5, "contingency": 0.0, "total_pd": 1.75,
     "tooltip": "Data Engg/BI XS: minor config/mapping tweak, single-field transform, small DQ rule, filter/label change on an existing dashboard, or low-risk redeploy with smoke validation only."},
]
WORKING_DAYS_PER_MONTH = 21

MODEL_OPTIONS = ["stored-outputs (no model)"]
