"""Analysis backends. Only `stored` exists today: Analyze returns the outputs Srigopal's app produced
for the sample proposals (copied to data/seed/<seed_key>/). The interface is what a real model backend
(Azure OpenAI once IT #19 exists) will implement later: analyze(field, context) -> content."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from repo import DATA_DIR, DIAGRAMS_DIR
from schema import DIAGRAM_FIELDS, SECTION_LABELS, TABLE_FIELDS, TEXT_FIELDS

SEED_DIR = DATA_DIR / "seed"
SAMPLE_SEED_KEY = "RFPAuthor"  # generic sample used for proposals that have no stored outputs of their own
ANALYZE_DELAY_SECONDS = 0.8    # small pause so the UI shows the "Analyzing..." state like his spinner


class StoredOutputsBackend:
    name = "stored-outputs (no model)"

    def seed_dir(self, seed_key: str) -> Path:
        d = SEED_DIR / (seed_key or SAMPLE_SEED_KEY)
        return d if d.exists() else SEED_DIR / SAMPLE_SEED_KEY

    def analyze(self, field: str, seed_key: str):
        """Return stored content for a field: str for text fields, list for tables, dict for effort_estimate."""
        time.sleep(ANALYZE_DELAY_SECONDS)
        d = self.seed_dir(seed_key)
        if field in TABLE_FIELDS or field == "effort_estimate":
            path = d / f"{field}.json"
            if not path.exists():
                return [] if field in TABLE_FIELDS else {}
            return json.loads(path.read_text(encoding="utf-8"))
        path = d / f"{field}.txt"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def diagram(self, field: str, seed_key: str, proposal_id: str) -> Path | None:
        """Copy the stored diagram image for this field into the proposal's diagram folder."""
        time.sleep(ANALYZE_DELAY_SECONDS)
        src = self.seed_dir(seed_key) / f"{DIAGRAM_FIELDS[field]}.jpg"
        if not src.exists():
            return None
        dest_dir = DIAGRAMS_DIR / proposal_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{DIAGRAM_FIELDS[field]}.jpg"
        dest.write_bytes(src.read_bytes())
        return dest

    def chat(self, question: str, sections: dict[str, dict], tables: dict[str, list]) -> str:
        """Keyword lookup over the analyzed sections: returns the best matching passages with their section names."""
        words = [w for w in re.findall(r"[a-z0-9]{3,}", question.lower()) if w not in _STOPWORDS]
        candidates: list[tuple[int, str, str]] = []
        for field, sec in sections.items():
            text = str(sec.get("content", "") or "")
            if not text.strip():
                continue
            for para in re.split(r"\n\s*\n|\n(?=[•\-\*] )", text):
                p = para.strip()
                if len(p) < 20:
                    continue
                score = sum(1 for w in words if w in p.lower())
                if score:
                    candidates.append((score, SECTION_LABELS.get(field, field), p))
        for field, rows in tables.items():
            for row in rows:
                blob = " ".join(str(v) for v in row.values())
                score = sum(1 for w in words if w in blob.lower())
                if score:
                    candidates.append((score, SECTION_LABELS.get(field, field), blob[:400]))
        if not candidates:
            return ("No model is connected in this build (stored-outputs mode), and none of the analyzed sections "
                    "mention that. Try asking about the summary, scope, architecture, roles or work breakdown.")
        candidates.sort(key=lambda c: c[0], reverse=True)
        lines = ["Stored-outputs mode: matching passages from the analyzed sections.", ""]
        seen = set()
        for score, label, passage in candidates:
            if label in seen:
                continue
            seen.add(label)
            lines.append(f"**{label}**")
            lines.append(passage[:700].replace("\n", " "))
            lines.append("")
            if len(seen) >= 3:
                break
        return "\n".join(lines).strip()


_STOPWORDS = {"the", "and", "for", "what", "are", "this", "that", "with", "from", "about", "does", "have", "how", "which", "who", "rfp", "proposal"}

BACKEND = StoredOutputsBackend()
