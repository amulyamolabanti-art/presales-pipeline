"""Dynamic Azure SQL repository mapped to the user's 8 schema tables:

Opportunity, Document, Requirement, Gap, ActionItem, DraftSection, StageHistory, AuditLog.

With offline Excel fallback.

"""

from __future__ import annotations



import json

import os

import shutil

import threading

import uuid

from datetime import datetime

from pathlib import Path

import sys

from typing import Any, Optional



_HERE = Path(__file__).resolve().parent

if str(_HERE) not in sys.path:

    sys.path.insert(0, str(_HERE))



from openpyxl import Workbook, load_workbook



from schema import (

    COMPLEXITY_KEYS, DEFAULT_COMPLEXITY_DISTRIBUTION, DEFAULT_EFFORT_MATRIX,

    DEFAULT_EFFORT_MATRIX_COLUMN_HELP, PROMPT_FIELDS, TABLE_COLUMNS, TABLE_SHEETS, TEXT_FIELDS,

)

from calc import (

    normalize_clarification_row, normalize_effort_matrix_row, normalize_inventory_rows,

    normalize_simple_row, normalize_work_breakdown_row, normalize_distribution,

)



ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = ROOT / "data"

DB_PATH = DATA_DIR / "apa_db.xlsx"

DOCS_DIR = DATA_DIR / "docs"

DIAGRAMS_DIR = DATA_DIR / "diagrams"

PROMPTS_DIR = ROOT / "prompts"



EXCEL_CELL_LIMIT = 32000



_lock = threading.RLock()





def now_iso() -> str:

    return datetime.now().replace(microsecond=0).isoformat()





def new_id(prefix: str = "") -> str:

    return f"{prefix}{uuid.uuid4().hex[:10]}"





def format_display_name(user_id: str, raw_name: str = "") -> str:

    name = (raw_name or "").strip()

    if name and "@" not in name and name.lower() != user_id.lower():

        return name

    base = (name.split("@", 1)[0] if "@" in name else user_id).strip()

    parts = [p for p in base.replace("_", ".").replace("-", ".").split(".") if p]

    return " ".join(p.upper() if len(p) == 1 else p.capitalize() for p in parts) or user_id







def ensure_opportunity_in_sql(cursor, opp_id: str, title: str = "", client: str = "", owner_email: str = ""):

    """Ensure parent Opportunity record exists in SQL before inserting child rows."""

    try:

        cursor.execute("SELECT COUNT(*) FROM [Opportunity] WHERE opportunityId = ?", (opp_id,))

        if cursor.fetchone()[0] == 0:

            cursor.execute(

                "INSERT INTO [Opportunity] (opportunityId, clientName, bidTitle, circle, currentStage, status, bidOwnerEmail, dueDate, createdAt) "

                "VALUES (?, ?, ?, 'Enterprise', 'In analysis', 'Active', ?, DATEADD(day, 30, GETUTCDATE()), GETUTCDATE())",

                (opp_id, client or "Enterprise Client", title or f"Proposal {opp_id}", owner_email or "likhitha.yada@ascendion.com")

            )

    except Exception as e:

        print(f"[Azure SQL] ensure_opportunity_in_sql notice: {e}", flush=True)



def parse_opp_id(val: Any) -> Optional[str]:

    """Parse OpportunityId string or int (supports 'p_1', 'p_OPP-2026-001', '1', 'OPP-2026-001')."""

    if val is None:

        return None

    s = str(val).strip()

    if s.lower().startswith("p_"):

        s = s[2:]

    return s if s else None





def get_sql_connection():

    """Retrieve SQL connection using external environment variables (zero hardcoding)."""

    conn_str = os.environ.get("AZURE_SQL_CONNECTIONSTRING")

    if not conn_str:

        server = (

            os.environ.get("SQL_SERVER_FQDN")

            or os.environ.get("DB_SERVER")

            or os.environ.get("SQL_SERVER")

        )

        database = (

            os.environ.get("SQL_DATABASE_NAME")

            or os.environ.get("DB_NAME")

            or os.environ.get("SQL_DATABASE")

            or ""

        )

        user = os.environ.get("SQL_USER") or os.environ.get("DB_USER") or ""

        password = os.environ.get("SQL_PASSWORD") or os.environ.get("DB_PASSWORD") or ""

        if server and database:

            try:

                import pyodbc

                drivers = pyodbc.drivers()

                driver = next(

                    (d for d in drivers if "ODBC Driver" in d and "SQL Server" in d),

                    "ODBC Driver 18 for SQL Server",

                )

            except Exception:

                driver = "ODBC Driver 18 for SQL Server"

            conn_str = (

                f"Driver={{{driver}}};"

                f"Server=tcp:{server},1433;"

                f"Database={database};"

                f"Uid={user};"

                f"Pwd={password};"

                f"Encrypt=yes;"

                f"TrustServerCertificate=yes;"

                f"Connection Timeout=30;"

            )

    if not conn_str:

        return None

    if "TrustServerCertificate=no" in conn_str:

        conn_str = conn_str.replace("TrustServerCertificate=no", "TrustServerCertificate=yes")

    try:

        import pyodbc

        return pyodbc.connect(conn_str, timeout=30)

    except Exception as exc:

        print(f"[Azure SQL] Connection notice: {exc}. Using fallback.", flush=True)

        return None





def get_db_columns(cursor, table_name: str) -> list[str]:

    """Dynamically discover column names from INFORMATION_SCHEMA.COLUMNS."""

    try:

        cursor.execute(

            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?",

            (table_name,)

        )

        return [row[0] for row in cursor.fetchall()]

    except Exception:

        return []





def _auto_seed_sql_if_empty(cursor, conn):

    """Seed initial opportunities into Azure SQL if table is empty."""

    try:

        cursor.execute("SELECT COUNT(*) FROM [Opportunity]")

        cnt = cursor.fetchone()[0]

        if cnt == 0:

            cursor.execute("""

                INSERT INTO [Opportunity] (opportunityId, clientName, bidTitle, circle, currentStage, status, bidOwnerEmail, dueDate, createdAt)

                VALUES 

                ('OPP-2026-001', 'Contoso Healthcare', 'Cloud Modernization RFP', 'Healthcare', 'In analysis', 'Active', 'likhitha.yada@ascendion.com', '2026-12-15 17:00:00', GETUTCDATE()),

                ('OPP-2026-002', 'Fabrikam Financial', 'Generative AI Analytics Platform', 'Enterprise', 'Drafting', 'Active', 'charishma.m@ascendion.com', '2026-12-20 17:00:00', GETUTCDATE())

            """)

            try:

                cursor.execute("""

                    INSERT INTO [StageHistory] (opportunityId, stage, status, updatedBy, notes, timestamp)

                    VALUES 

                    ('OPP-2026-001', 'In analysis', 'Started', 'charishma.m@ascendion.com', 'Intake agent parsing started', GETUTCDATE()),

                    ('OPP-2026-002', 'Drafting', 'Started', 'charishma.m@ascendion.com', 'Straw-man drafting in progress', GETUTCDATE())

                """)

            except Exception:

                pass

            try:

                cursor.execute("""

                    INSERT INTO [DraftSection] (sectionId, opportunityId, sectionName, content, citations, version, needsSmeReview, updatedAt)

                    VALUES

                    ('SEC-001', 'OPP-2026-002', 'summary', 'Ascendion proposes an enterprise AI analytics platform built on Azure OpenAI and Databricks.', '["Fabrikam-2025"]', 1, 0, GETUTCDATE())

                """)

            except Exception:

                pass

            conn.commit()

            print("[Azure SQL] Auto-seeded 2 initial opportunities into Opportunity table.", flush=True)

    except Exception as exc:

        print(f"[Azure SQL] Auto-seed notice: {exc}", flush=True)





class Db:

    """Dynamic SQL repository mapped to Opportunity, DraftSection, Document, AuditLog, etc."""



    def __init__(self):

        self.tables: dict[str, list[dict]] = {

            "Users": [], "Proposals": [], "ProposalAccess": [], "Documents": [],

            "Sections": [], "ClarificationQuestions": [], "ArchitectureMapping": [],

            "Roles": [], "WorkBreakdown": [], "EffortMatrix": [], "EffortDistribution": [],

            "EffortInventory": [], "EffortColumnHelp": [], "GanttSettings": [],

            "Prompts": [], "ChatMessages": [], "AuditLog": []

        }

        self._load()



    def _load(self) -> None:

        conn = get_sql_connection()

        if conn:

            try:

                cursor = conn.cursor()

                # Check and seed if empty

                _auto_seed_sql_if_empty(cursor, conn)



                # 1. Dynamically read Opportunities -> Proposals

                cursor.execute("SELECT * FROM [Opportunity]")

                cols = [c[0].lower() for c in cursor.description]

                proposals = []

                for row in cursor.fetchall():

                    r = dict(zip(cols, row))

                    opp_id = r.get("opportunityid")

                    title = r.get("bidtitle") or r.get("title") or r.get("name") or f"Opportunity {opp_id}"

                    client = r.get("clientname") or r.get("client") or ""

                    circle = r.get("circle") or r.get("industry") or ""

                    status = r.get("currentstage") or r.get("status") or "Draft"

                    owner = r.get("bidowneremail") or r.get("owner") or "admin"

                    created_at = str(r.get("createdat", ""))

                    updated_at = str(r.get("updatedat") or r.get("createdat") or "")

                    proposals.append({

                        "proposal_id": f"p_{opp_id}",

                        "opportunity_id": str(opp_id),

                        "name": title,

                        "client": client,

                        "industry": circle,

                        "status": status,

                        "model": "stored-outputs (no model)",

                        "seed_key": "RFPAuthor",

                        "owner_user_id": owner,

                        "owner_name": owner.split("@")[0] if "@" in owner else owner,

                        "created_at": created_at,

                        "updated_at": updated_at,

                    })

                # Merge existing in-memory proposals so recently created proposals are not wiped

                existing_pids = {p["proposal_id"] for p in proposals}

                for ep in self.tables.get("Proposals", []):

                    if ep.get("proposal_id") not in existing_pids:

                        proposals.append(ep)

                self.tables["Proposals"] = proposals



                # 2. Dynamically read DraftSection -> Sections

                cursor.execute("SELECT * FROM [DraftSection]")

                cols = [c[0].lower() for c in cursor.description]

                sections = []

                for row in cursor.fetchall():

                    r = dict(zip(cols, row))

                    opp_id = r.get("opportunityid")

                    sec_title = r.get("sectionname") or r.get("sectiontitle") or ""

                    content = r.get("content") or ""

                    sections.append({

                        "proposal_id": f"p_{opp_id}",

                        "field": sec_title,

                        "content_md": content,

                        "status": "Analyzed" if content else "Not analyzed yet",

                        "model": "",

                        "updated_at": str(r.get("updatedat", "")),

                    })

                self.tables["Sections"] = sections



                # 3. Dynamically read Document -> Documents

                cursor.execute("SELECT * FROM [Document]")

                cols = [c[0].lower() for c in cursor.description]

                docs = []

                for row in cursor.fetchall():

                    r = dict(zip(cols, row))

                    opp_id = r.get("opportunityid")

                    docs.append({

                        "doc_id": str(r.get("documentid", "")),

                        "proposal_id": f"p_{opp_id}",

                        "file_name": r.get("filename", ""),

                        "chars": 0,

                        "uploaded_at": str(r.get("uploadedat", "")),

                        "text_path": r.get("storageurl") or r.get("bloburl", ""),

                        "error": "",

                    })

                self.tables["Documents"] = docs



                conn.close()

                print(f"[Azure SQL] Loaded {len(proposals)} opportunities dynamically from SQL.", flush=True)

                return

            except Exception as e:

                print(f"[Azure SQL] Dynamic load notice: {e}. Checking local cache.", flush=True)



        # Fallback to local workbook if SQL offline or unconfigured

        if DB_PATH.exists():

            wb = load_workbook(DB_PATH, data_only=True)

            for sheet in list(self.tables.keys()):

                rows = []

                if sheet in wb.sheetnames:

                    ws = wb[sheet]

                    header = [str(c.value or "").strip() for c in next(ws.iter_rows(min_row=1, max_row=1))] if ws.max_row >= 1 else []

                    for values in ws.iter_rows(min_row=2, values_only=True):

                        if values is None or all(v is None or str(v) == "" for v in values):

                            continue

                        row = {col: ("" if v is None else v) for col, v in zip(header, values)}

                        rows.append(row)

                self.tables[sheet] = rows

            wb.close()



    def save(self) -> None:

        """Keep local cache synced."""

        with _lock:

            if DB_PATH.exists() or not get_sql_connection():

                try:

                    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

                    wb = Workbook()

                    wb.remove(wb.active)

                    for sheet, rows in self.tables.items():

                        ws = wb.create_sheet(sheet)

                        if rows:

                            cols = list(rows[0].keys())

                            ws.append(cols)

                            for r in rows:

                                ws.append([str(r.get(c, "")) for c in cols])

                    tmp = DB_PATH.with_suffix(".tmp.xlsx")

                    wb.save(tmp)

                    tmp.replace(DB_PATH)

                except Exception:

                    pass



    # ---- generic helpers

    def rows(self, sheet: str, **where) -> list[dict]:

        out = []

        for row in self.tables.get(sheet, []):

            if all(str(row.get(k, "")) == str(v) for k, v in where.items()):

                out.append(row)

        return out



    def replace(self, sheet: str, new_rows: list[dict], **where) -> None:

        keep = [r for r in self.tables.get(sheet, []) if not all(str(r.get(k, "")) == str(v) for k, v in where.items())]

        self.tables[sheet] = keep + [{**where, **r} for r in new_rows]



    def append(self, sheet: str, row: dict) -> None:

        self.tables.setdefault(sheet, []).append(row)



    def audit(self, user_id: str, proposal_id: str, action: str, detail: str = "") -> None:

        self.append("AuditLog", {"ts": now_iso(), "user_id": user_id, "proposal_id": proposal_id, "action": action, "detail": detail[:500]})

        conn = get_sql_connection()

        if conn:

            try:

                opp_id = parse_opp_id(proposal_id)

                if opp_id:

                    cursor = conn.cursor()

                    ensure_opportunity_in_sql(cursor, opp_id)

                    actor = user_id or "likhitha.yada@ascendion.com"

                    if "@" not in actor:

                        actor = f"{actor}@ascendion.com"

                    cursor.execute(

                        "INSERT INTO [AuditLog] (opportunityId, action, actorEmail, details, timestamp) VALUES (?, ?, ?, ?, GETUTCDATE())",

                        (opp_id, action[:100], actor[:100], detail[:1000])

                    )

                    conn.commit()

                conn.close()

            except Exception as e:

                print(f"[Azure SQL] Audit log write notice: {e}", flush=True)



    # ---- users

    def upsert_user(self, user_id: str, display_name: str, email: str = "", role: str = "user", department: str = "") -> dict:

        inferred_email = email or (display_name if "@" in display_name else "")

        clean_name = format_display_name(user_id, display_name)

        existing = self.rows("Users", user_id=user_id)

        if existing:

            row = existing[0]

            cur_name = str(row.get("display_name", "")).strip()

            if clean_name and (not cur_name or "@" in cur_name or cur_name.lower() == user_id.lower()):

                row["display_name"] = clean_name

            if inferred_email and not row.get("email"):

                row["email"] = inferred_email

            if department or user_id == "unknown":

                row["department"] = department

            return row

        row = {

            "user_id": user_id,

            "display_name": clean_name,

            "email": inferred_email,

            "role": role,

            "department": department or "",

            "created_at": now_iso(),

        }

        self.append("Users", row)

        return row



    def can_access_proposal(self, proposal_id: str, user_id: str) -> bool:

        return True



    def grant_access(self, proposal_id: str, user_id: str, access_role: str = "member") -> None:

        pass



    # ---- proposals / opportunities

    def list_proposals(self, user_id: str | None = None) -> list[dict]:

        self._load()

        out = []

        for p in self.tables["Proposals"]:

            sections = self.rows("Sections", proposal_id=p["proposal_id"])

            ready = sum(1 for s in sections if str(s.get("content_md", "")).strip())

            out.append({

                **p,

                "owner_name": p.get("owner_name", "Admin"),

                "sections_ready": ready,

                "sections_total": 17,

                "documents": len(self.rows("Documents", proposal_id=p["proposal_id"])),

            })

        out.sort(key=lambda p: str(p.get("updated_at", "")), reverse=True)

        return out



    def get_proposal(self, proposal_id: str) -> dict | None:
        self._load()
        target = str(proposal_id or "").strip().lower()
        clean_target = target[2:] if target.startswith("p_") else target
        for p in self.tables.get("Proposals", []):
            pid = str(p.get("proposal_id", "")).strip().lower()
            oid = str(p.get("opportunity_id", "")).strip().lower()
            if target in (pid, oid) or clean_target in (pid, oid):
                return p

        # Check Azure SQL directly if not found in cache
        conn = get_sql_connection()
        if conn and target:
            try:
                opp_id = parse_opp_id(target)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM [Opportunity] WHERE LOWER(opportunityId) = LOWER(?)", (opp_id,))
                row = cursor.fetchone()
                if row:
                    cols = [c[0].lower() for c in cursor.description]
                    r = dict(zip(cols, row))
                    p_row = {
                        "proposal_id": f"p_{r.get('opportunityid')}",
                        "opportunity_id": str(r.get("opportunityid")),
                        "name": r.get("bidtitle") or f"Proposal {r.get('opportunityid')}",
                        "client": r.get("clientname") or "",
                        "owner_user_id": r.get("bidowneremail") or "likhitha.yada@ascendion.com",
                        "owner_name": (r.get("bidowneremail") or "").split("@")[0].replace(".", " ").title(),
                        "status": r.get("status") or "Active",
                        "model": "gpt-4o",
                        "seed_key": "",
                        "created_at": str(r.get("createdat", "")),
                        "updated_at": str(r.get("createdat", "")),
                    }
                    self.tables.setdefault("Proposals", []).append(p_row)
                    conn.close()
                    return p_row
                conn.close()
            except Exception:
                pass

        # If it's a valid ID pattern, create fallback shell
        if target.startswith("opp-") or clean_target.startswith("opp-") or target.isdigit():
            p_row = {
                "proposal_id": f"p_{clean_target.upper()}",
                "opportunity_id": clean_target.upper(),
                "name": f"Proposal {clean_target.upper()}",
                "client": "Client",
                "owner_user_id": "likhitha.yada@ascendion.com",
                "owner_name": "Likhitha Yada",
                "status": "Active",
                "model": "gpt-4o",
                "seed_key": "",
                "created_at": "2026-11-17T10:00:00",
                "updated_at": "2026-11-17T10:00:00",
            }
            self.tables.setdefault("Proposals", []).append(p_row)
            return p_row

        return None



    def create_proposal(self, name: str, client: str, owner_user_id: str, seed_key: str = "", model: str = "") -> dict:

        conn = get_sql_connection()

        opp_id = f"OPP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        now_str = now_iso()

        if conn:

            try:

                cursor = conn.cursor()

                cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Opportunity'")

                avail_cols = [row[0].lower() for row in cursor.fetchall()]

                if "bidtitle" in avail_cols:

                    cursor.execute(

                        "INSERT INTO [Opportunity] (opportunityId, clientName, bidTitle, circle, currentStage, status, bidOwnerEmail, dueDate, createdAt) "

                        "VALUES (?, ?, ?, 'Enterprise', 'Drafting', 'Active', ?, DATEADD(day, 30, GETUTCDATE()), GETUTCDATE())",

                        (opp_id, client.strip() or "Client", name.strip(), owner_user_id or "admin")

                    )

                else:

                    cursor.execute(

                        "INSERT INTO [Opportunity] (Title, ClientName, Status, CreatedAt) "

                        "VALUES (?, ?, 'Draft', GETUTCDATE())",

                        (name.strip(), client.strip() or "Client")

                    )

                try:

                    cursor.execute(

                        "INSERT INTO [StageHistory] (opportunityId, stage, status, updatedBy, notes, timestamp) "

                        "VALUES (?, 'Drafting', 'Started', ?, 'Proposal created from Web UI', GETUTCDATE())",

                        (opp_id, owner_user_id or "admin")

                    )

                except Exception:

                    pass

                conn.commit()

                conn.close()

                print(f"[Azure SQL] Created Opportunity {opp_id}: {name}", flush=True)

            except Exception as e:

                print(f"[Azure SQL] Error creating Opportunity: {e}", flush=True)



        pid = f"p_{opp_id}" if opp_id else new_id("p_")

        row = {

            "proposal_id": pid,

            "opportunity_id": opp_id,

            "name": name.strip(),

            "client": client.strip(),

            "owner_user_id": owner_user_id,

            "status": "Draft",

            "model": model or "stored-outputs (no model)",

            "seed_key": seed_key or "RFPAuthor",

            "created_at": now_str,

            "updated_at": now_str,

        }

        self.append("Proposals", row)

        self.replace("Prompts", [{"field": f, "prompt_text": t, "updated_at": now_str} for f, t in template_prompts().items()], proposal_id=pid)

        self.replace("EffortMatrix", [dict(r) for r in DEFAULT_EFFORT_MATRIX], proposal_id=pid)

        self.replace("EffortDistribution", [dict(DEFAULT_COMPLEXITY_DISTRIBUTION)], proposal_id=pid)

        self.replace("EffortInventory", [{"seq": 1, "item": "", "inventory": 0, "assumption": ""}], proposal_id=pid)

        self.replace("GanttSettings", [{"project_start": datetime.now().date().isoformat(), "resources": 1}], proposal_id=pid)

        self.save()

        return row



    def delete_proposal(self, proposal_id: str) -> None:

        conn = get_sql_connection()

        opp_id = parse_opp_id(proposal_id)

        if conn and opp_id:

            try:

                cursor = conn.cursor()

                # Delete foreign records first

                for child in ["DraftSection", "Document", "Requirement", "Gap", "ActionItem", "StageHistory", "AuditLog"]:

                    cursor.execute(f"DELETE FROM [{child}] WHERE OpportunityId = ?", (opp_id,))

                cursor.execute("DELETE FROM [Opportunity] WHERE OpportunityId = ?", (opp_id,))

                conn.commit()

                conn.close()

            except Exception as e:

                print(f"[Azure SQL] Delete Opportunity error: {e}", flush=True)



        self.tables["Proposals"] = [p for p in self.tables["Proposals"] if str(p.get("proposal_id", "")) != proposal_id and p.get("opportunity_id") != opp_id]

        self.save()



    # ---- sections / DraftSection

    def get_sections(self, proposal_id: str) -> dict[str, dict]:

        out = {f: {"content": "", "status": "Not analyzed yet", "model": "", "updated_at": ""} for f in TEXT_FIELDS}

        conn = get_sql_connection()

        opp_id = parse_opp_id(proposal_id)

        if conn and opp_id:

            try:

                cursor = conn.cursor()

                cursor.execute("SELECT * FROM [DraftSection] WHERE OpportunityId = ?", (opp_id,))

                cols = [c[0].lower() for c in cursor.description]

                for row in cursor.fetchall():

                    r = dict(zip(cols, row))

                    title = r.get("sectionname") or r.get("sectiontitle") or ""

                    content = r.get("content") or ""

                    updated = r.get("updatedat") or ""

                    if title in out:

                        out[title] = {

                            "content": content,

                            "status": "Analyzed" if content else "Not analyzed yet",

                            "model": "",

                            "updated_at": str(updated),

                        }

                conn.close()

                return out

            except Exception as e:

                print(f"[Azure SQL] Get sections notice: {e}", flush=True)



        for r in self.rows("Sections", proposal_id=proposal_id):

            if r.get("field") in out:

                content = str(r.get("content_md", "") or "")

                out[r["field"]] = {

                    "content": content,

                    "status": r.get("status") or ("Analyzed" if content else "Not analyzed yet"),

                    "model": r.get("model") or "",

                    "updated_at": r.get("updated_at") or "",

                }

        return out



    def set_section(self, proposal_id: str, field: str, content: str, model: str = "") -> None:

        now_str = now_iso()

        conn = get_sql_connection()

        opp_id = parse_opp_id(proposal_id)

        if conn and opp_id:

            try:

                cursor = conn.cursor()

                cursor.execute("SELECT SectionId FROM [DraftSection] WHERE OpportunityId = ? AND SectionTitle = ?", (opp_id, field))

                existing = cursor.fetchone()

                if existing:

                    cursor.execute(

                        "UPDATE [DraftSection] SET Content = ?, UpdatedAt = GETUTCDATE() WHERE SectionId = ?",

                        (content, existing[0])

                    )

                else:

                    cursor.execute(

                        "INSERT INTO [DraftSection] (OpportunityId, SectionTitle, Content, Version, UpdatedAt) VALUES (?, ?, ?, 1, GETUTCDATE())",

                        (opp_id, field, content)

                    )

                # Update Opportunity UpdatedAt

                cursor.execute("UPDATE [Opportunity] SET UpdatedAt = GETUTCDATE() WHERE OpportunityId = ?", (opp_id,))

                conn.commit()

                conn.close()

            except Exception as e:

                print(f"[Azure SQL] Set section notice: {e}", flush=True)



        existing = [r for r in self.rows("Sections", proposal_id=proposal_id) if r.get("field") == field]

        if existing:

            existing[0]["content_md"] = content

            existing[0]["status"] = "Analyzed" if content else "Not analyzed yet"

            existing[0]["model"] = model

            existing[0]["updated_at"] = now_str

        else:

            self.append("Sections", {

                "proposal_id": proposal_id, "field": field, "content_md": content,

                "status": "Analyzed" if content else "Not analyzed yet",

                "model": model, "updated_at": now_str,

            })

        self.save()



    # ---- tables / Requirement / ActionItem / Gap

    def get_table(self, proposal_id: str, field: str) -> list[dict]:

        return [dict(r) for r in self.rows(TABLE_SHEETS.get(field, field), proposal_id=proposal_id)]



    def set_table(self, proposal_id: str, field: str, rows: list[dict]) -> list[dict]:

        sheet = TABLE_SHEETS[field]

        cols = TABLE_COLUMNS.get(field, {})

        normalized = [normalize_simple_row(r, cols) if cols else r for r in rows]

        self.replace(sheet, normalized, proposal_id=proposal_id)

        self.save()

        return normalized



    # ---- effort

    def get_effort(self, proposal_id: str) -> dict:

        inv = self.rows("EffortInventory", proposal_id=proposal_id)

        dist = self.rows("EffortDistribution", proposal_id=proposal_id)

        matrix = self.rows("EffortMatrix", proposal_id=proposal_id)

        return {

            "inventory_rows": [dict(r) for r in inv],

            "distribution": dict(dist[0]) if dist else dict(DEFAULT_COMPLEXITY_DISTRIBUTION),

            "matrix": [dict(r) for r in matrix] if matrix else [dict(r) for r in DEFAULT_EFFORT_MATRIX],

            "column_help": {r["column"]: r["help_text"] for r in self.rows("EffortColumnHelp", proposal_id=proposal_id)} or dict(DEFAULT_EFFORT_MATRIX_COLUMN_HELP),

        }



    def set_effort(self, proposal_id: str, state: dict) -> dict:

        if "inventory_rows" in state:

            self.replace("EffortInventory", normalize_inventory_rows(state["inventory_rows"]), proposal_id=proposal_id)

        if "distribution" in state:

            self.replace("EffortDistribution", [normalize_distribution(state["distribution"])], proposal_id=proposal_id)

        if "matrix" in state:

            self.replace("EffortMatrix", [normalize_effort_matrix_row(r) for r in state["matrix"]], proposal_id=proposal_id)

        self.save()

        return self.get_effort(proposal_id)



    # ---- documents / Document table

    def get_documents(self, proposal_id: str) -> list[dict]:

        conn = get_sql_connection()

        opp_id = parse_opp_id(proposal_id)

        if conn and opp_id:

            try:

                cursor = conn.cursor()

                cursor.execute("SELECT documentId, fileName, fileType, storageUrl, uploadedAt FROM [Document] WHERE opportunityId = ?", (opp_id,))

                out = []

                for doc_id, fname, ftype, s_url, uploaded in cursor.fetchall():

                    chars = 0

                    if s_url:

                        fpath = ROOT / s_url

                        if fpath.exists():

                            try:

                                chars = len(fpath.read_text(encoding="utf-8", errors="ignore"))

                            except Exception:

                                pass

                    out.append({

                        "doc_id": str(doc_id),

                        "proposal_id": proposal_id,

                        "file_name": fname or "",

                        "chars": chars,

                        "uploaded_at": str(uploaded or ""),

                        "text_path": s_url or "",

                        "error": "",

                    })

                conn.close()

                if out:

                    return out

            except Exception as e:

                print(f"[Azure SQL] Get documents notice: {e}", flush=True)

        return [dict(r) for r in self.rows("Documents", proposal_id=proposal_id)]



    def add_document(self, proposal_id: str, file_name: str, chars: int, text_path: str, error: str = "") -> dict:

        now_str = now_iso()

        doc_id = new_id("DOC-")

        conn = get_sql_connection()

        opp_id = parse_opp_id(proposal_id)

        if conn and opp_id:

            try:

                cursor = conn.cursor()

                ensure_opportunity_in_sql(cursor, opp_id)

                ftype = file_name.split(".")[-1].upper() if "." in file_name else "TXT"

                cursor.execute(

                    "INSERT INTO [Document] (documentId, opportunityId, fileName, fileType, storageUrl, docType, version, uploadedAt) "

                    "VALUES (?, ?, ?, ?, ?, 'RFP', 1, GETUTCDATE())",

                    (doc_id, opp_id, file_name, ftype, text_path or f"/uploads/{file_name}")

                )

                conn.commit()

                conn.close()

            except Exception as e:

                print(f"[Azure SQL] Add document notice: {e}", flush=True)



        row = {"doc_id": doc_id, "proposal_id": proposal_id, "file_name": file_name, "chars": chars, "uploaded_at": now_str, "text_path": text_path, "error": error}

        self.append("Documents", row)

        self.save()

        return row



    def clear_documents(self, proposal_id: str) -> None:

        conn = get_sql_connection()

        opp_id = parse_opp_id(proposal_id)

        if conn and opp_id:

            try:

                cursor = conn.cursor()

                cursor.execute("DELETE FROM [Document] WHERE opportunityId = ?", (opp_id,))

                conn.commit()

                conn.close()

            except Exception as e:

                print(f"[Azure SQL] Clear documents notice: {e}", flush=True)

        self.tables["Documents"] = [d for d in self.tables.get("Documents", []) if str(d.get("proposal_id", "")) != proposal_id]

        self.save()



    # ---- gantt

    def get_gantt_settings(self, proposal_id: str) -> dict:

        rows = self.rows("GanttSettings", proposal_id=proposal_id)

        if rows:

            return {

                "project_start": rows[0].get("project_start") or datetime.now().date().isoformat(),

                "resources": int(float(rows[0].get("resources") or 1)),

            }

        return {"project_start": datetime.now().date().isoformat(), "resources": 1}



    def set_gantt_settings(self, proposal_id: str, project_start: str, resources: int) -> dict:

        self.replace("GanttSettings", [{"project_start": project_start, "resources": resources}], proposal_id=proposal_id)

        self.save()

        return self.get_gantt_settings(proposal_id)



    # ---- prompts

    def get_prompts(self, proposal_id: str) -> dict[str, str]:

        out = template_prompts()

        for r in self.rows("Prompts", proposal_id=proposal_id):

            if r.get("field") in out and r.get("prompt_text"):

                out[r["field"]] = r["prompt_text"]

        return out



    def set_prompts(self, proposal_id: str, prompts: dict[str, str]) -> dict[str, str]:

        now_str = now_iso()

        rows = [{"field": f, "prompt_text": t, "updated_at": now_str} for f, t in prompts.items() if f in PROMPT_FIELDS]

        self.replace("Prompts", rows, proposal_id=proposal_id)

        self.save()

        return self.get_prompts(proposal_id)



    # ---- chat

    def get_chat(self, proposal_id: str) -> list[dict]:

        return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in self.rows("ChatMessages", proposal_id=proposal_id)]



    def add_chat(self, proposal_id: str, role: str, content: str) -> None:

        self.append("ChatMessages", {"proposal_id": proposal_id, "seq": len(self.get_chat(proposal_id)) + 1, "role": role, "content": content, "created_at": now_iso()})

        self.save()



    def clear_chat(self, proposal_id: str) -> None:

        self.tables["ChatMessages"] = [c for c in self.tables.get("ChatMessages", []) if str(c.get("proposal_id", "")) != proposal_id]

        self.save()





def template_prompts() -> dict[str, str]:

    out: dict[str, str] = {}

    for f in PROMPT_FIELDS:

        p = PROMPTS_DIR / f"{f}.txt"

        out[f] = p.read_text(encoding="utf-8") if p.exists() else ""

    return out





db = Db()

