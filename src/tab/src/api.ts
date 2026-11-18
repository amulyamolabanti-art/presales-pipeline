// Typed client for the FastAPI backend. Same origin in the built tab; proxied by Vite in dev.

export type Meta = {
  user: { user_id: string; display_name: string; email?: string; role?: string; department?: string };
  backend: string;
  models: string[];
  fields: string[];
  labels: Record<string, string>;
  tab_fields: Record<string, string[]>;
  table_columns: Record<string, Record<string, string>>;
  clarification_categories: string[];
  clarification_priorities: string[];
  prompt_fields: string[];
  extra_context_labels: Record<string, string>;
};

export type ProposalRow = {
  proposal_id: string; name: string; client: string; owner_user_id: string; owner_name: string; status: string;
  model: string; seed_key: string; created_at: string; updated_at: string; sections_ready: number; sections_total: number; documents: number;
};

export type Section = { content: string; html: string; status: string; model: string; updated_at: string };
export type Row = Record<string, string>;
export type MatrixRow = {
  size: string; complexity: string; discovery: number; develop: number; integration: number; deployment: number;
  contingency: number; total_pd: number; tooltip: string;
};
export type InventoryRow = { item: string; inventory: number; assumption: string };
export type EffortState = {
  matrix: MatrixRow[]; distribution: Record<string, number>; inventory_rows: InventoryRow[]; matrix_column_help: Record<string, string>;
};
export type EffortPayload = {
  state: EffortState;
  computed_rows: (InventoryRow & Record<string, number | string>)[];
  summary: { total_inventory: number; discovery: number; develop: number; integration: number; deployment: number; total_pd: number; resource_months: number; pd_by_size: Record<string, number> };
  wbs_total: number; effort_total: number; delta: number; matched: boolean;
};
export type GanttTask = {
  seq: number; task: string; phase: string; duration_pd: number; calendar_days: number; activity: string; description: string;
  rfp_section_reference: string; start: string; finish: string; dependencies_text: string; parallel_with_text: string; critical_path_text: string;
};
export type GanttPhase = { seq: number; phase: string; task: string; start: string; finish: string; duration_pd: number; task_count: number };
export type ChatMessage = { role: "user" | "assistant"; content: string; created_at: string };

export type Bundle = {
  proposal: ProposalRow;
  documents: { doc_id: string; file_name: string; chars: number; error?: string }[];
  loaded_files: string[];
  cached_chars: number;
  sections: Record<string, Section>;
  tables: Record<string, Row[]>;
  effort: EffortPayload;
  gantt_settings: { project_start: string; resources: number };
  diagrams: Record<string, string | null>;
  prompts: Record<string, string>;
  chat: ChatMessage[];
};

let identity: { id: string; name: string } | null = null;
export function setIdentity(id: string, name: string) { identity = { id, name }; }
export function getIdentity() { return identity; }

async function call<T>(method: string, path: string, body?: unknown, raw?: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  if (identity?.id) {
    headers["X-User-Id"] = identity.id;
    headers["X-User-Name"] = identity.name;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { method, headers, body: raw ?? (body !== undefined ? JSON.stringify(body) : undefined) });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => call<Meta>("GET", "/api/meta"),
  proposals: () => call<ProposalRow[]>("GET", "/api/proposals"),
  createProposal: (name: string, client: string) => call<ProposalRow>("POST", "/api/proposals", { name, client }),
  deleteProposal: (id: string) => call<{ ok: boolean }>("DELETE", `/api/proposals/${id}`),
  bundle: (id: string) => call<Bundle>("GET", `/api/proposals/${id}`),
  saveSection: (id: string, field: string, content: string) => call<Section>("PUT", `/api/proposals/${id}/sections/${field}`, { content }),
  saveTable: (id: string, field: string, rows: Row[]) => call<{ rows: Row[]; effort?: EffortPayload }>("PUT", `/api/proposals/${id}/tables/${field}`, { rows }),
  computeEffort: (id: string, state: EffortState) => call<EffortPayload>("POST", `/api/proposals/${id}/effort/compute`, { state }),
  saveEffort: (id: string, state: EffortState) => call<EffortPayload>("PUT", `/api/proposals/${id}/effort`, { state }),
  syncEffort: (id: string, direction: "effort_to_wbs" | "wbs_to_effort", state: EffortState) =>
    call<{ effort: EffortPayload; work_breakdown: Row[] }>("POST", `/api/proposals/${id}/effort/sync`, { direction, state }),
  saveGanttSettings: (id: string, project_start: string, resources: number) =>
    call<{ project_start: string; resources: number }>("PUT", `/api/proposals/${id}/gantt-settings`, { project_start, resources }),
  gantt: (id: string, project_start: string, resources: number) =>
    call<{ tasks: GanttTask[]; phases: GanttPhase[] }>("GET", `/api/proposals/${id}/gantt?project_start=${project_start}&resources=${resources}`),
  analyze: (id: string, fields: string[]) => call<Bundle & { analyzed: string[] }>("POST", `/api/proposals/${id}/analyze`, { fields }),
  diagram: (id: string, field: string) => call<{ url: string }>("POST", `/api/proposals/${id}/diagram/${field}`),
  upload: (id: string, files: FileList) => {
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append("files", f));
    return call<{ documents: Bundle["documents"]; loaded_files: string[]; cached_chars: number; errors: string[] }>("POST", `/api/proposals/${id}/documents`, undefined, fd);
  },
  savePrompts: (id: string, prompts: Record<string, string>) => call<Record<string, string>>("PUT", `/api/proposals/${id}/prompts`, { prompts }),
  resetPrompts: (id: string) => call<Record<string, string>>("POST", `/api/proposals/${id}/prompts/reset`),
  setModel: (id: string, model: string) => call<ProposalRow>("PUT", `/api/proposals/${id}/model`, { model }),
  chat: (id: string, question: string, current_tab: string) => call<{ messages: ChatMessage[] }>("POST", `/api/proposals/${id}/chat`, { question, current_tab }),
  clearChat: (id: string) => call<{ messages: ChatMessage[] }>("DELETE", `/api/proposals/${id}/chat`),
};
