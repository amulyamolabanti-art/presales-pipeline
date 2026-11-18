"""Build data/apa_db.xlsx from Srigopal's sample proposals (read-only reference under Karthik/_ref_srigopal).
Copies each proposal's output files to data/seed/<key>/ (the stored-outputs backend reads those) and
diagrams to data/diagrams/<proposal_id>/. Re-runnable: it recreates the workbook from scratch.

    python seed.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repo  # noqa: E402
from repo import DATA_DIR, DB_PATH, DIAGRAMS_DIR, Db, create_empty_workbook  # noqa: E402
from schema import DIAGRAM_FIELDS, PROMPT_FIELDS, TABLE_FIELDS, TEXT_FIELDS  # noqa: E402

REF = repo.ROOT / "_ref_srigopal" / "Ollama Code" / "ollama" / "ollama"
USERS = REF / "Users"
SEED_DIR = DATA_DIR / "seed"

# (seed_key, display name, client, owner user id, owner display name, source folder)
SAMPLES = [
    ("ARMS", "ARMS", "St. Luke's Medical Center", "srigopal.mohanty", "Srigopal Mohanty", USERS / "srigopal.mohanty@ascendion.com" / "Proposals" / "ARMS"),
    ("Cirrium", "Cirrium", "", "srigopal.mohanty", "Srigopal Mohanty", USERS / "srigopal.mohanty@ascendion.com" / "Proposals" / "Cirrium"),
    ("IDB", "IDB", "", "srigopal.mohanty", "Srigopal Mohanty", USERS / "srigopal.mohanty@ascendion.com" / "Proposals" / "IDB"),
    ("Windstar", "Windstar", "Windstar Cruises", "srigopal.mohanty", "Srigopal Mohanty", USERS / "srigopal.mohanty@ascendion.com" / "Proposals" / "Windstar"),
    ("WindstarCrew", "Windstar Cruises Crew Scheduling", "Windstar Cruises", "rishi.saran", "Rishi Saran", USERS / "rishi.saran@ascendion.com" / "Proposals" / "Windstar Cruises Crew Scheduing"),
    ("RFPAuthor", "Sample proposal (template outputs)", "", "karthik.valluri", "Karthik Valluri", USERS / "RFPAuthor"),
]


def copy_seed_files(src: Path, key: str) -> None:
    dest = SEED_DIR / key
    dest.mkdir(parents=True, exist_ok=True)
    for f in TEXT_FIELDS:
        p = src / f"{f}.txt"
        if p.exists():
            shutil.copy2(p, dest / p.name)
    for f in list(TABLE_FIELDS) + ["effort_estimate"]:
        p = src / f"{f}.json"
        if p.exists():
            shutil.copy2(p, dest / p.name)
    for diag in DIAGRAM_FIELDS.values():
        p = src / f"{diag}.jpg"
        if p.exists():
            shutil.copy2(p, dest / p.name)


def main() -> None:
    if not REF.exists():
        sys.exit(f"Reference folder not found: {REF}")
    if DB_PATH.exists():
        DB_PATH.unlink()
    create_empty_workbook()
    db = Db()
    db.upsert_user("karthik.valluri", "Karthik Valluri", "", "admin", department="Data & Insights")

    for key, name, client, owner_id, owner_name, src in SAMPLES:
        if not src.exists():
            print(f"skip {key}: {src} missing")
            continue
        db.upsert_user(owner_id, owner_name, department="Data & Insights")
        copy_seed_files(src, key)
        p = db.create_proposal(name, client, owner_id, seed_key=key, model="stored-outputs (no model)")
        pid = p["proposal_id"]
        p["status"] = "Analyzed"

        for f in TEXT_FIELDS:
            path = src / f"{f}.txt"
            if path.exists():
                db.set_section(pid, f, path.read_text(encoding="utf-8"), model="gemini-2.5-pro (stored)")
        for f in TABLE_FIELDS:
            path = src / f"{f}.json"
            if path.exists():
                db.set_table(pid, f, json.loads(path.read_text(encoding="utf-8")))
        eff = src / "effort_estimate.json"
        if eff.exists():
            db.set_effort(pid, json.loads(eff.read_text(encoding="utf-8")))
        prompts = {}
        for f in PROMPT_FIELDS:
            path = src / f"context_{f}.txt"
            if path.exists():
                prompts[f] = path.read_text(encoding="utf-8")
        if prompts:
            db.set_prompts(pid, prompts)
        for field, diag in DIAGRAM_FIELDS.items():
            img = src / f"{diag}.jpg"
            if img.exists():
                d = DIAGRAMS_DIR / pid
                d.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img, d / f"{diag}.jpg")
        db.audit("seed", pid, "seed", f"seeded from {src.name}")
        print(f"seeded {name} -> {pid}")

    db.save()
    print(f"workbook written: {DB_PATH}")


if __name__ == "__main__":
    main()
