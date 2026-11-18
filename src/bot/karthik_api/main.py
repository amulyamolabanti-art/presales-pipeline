"""AI Proposal Assistant prototype API. Serves the built React tab (app/dist) and /api/* routes.
Run from the Karthik folder:  python -m uvicorn main:app --app-dir api --port 8080
"""
from __future__ import annotations

import io
import os
import sys
from datetime import date
from pathlib import Path

from fastapi import APIRouter, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backends import BACKEND  # noqa: E402
from calc import (  # noqa: E402
    build_gantt_rows, build_phase_gantt_rows, calculate_effort_inventory_rows, effort_phase_summary,
    reconcile_effort_to_wbs_total, reconcile_wbs_to_effort_total, section_content_html,
    sum_effort_estimate_pd, sum_work_breakdown_pd,
)
from repo import DIAGRAMS_DIR, DOCS_DIR, ROOT, Db, template_prompts  # noqa: E402
from schema import (  # noqa: E402
    CLARIFICATION_CATEGORIES, CLARIFICATION_PRIORITIES, DIAGRAM_FIELDS, FORMATTED_DISPLAY_FIELDS,
    MODEL_OPTIONS, PROMPT_FIELDS, RFP_FIELDS, SECTION_LABELS, TAB_FIELDS, TABLE_COLUMNS, TABLE_FIELDS,
    TEXT_FIELDS, EXTRA_CONTEXT_FIELDS,
)

app = FastAPI(title="AI Proposal Assistant (prototype)")
api_router = APIRouter()
DIST = ROOT / "src" / "tab" / "dist"


# ----------------------------------------------------------------- helpers

def current_user(db: Db, x_user_id: str | None = None, x_user_name: str | None = None) -> dict:
    raw_uid = (x_user_id or "").strip().lower()

    # When user details cannot be obtained (e.g. accessed outside Teams without auth headers),
    # return an anonymous / Unknown user instead of defaulting to a specific developer name.
    if not raw_uid:
        return db.upsert_user(
            "unknown",
            display_name="Unknown",
            email="",
            role="guest",
            department="",
        )

    uid = raw_uid

    raw_name = (x_user_name or "").strip()
    if raw_uid == "karthik.valluri" and uid != "karthik.valluri":
        raw_name = ""

    matched_dept = ""
    matched_name = ""
    matched_email = ""
    try:
        from auth.directory_service import load_sharepoint_directories, resolve_directory_user
        from config import Config
        dirs = load_sharepoint_directories(Config())
        matched = resolve_directory_user(uid, dirs)
        if matched:
            matched_name = matched.get("userName") or ""
            matched_email = matched.get("userEmail") or ""
            matched_dept = matched.get("circleName") or ""
    except Exception:
        pass

    if not raw_name and uid == "karthik.valluri":
        raw_name = "Karthik Valluri"

    display_name = raw_name or matched_name or uid
    return db.upsert_user(
        uid,
        display_name=display_name,
        email=matched_email,
        department=matched_dept,
    )


def must_get(db: Db, proposal_id: str, user: dict | None = None) -> dict:
    p = db.get_proposal(proposal_id)
    if not p:
        raise HTTPException(404, "Proposal not found")
    if user and not db.can_access_proposal(proposal_id, user["user_id"]):
        raise HTTPException(403, "You do not have access to this proposal.")
    return p


def diagram_url(proposal_id: str, field: str) -> str | None:
    path = DIAGRAMS_DIR / proposal_id / f"{DIAGRAM_FIELDS[field]}.jpg"
    if not path.exists():
        return None
    return f"/api/proposals/{proposal_id}/diagrams/{field}?v={int(path.stat().st_mtime)}"


def sections_payload(db: Db, proposal_id: str) -> dict:
    out = {}
    for field, sec in db.get_sections(proposal_id).items():
        out[field] = {**sec, "html": section_content_html(sec["content"]) if field in FORMATTED_DISPLAY_FIELDS else ""}
    return out


def effort_payload(state: dict, wbs_rows: list[dict]) -> dict:
    rows = calculate_effort_inventory_rows(state["inventory_rows"], state["distribution"], state["matrix"])
    wbs_total = sum_work_breakdown_pd(wbs_rows)
    effort_total = sum_effort_estimate_pd(state)
    return {
        "state": state,
        "computed_rows": rows,
        "summary": effort_phase_summary(state),
        "wbs_total": wbs_total,
        "effort_total": effort_total,
        "delta": round(effort_total - wbs_total, 2),
        "matched": abs(wbs_total - effort_total) < 0.05,
    }


def bundle(db: Db, proposal_id: str) -> dict:
    p = must_get(db, proposal_id)
    tables = {f: db.get_table(proposal_id, f) for f in TABLE_FIELDS}
    effort = db.get_effort(proposal_id)
    docs = db.get_documents(proposal_id)
    return {
        "proposal": p,
        "documents": docs,
        "loaded_files": [d["file_name"] for d in docs],
        "cached_chars": sum(int(float(d.get("chars") or 0)) for d in docs),
        "sections": sections_payload(db, proposal_id),
        "tables": tables,
        "effort": effort_payload(effort, tables["work_breakdown"]),
        "gantt_settings": db.get_gantt_settings(proposal_id),
        "diagrams": {f: diagram_url(proposal_id, f) for f in DIAGRAM_FIELDS},
        "prompts": db.get_prompts(proposal_id),
        "chat": db.get_chat(proposal_id),
    }


# ----------------------------------------------------------------- meta

@api_router.get("/api/meta")
def meta(x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    db.save()
    return {
        "user": user,
        "backend": BACKEND.name,
        "models": MODEL_OPTIONS,
        "fields": RFP_FIELDS,
        "labels": SECTION_LABELS,
        "tab_fields": TAB_FIELDS,
        "table_columns": TABLE_COLUMNS,
        "clarification_categories": CLARIFICATION_CATEGORIES,
        "clarification_priorities": CLARIFICATION_PRIORITIES,
        "prompt_fields": PROMPT_FIELDS,
        "extra_context_labels": EXTRA_CONTEXT_FIELDS,
    }


# ----------------------------------------------------------------- proposals

class ProposalIn(BaseModel):
    name: str
    client: str = ""


@api_router.get("/api/proposals")
def list_proposals(x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    db.save()
    return db.list_proposals(user_id=user["user_id"])


@api_router.post("/api/proposals")
def create_proposal(body: ProposalIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    if not body.name.strip():
        raise HTTPException(400, "Proposal name is empty.")
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    if any(p["name"].strip().lower() == body.name.strip().lower() for p in db.tables["Proposals"]):
        raise HTTPException(409, "A proposal with this name already exists.")
    p = db.create_proposal(body.name, body.client, user["user_id"], seed_key="RFPAuthor", model=MODEL_OPTIONS[0])
    db.audit(user["user_id"], p["proposal_id"], "create_proposal", body.name)
    db.save()
    return p


@api_router.get("/api/proposals/{proposal_id}")
def get_proposal(proposal_id: str, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id, user)
    return bundle(db, proposal_id)


@api_router.delete("/api/proposals/{proposal_id}")
def delete_proposal(proposal_id: str, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id, user)
    db.delete_proposal(proposal_id)
    db.audit(user["user_id"], proposal_id, "delete_proposal")
    db.save()
    return {"ok": True}


# ----------------------------------------------------------------- sections & tables

class SectionIn(BaseModel):
    content: str


@api_router.put("/api/proposals/{proposal_id}/sections/{field}")
def put_section(proposal_id: str, field: str, body: SectionIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    if field not in TEXT_FIELDS:
        raise HTTPException(400, f"Unknown text field {field}")
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    db.set_section(proposal_id, field, body.content)
    db.audit(user["user_id"], proposal_id, "save_section", field)
    db.save()
    return sections_payload(db, proposal_id)[field]


class RowsIn(BaseModel):
    rows: list[dict]


@api_router.put("/api/proposals/{proposal_id}/tables/{field}")
def put_table(proposal_id: str, field: str, body: RowsIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    if field not in TABLE_FIELDS:
        raise HTTPException(400, f"Unknown table {field}")
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    rows = db.set_table(proposal_id, field, body.rows)
    db.audit(user["user_id"], proposal_id, "save_table", f"{field} ({len(rows)} rows)")
    db.save()
    out = {"rows": rows}
    if field == "work_breakdown":
        out["effort"] = effort_payload(db.get_effort(proposal_id), rows)
    return out


# ----------------------------------------------------------------- effort estimate

class EffortIn(BaseModel):
    state: dict


@api_router.post("/api/proposals/{proposal_id}/effort/compute")
def compute_effort(proposal_id: str, body: EffortIn):
    """Recalculate formula columns for an unsaved state (no write)."""
    db = Db()
    must_get(db, proposal_id)
    from calc import normalize_effort_matrix_row, normalize_distribution, normalize_inventory_rows
    state = {
        "matrix": [normalize_effort_matrix_row(r) for r in body.state.get("matrix") or []],
        "distribution": normalize_distribution(body.state.get("distribution") or {}),
        "inventory_rows": normalize_inventory_rows(body.state.get("inventory_rows") or []),
        "matrix_column_help": body.state.get("matrix_column_help") or {},
    }
    return effort_payload(state, db.get_table(proposal_id, "work_breakdown"))


@api_router.put("/api/proposals/{proposal_id}/effort")
def put_effort(proposal_id: str, body: EffortIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    wbs_rows = db.get_table(proposal_id, "work_breakdown")
    state = body.state
    # Final reconcile on save when the WBS has PD (same rule as his Save button).
    wbs_total = sum_work_breakdown_pd(wbs_rows)
    if wbs_total > 0 and abs(sum_effort_estimate_pd(db.set_effort(proposal_id, state)) - wbs_total) >= 0.05:
        state = reconcile_effort_to_wbs_total(db.get_effort(proposal_id), wbs_total)
    saved = db.set_effort(proposal_id, state)
    db.audit(user["user_id"], proposal_id, "save_effort")
    db.save()
    return effort_payload(saved, wbs_rows)


class SyncIn(BaseModel):
    direction: str  # "effort_to_wbs" (scale inventory to WBS total) | "wbs_to_effort" (scale WBS PD to effort total)
    state: dict | None = None


@api_router.post("/api/proposals/{proposal_id}/effort/sync")
def sync_effort(proposal_id: str, body: SyncIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    if body.state:
        db.set_effort(proposal_id, body.state)
    state = db.get_effort(proposal_id)
    wbs_rows = db.get_table(proposal_id, "work_breakdown")
    wbs_total = sum_work_breakdown_pd(wbs_rows)
    effort_total = sum_effort_estimate_pd(state)
    if body.direction == "effort_to_wbs":
        if wbs_total <= 0:
            raise HTTPException(400, "Work Breakdown has no PD total to sync against. Analyze Work Breakdown first.")
        state = db.set_effort(proposal_id, reconcile_effort_to_wbs_total(state, wbs_total))
    elif body.direction == "wbs_to_effort":
        if effort_total <= 0:
            raise HTTPException(400, "Effort Estimate has no PD total. Analyze Effort Estimate first.")
        wbs_rows = db.set_table(proposal_id, "work_breakdown", reconcile_wbs_to_effort_total(wbs_rows, effort_total))
    else:
        raise HTTPException(400, "direction must be effort_to_wbs or wbs_to_effort")
    db.audit(user["user_id"], proposal_id, "sync_effort", body.direction)
    db.save()
    return {"effort": effort_payload(state, wbs_rows), "work_breakdown": wbs_rows}


# ----------------------------------------------------------------- gantt

class GanttSettingsIn(BaseModel):
    project_start: str
    resources: int


@api_router.put("/api/proposals/{proposal_id}/gantt-settings")
def put_gantt_settings(proposal_id: str, body: GanttSettingsIn):
    db = Db()
    must_get(db, proposal_id)
    out = db.set_gantt_settings(proposal_id, body.project_start, body.resources)
    db.save()
    return out


@api_router.get("/api/proposals/{proposal_id}/gantt")
def get_gantt(proposal_id: str, project_start: str | None = None, resources: int | None = None):
    db = Db()
    must_get(db, proposal_id)
    settings = db.get_gantt_settings(proposal_id)
    start = date.fromisoformat((project_start or settings["project_start"])[:10])
    res = int(resources or settings["resources"])
    tasks = build_gantt_rows(db.get_table(proposal_id, "work_breakdown"), start, res)
    return {"tasks": tasks, "phases": build_phase_gantt_rows(tasks), "project_start": start.isoformat(), "resources": res}


# ----------------------------------------------------------------- analyze & diagrams

class AnalyzeIn(BaseModel):
    fields: list[str]


@api_router.post("/api/proposals/{proposal_id}/analyze")
def analyze(proposal_id: str, body: AnalyzeIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    p = must_get(db, proposal_id)
    done = []
    for field in body.fields:
        if field not in RFP_FIELDS:
            continue
        content = BACKEND.analyze(field, str(p.get("seed_key") or ""))
        if field in TABLE_FIELDS:
            db.set_table(proposal_id, field, content if isinstance(content, list) else [])
        elif field == "effort_estimate":
            if isinstance(content, dict) and content:
                db.set_effort(proposal_id, content)
        else:
            db.set_section(proposal_id, field, str(content or ""), model=BACKEND.name)
        done.append(field)
    p["status"] = "Analyzed"
    db.audit(user["user_id"], proposal_id, "analyze", ", ".join(done))
    db.save()
    return {"analyzed": done, **bundle(db, proposal_id)}


@api_router.post("/api/proposals/{proposal_id}/diagram/{field}")
def make_diagram(proposal_id: str, field: str, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    if field not in DIAGRAM_FIELDS:
        raise HTTPException(400, "Diagram is only available for the two architecture sections.")
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    p = must_get(db, proposal_id)
    path = BACKEND.diagram(field, str(p.get("seed_key") or ""), proposal_id)
    db.audit(user["user_id"], proposal_id, "diagram", field)
    db.save()
    if not path:
        raise HTTPException(404, "No stored diagram for this section in stored-outputs mode.")
    return {"url": diagram_url(proposal_id, field)}


@api_router.get("/api/proposals/{proposal_id}/diagrams/{field}")
def get_diagram(proposal_id: str, field: str):
    if field not in DIAGRAM_FIELDS:
        raise HTTPException(404)
    path = DIAGRAMS_DIR / proposal_id / f"{DIAGRAM_FIELDS[field]}.jpg"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")


# ----------------------------------------------------------------- documents

def extract_text(name: str, data: bytes) -> str:
    lower = name.lower()
    if lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text
        except Exception:
            pass
        try:
            import pypdf2
            reader = pypdf2.PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text
        except Exception:
            pass
        try:
            import re
            matches = re.findall(rb"\((.*?)\)[\r\n\s]*Tj", data)
            if matches:
                return "\n".join(m.decode("utf-8", errors="ignore") for m in matches)
        except Exception:
            pass
        return data.decode("utf-8", errors="ignore")

    if lower.endswith(".docx") or lower.endswith(".doc"):
        try:
            import docx
            d = docx.Document(io.BytesIO(data))
            text = "\n".join(par.text for par in d.paragraphs if par.text)
            if text.strip():
                return text
        except Exception:
            pass
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                xml_content = zf.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = []
                for p in tree.iterfind(".//w:p", namespaces):
                    texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                    if texts:
                        paragraphs.append("".join(texts))
                if paragraphs:
                    return "\n".join(paragraphs)
        except Exception:
            pass
        return data.decode("utf-8", errors="ignore")

    return data.decode("utf-8", errors="ignore")


@api_router.post("/api/proposals/{proposal_id}/documents")
async def upload_documents(proposal_id: str, files: list[UploadFile] = File(...), x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    folder = DOCS_DIR / proposal_id
    folder.mkdir(parents=True, exist_ok=True)
    db.clear_documents(proposal_id)  # a new upload replaces the set, like his uploader
    errors = []
    for f in files:
        data = await f.read()
        try:
            text = extract_text(f.filename or "file", data)
            out = folder / ((f.filename or "file") + ".txt")
            out.write_text(text, encoding="utf-8")
            db.add_document(proposal_id, f.filename or "file", len(text), str(out.relative_to(ROOT)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{f.filename}: {exc}")
            db.add_document(proposal_id, f.filename or "file", 0, "", error=str(exc))
    db.audit(user["user_id"], proposal_id, "upload", ", ".join(f.filename or "" for f in files))
    db.save()
    docs = db.get_documents(proposal_id)
    return {"documents": docs, "loaded_files": [d["file_name"] for d in docs],
            "cached_chars": sum(int(float(d.get("chars") or 0)) for d in docs), "errors": errors}


# ----------------------------------------------------------------- prompts (Settings)

class PromptsIn(BaseModel):
    prompts: dict[str, str]


@api_router.put("/api/proposals/{proposal_id}/prompts")
def put_prompts(proposal_id: str, body: PromptsIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    out = db.set_prompts(proposal_id, body.prompts)
    db.audit(user["user_id"], proposal_id, "save_prompts")
    db.save()
    return out


@api_router.post("/api/proposals/{proposal_id}/prompts/reset")
def reset_prompts(proposal_id: str, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    out = db.set_prompts(proposal_id, template_prompts())
    db.audit(user["user_id"], proposal_id, "reset_prompts")
    db.save()
    return out


class ModelIn(BaseModel):
    model: str


@api_router.put("/api/proposals/{proposal_id}/model")
def put_model(proposal_id: str, body: ModelIn):
    db = Db()
    p = must_get(db, proposal_id)
    p["model"] = body.model
    db.save()
    return p


# ----------------------------------------------------------------- chat

class ChatIn(BaseModel):
    question: str
    current_tab: str = ""


@api_router.post("/api/proposals/{proposal_id}/chat")
def chat(proposal_id: str, body: ChatIn, x_user_id: str | None = Header(None), x_user_name: str | None = Header(None)):
    db = Db()
    user = current_user(db, x_user_id, x_user_name)
    must_get(db, proposal_id)
    q = body.question.strip()
    if not q:
        raise HTTPException(400, "Empty question")
    db.add_chat(proposal_id, "user", q)
    reply = BACKEND.chat(q, db.get_sections(proposal_id), {f: db.get_table(proposal_id, f) for f in TABLE_FIELDS})
    db.add_chat(proposal_id, "assistant", reply)
    db.audit(user["user_id"], proposal_id, "chat", q[:120])
    db.save()
    return {"messages": db.get_chat(proposal_id)}


@api_router.delete("/api/proposals/{proposal_id}/chat")
def clear_chat(proposal_id: str):
    db = Db()
    must_get(db, proposal_id)
    db.clear_chat(proposal_id)
    db.save()
    return {"messages": []}


# ----------------------------------------------------------------- static tab

@api_router.get("/healthz")
def healthz():
    return {"ok": True, "dist": DIST.exists()}


app.include_router(api_router)

if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="static")
else:
    @app.get("/")
    def no_build():
        return JSONResponse({"message": "React app not built yet. Run `npm run build` in Karthik/app."})
