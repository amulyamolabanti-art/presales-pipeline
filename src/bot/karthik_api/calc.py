"""Pure calculations ported from rfp_core.py: row normalisation, effort maths, Gantt scheduling,
and the section text -> HTML formatter. No Streamlit, no I/O."""
from __future__ import annotations

import html
import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from schema import (
    CLARIFICATION_CATEGORIES, CLARIFICATION_PRIORITIES, COMPLEXITY_KEYS, COMPLEXITY_LABELS,
    DEFAULT_COMPLEXITY_DISTRIBUTION, DEFAULT_EFFORT_MATRIX, DEFAULT_EFFORT_MATRIX_COLUMN_HELP,
    WORK_BREAKDOWN_COLUMNS, WORKING_DAYS_PER_MONTH,
)


def to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        text = str(value)
        numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
        return float(numbers[0]) if numbers else default


# ---------------------------------------------------------------- table rows

def normalize_work_breakdown_row(row: dict) -> dict:
    normalized = {key: "" for key in WORK_BREAKDOWN_COLUMNS}
    if not isinstance(row, dict):
        return normalized
    aliases = {
        "person_days": "pd", "person_day": "pd", "persondays": "pd", "effort_pd": "pd", "effort": "pd",
        "rfp_reference": "rfp_section_reference", "rfp_section": "rfp_section_reference",
        "section_reference": "rfp_section_reference", "reference": "rfp_section_reference",
    }
    for raw_key, value in row.items():
        key = str(raw_key).strip().lower().replace(" ", "_").replace("-", "_")
        key = aliases.get(key, key)
        if key in normalized:
            normalized[key] = str(value).strip() if value is not None else ""
    return normalized


def sum_work_breakdown_pd(rows: list[dict]) -> float:
    total = 0.0
    for row in rows or []:
        text = str(normalize_work_breakdown_row(row).get("pd", "")).strip()
        numbers = [float(m) for m in re.findall(r"\d+(?:\.\d+)?", text)]
        if numbers:
            total += max(numbers)
    return round(total, 2)


def normalize_clarification_row(row: dict, number: int | None = None) -> dict:
    row = row if isinstance(row, dict) else {}
    cat = str(row.get("category", "") or "").strip()
    cat = {c.lower(): c for c in CLARIFICATION_CATEGORIES}.get(cat.lower(), cat)
    pri = str(row.get("priority", "") or "").strip()
    pri = {p.lower(): p for p in CLARIFICATION_PRIORITIES}.get(pri.lower(), pri)
    return {
        "number": str(number if number is not None else row.get("number", "") or "").strip(),
        "category": cat,
        "question": str(row.get("question", "") or "").strip(),
        "why_asking": str(row.get("why_asking", "") or "").strip(),
        "source_context": str(row.get("source_context", "") or "").strip(),
        "priority": pri,
    }


def normalize_simple_row(row: dict, columns: dict) -> dict:
    row = row if isinstance(row, dict) else {}
    return {key: str(row.get(key, "") or "").strip() for key in columns}


# ---------------------------------------------------------------- effort maths

def default_effort_matrix_size_tooltips() -> dict[str, str]:
    return {r["size"].upper(): r["tooltip"] for r in DEFAULT_EFFORT_MATRIX}


def default_effort_state() -> dict:
    return {
        "matrix": [dict(r) for r in DEFAULT_EFFORT_MATRIX],
        "distribution": dict(DEFAULT_COMPLEXITY_DISTRIBUTION),
        "inventory_rows": [{"item": "", "inventory": 0, "assumption": ""}],
        "matrix_column_help": dict(DEFAULT_EFFORT_MATRIX_COLUMN_HELP),
    }


def normalize_effort_matrix_row(row: dict) -> dict:
    size = str(row.get("size", "")).strip().upper() or "M"
    complexity = str(row.get("complexity", "")).strip() or COMPLEXITY_LABELS.get(size.lower(), size)
    discovery = to_float(row.get("discovery"))
    develop = to_float(row.get("develop"))
    integration = to_float(row.get("integration"))
    deployment = to_float(row.get("deployment"))
    contingency = to_float(row.get("contingency"))
    if contingency > 1:
        contingency = contingency / 100.0
    computed_total = round((discovery + develop + integration + deployment) * (1 + contingency), 2)
    total_pd = to_float(row.get("total_pd"), computed_total)
    if total_pd <= 0:
        total_pd = computed_total if computed_total > 0 else 1.0
    tooltip = str(row.get("tooltip", "") or "").strip() or default_effort_matrix_size_tooltips().get(size, "")
    return {
        "size": size, "complexity": complexity, "discovery": discovery, "develop": develop,
        "integration": integration, "deployment": deployment, "contingency": contingency,
        "total_pd": total_pd, "tooltip": tooltip,
    }


def recompute_effort_matrix_totals(matrix_rows: list[dict]) -> list[dict]:
    out = []
    for row in matrix_rows:
        n = normalize_effort_matrix_row(row)
        base = n["discovery"] + n["develop"] + n["integration"] + n["deployment"]
        n["total_pd"] = round(base * (1 + n["contingency"]), 2)
        if n["total_pd"] <= 0:
            n["total_pd"] = 1.0
        out.append(n)
    return out


def matrix_total_pd_by_size(matrix_rows: list[dict]) -> dict[str, float]:
    totals = {r["size"].lower(): float(r["total_pd"]) for r in DEFAULT_EFFORT_MATRIX}
    for row in recompute_effort_matrix_totals(matrix_rows):
        key = row["size"].lower()
        if key in COMPLEXITY_KEYS and float(row["total_pd"]) > 0:
            totals[key] = float(row["total_pd"])
    return totals


def normalize_distribution(dist: dict) -> dict:
    dist = dist or {}
    return {k: max(to_float(dist.get(k), DEFAULT_COMPLEXITY_DISTRIBUTION[k]), 0.0) for k in COMPLEXITY_KEYS}


def normalize_inventory_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows or []:
        row = row if isinstance(row, dict) else {}
        out.append({
            "item": str(row.get("item", "") or "").strip(),
            "inventory": max(int(round(to_float(row.get("inventory")))), 0),
            "assumption": str(row.get("assumption", "") or "").strip(),
        })
    return out or [{"item": "", "inventory": 0, "assumption": ""}]


def calculate_effort_inventory_rows(inventory_rows, distribution, matrix_rows) -> list[dict]:
    pd_by_size = matrix_total_pd_by_size(matrix_rows)
    dist = normalize_distribution(distribution)
    out = []
    for row in normalize_inventory_rows(inventory_rows):
        counts = {k: round(row["inventory"] * dist[k], 2) for k in COMPLEXITY_KEYS}
        efforts = {k: round(counts[k] * pd_by_size[k], 2) for k in COMPLEXITY_KEYS}
        out.append({
            **row,
            **{f"{k}_count": counts[k] for k in COMPLEXITY_KEYS},
            **{f"{k}_effort": efforts[k] for k in COMPLEXITY_KEYS},
            "total_pd": round(sum(efforts.values()), 2),
        })
    return out


def sum_effort_estimate_pd(state: dict) -> float:
    rows = calculate_effort_inventory_rows(
        state.get("inventory_rows", []), state.get("distribution", DEFAULT_COMPLEXITY_DISTRIBUTION),
        state.get("matrix", DEFAULT_EFFORT_MATRIX),
    )
    return round(sum(to_float(r.get("total_pd")) for r in rows), 2)


def effort_phase_summary(state: dict) -> dict:
    rows = calculate_effort_inventory_rows(
        state.get("inventory_rows", []), state.get("distribution", DEFAULT_COMPLEXITY_DISTRIBUTION),
        state.get("matrix", DEFAULT_EFFORT_MATRIX),
    )
    pd_by_size = matrix_total_pd_by_size(state.get("matrix", DEFAULT_EFFORT_MATRIX))
    matrix_map = {r["size"].lower(): r for r in recompute_effort_matrix_totals(state.get("matrix", []))}
    discovery = develop = integration = deployment = 0.0
    for row in rows:
        for k in COMPLEXITY_KEYS:
            count = to_float(row.get(f"{k}_count"))
            m = matrix_map.get(k, {})
            discovery += count * to_float(m.get("discovery"))
            develop += count * to_float(m.get("develop"))
            integration += count * to_float(m.get("integration"))
            deployment += count * to_float(m.get("deployment"))
    total_pd = sum_effort_estimate_pd(state)
    return {
        "total_inventory": round(sum(to_float(r.get("inventory")) for r in rows), 2),
        "discovery": round(discovery, 2), "develop": round(develop, 2),
        "integration": round(integration, 2), "deployment": round(deployment, 2),
        "total_pd": total_pd,
        "resource_months": round(total_pd / 20.0, 2) if total_pd else 0.0,
        "pd_by_size": pd_by_size,
    }


def reconcile_wbs_to_effort_total(wbs_rows: list[dict], effort_total: float) -> list[dict]:
    """Scale Work Breakdown PD values so their sum equals the Effort Estimate total."""
    current_total = sum_work_breakdown_pd(wbs_rows)
    if effort_total <= 0 or current_total <= 0:
        return [normalize_work_breakdown_row(r) for r in wbs_rows]
    scale = effort_total / current_total
    scaled, numeric_indexes = [], []
    for index, row in enumerate(wbs_rows):
        n = normalize_work_breakdown_row(row)
        numbers = [float(m) for m in re.findall(r"\d+(?:\.\d+)?", str(n.get("pd", "")))]
        if numbers:
            n["pd"] = str(round(max(numbers) * scale, 2))
            numeric_indexes.append(index)
        scaled.append(n)
    drift = round(effort_total - sum_work_breakdown_pd(scaled), 2)
    if abs(drift) >= 0.01 and numeric_indexes:
        last = scaled[numeric_indexes[-1]]
        last["pd"] = str(round(max(to_float(last.get("pd")) + drift, 0.0), 2))
    return scaled


def reconcile_effort_to_wbs_total(state: dict, wbs_total: float) -> dict:
    """Scale inventory so the Effort Estimate total equals the Work Breakdown total."""
    current_total = sum_effort_estimate_pd(state)
    if wbs_total <= 0 or current_total <= 0:
        return state
    scale = wbs_total / current_total
    scaled_rows = [
        {"item": r["item"], "inventory": max(int(round(r["inventory"] * scale)), 0), "assumption": r["assumption"]}
        for r in normalize_inventory_rows(state.get("inventory_rows", []))
    ]
    scaled_state = {
        **state,
        "matrix": state.get("matrix", DEFAULT_EFFORT_MATRIX),
        "distribution": state.get("distribution", dict(DEFAULT_COMPLEXITY_DISTRIBUTION)),
        "inventory_rows": scaled_rows or [{"item": "", "inventory": 0, "assumption": ""}],
    }
    drift = round(wbs_total - sum_effort_estimate_pd(scaled_state), 2)
    if abs(drift) >= 0.01 and scaled_rows:
        pd_by_size = matrix_total_pd_by_size(scaled_state["matrix"])
        dist = normalize_distribution(scaled_state["distribution"])
        blended = sum(dist[k] * pd_by_size[k] for k in COMPLEXITY_KEYS)
        if blended > 0:
            largest = max(scaled_rows, key=lambda r: to_float(r.get("inventory")))
            largest["inventory"] = max(int(round(to_float(largest.get("inventory")) + drift / blended)), 0)
    return scaled_state


# ---------------------------------------------------------------- gantt scheduling

def parse_person_days(value) -> float:
    text = str(value or "").strip()
    numbers = [float(m) for m in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return 1.0
    duration = max(numbers)
    return duration if duration > 0 else 1.0


def pd_to_calendar_days(person_days: float, resources: int) -> int:
    resources = max(int(resources or 1), 1)
    working_days = max(float(person_days), 0.0) / resources
    return max(1, int(math.ceil(working_days * (30.0 / WORKING_DAYS_PER_MONTH))))


def _extract_description_section(description: str, label: str) -> str:
    pattern = rf"{label}\s*:\s*(.*?)(?=\n\s*(?:Deliverables|Dependencies|Can Run In Parallel With|Critical Path|\[SCHEDULE\])\s*:|\Z)"
    m = re.search(pattern, description or "", flags=re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _split_schedule_names(text: str) -> list[str]:
    cleaned = re.sub(r"[\r\n]+", "|", text or "")
    names = []
    for part in re.split(r"[|;,]+", cleaned):
        name = part.strip(" .-•*\t\"'")
        if not name or name.lower() in {"none", "n/a", "na", "nil", "not applicable", "-"}:
            continue
        names.append(name)
    return names


def _extract_schedule_key_values(description: str, key: str) -> list[str]:
    values = []
    for m in re.finditer(rf"(?im)^\s*{re.escape(key)}\s*=\s*(.+?)\s*$", description or ""):
        values.extend(_split_schedule_names(m.group(1)))
    return values


def parse_wbs_schedule_attributes(description: str) -> dict:
    text = description or ""
    deps = _extract_schedule_key_values(text, "DEPENDENCY") + _extract_schedule_key_values(text, "DEPENDENCIES")
    if not deps:
        deps = _split_schedule_names(_extract_description_section(text, "Dependencies"))
    parallel = (_extract_schedule_key_values(text, "PARALLEL") + _extract_schedule_key_values(text, "PARALLEL_WITH")
                + _extract_schedule_key_values(text, "CAN_RUN_IN_PARALLEL_WITH"))
    if not parallel:
        parallel = _split_schedule_names(_extract_description_section(text, "Can Run In Parallel With"))
    critical_vals = _extract_schedule_key_values(text, "CRITICAL_PATH")
    critical_raw = (critical_vals[0] if critical_vals else _extract_description_section(text, "Critical Path")).strip().lower()
    critical = critical_raw.startswith("y") or critical_raw in {"true", "critical", "1", "yes"}

    def unique(items):
        seen, out = set(), []
        for item in items:
            if item.lower() not in seen:
                seen.add(item.lower())
                out.append(item)
        return out

    return {"dependencies": unique(deps), "parallel_with": unique(parallel), "critical_path": critical}


def _normalize_task_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def _resolve_task_refs(ref_names: list[str], task_names: list[str]) -> list[str]:
    resolved = []
    normalized_map = {_normalize_task_key(n): n for n in task_names}
    for ref in ref_names:
        key = _normalize_task_key(ref)
        if not key:
            continue
        if key in normalized_map:
            resolved.append(normalized_map[key])
            continue
        best_name, best_score = None, 0
        for cand_key, cand_name in normalized_map.items():
            if key in cand_key or cand_key in key:
                score = min(len(key), len(cand_key))
                if score > best_score:
                    best_score, best_name = score, cand_name
        if best_name:
            resolved.append(best_name)
    out = []
    for n in resolved:
        if n not in out:
            out.append(n)
    return out


def _parallel_groups(task_names, parallel_map):
    graph = {n: set() for n in task_names}
    for n in task_names:
        for peer in parallel_map.get(n, []):
            if peer in graph and peer != n:
                graph[n].add(peer)
                graph[peer].add(n)
    seen, groups = set(), []
    for n in task_names:
        if n in seen:
            continue
        stack, comp = [n], []
        seen.add(n)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for peer in graph[cur]:
                if peer not in seen:
                    seen.add(peer)
                    stack.append(peer)
        groups.append(comp)
    return groups


def build_gantt_rows(rows: list[dict], project_start: date, resources: int = 1) -> list[dict]:
    """Task schedule using DEPENDENCY / PARALLEL / CRITICAL_PATH and resource loading. Dates as ISO strings."""
    prepared = []
    for index, row in enumerate(rows, start=1):
        n = normalize_work_breakdown_row(row)
        if not any(str(n.get(c, "")).strip() for c in WORK_BREAKDOWN_COLUMNS):
            continue
        task_name = (n.get("task") or n.get("activity") or f"Task {index}").strip()
        phase = (n.get("phase") or "Unassigned").strip() or "Unassigned"
        person_days = parse_person_days(n.get("pd", ""))
        attrs = parse_wbs_schedule_attributes(n.get("description", ""))
        prepared.append({
            "seq": index, "task": task_name, "phase": phase, "duration_pd": person_days,
            "calendar_days": pd_to_calendar_days(person_days, resources),
            "activity": n.get("activity", ""), "description": n.get("description", ""),
            "rfp_section_reference": n.get("rfp_section_reference", ""),
            "dependencies": attrs["dependencies"], "parallel_with": attrs["parallel_with"],
            "critical_path": attrs["critical_path"],
        })
    if not prepared:
        return []

    seen_names: dict[str, int] = {}
    for item in prepared:
        base = item["task"]
        count = seen_names.get(base, 0) + 1
        seen_names[base] = count
        if count > 1:
            item["task"] = f"{base} #{count}"

    task_names = [i["task"] for i in prepared]
    for item in prepared:
        item["dependencies"] = _resolve_task_refs(item["dependencies"], task_names)
        item["parallel_with"] = _resolve_task_refs(item["parallel_with"], task_names)
    name_to_item = {i["task"]: i for i in prepared}
    for item in prepared:
        for peer in list(item["parallel_with"]):
            peer_item = name_to_item.get(peer)
            if peer_item is not None and item["task"] not in peer_item["parallel_with"]:
                peer_item["parallel_with"].append(item["task"])
    groups = _parallel_groups(task_names, {i["task"]: i["parallel_with"] for i in prepared})

    start_anchor = datetime.combine(project_start, datetime.min.time())
    has_links = any(i["dependencies"] or i["parallel_with"] for i in prepared)

    earliest: dict[str, datetime] = {}
    finish: dict[str, datetime] = {}
    cursor = start_anchor
    remaining = {i["task"]: i for i in prepared}
    safety = 0
    while remaining and safety < len(prepared) * 4:
        safety += 1
        progress = False
        for name, item in list(remaining.items()):
            deps = item["dependencies"]
            if any(d not in finish for d in deps):
                continue
            if deps:
                start_dt = max(finish[d] for d in deps)
            elif has_links:
                start_dt = start_anchor
            else:
                start_dt = cursor
            finish_dt = start_dt + timedelta(days=max(int(item["calendar_days"]), 1))
            earliest[name], finish[name] = start_dt, finish_dt
            cursor = max(cursor, finish_dt)
            del remaining[name]
            progress = True
        if not progress:
            name, item = next(iter(remaining.items()))
            start_dt = cursor
            finish_dt = start_dt + timedelta(days=max(int(item["calendar_days"]), 1))
            earliest[name], finish[name] = start_dt, finish_dt
            cursor = finish_dt
            del remaining[name]

    def align_groups(respect_deps: bool):
        for group in groups:
            if len(group) < 2:
                continue
            group_start = max(earliest[n] for n in group)
            if respect_deps:
                for n in group:
                    deps = name_to_item[n]["dependencies"]
                    if deps:
                        group_start = max(group_start, max(finish[d] for d in deps if d in finish))
            for n in group:
                earliest[n] = group_start
                finish[n] = group_start + timedelta(days=max(int(name_to_item[n]["calendar_days"]), 1))

    align_groups(False)
    for _ in range(len(prepared) + 1):
        changed = False
        for name in task_names:
            deps = name_to_item[name]["dependencies"]
            if not deps:
                continue
            min_start = max(finish[d] for d in deps if d in finish)
            if earliest[name] < min_start:
                earliest[name] = min_start
                finish[name] = min_start + timedelta(days=max(int(name_to_item[name]["calendar_days"]), 1))
                changed = True
        if not changed:
            break
    align_groups(True)

    return [{
        **item,
        "start": earliest[item["task"]].date().isoformat(),
        "finish": finish[item["task"]].date().isoformat(),
        "dependencies_text": ", ".join(item["dependencies"]) or "None",
        "parallel_with_text": ", ".join(item["parallel_with"]) or "None",
        "critical_path_text": "Yes" if item["critical_path"] else "No",
    } for item in prepared]


def build_phase_gantt_rows(task_rows: list[dict]) -> list[dict]:
    if not task_rows:
        return []
    phases = []
    for r in task_rows:
        if r["phase"] not in phases:
            phases.append(r["phase"])
    out = []
    for idx, phase in enumerate(phases, start=1):
        tasks = [r for r in task_rows if r["phase"] == phase]
        start = min(r["start"] for r in tasks)
        fin = max(r["finish"] for r in tasks)
        if fin <= start:
            fin = (date.fromisoformat(start) + timedelta(days=1)).isoformat()
        out.append({
            "seq": idx, "phase": phase, "task": phase, "start": start, "finish": fin,
            "duration_pd": round(sum(float(r["duration_pd"]) for r in tasks), 2),
            "task_count": len(tasks), "activity": f"{len(tasks)} task(s)",
        })
    return out


# ---------------------------------------------------------------- section formatter (verbatim port)

_MD_TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _is_table_sep(line: str) -> bool:
    return bool(_MD_TABLE_SEP_RE.match(str(line or "").strip()))


def _split_table_row(line: str) -> list[str]:
    text = str(line or "").strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [c.strip() for c in text.split("|")]


def _inline(text: str) -> str:
    escaped = html.escape(str(text or ""))
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def _table_html(headers: list[str], rows: list[list[str]]) -> str:
    width = len(headers)
    if not width:
        return ""
    head = "".join(f"<th>{html.escape(c)}</th>" for c in headers)
    body = []
    for row in rows:
        padded = (row + [""] * width)[:width]
        cells = []
        for i, cell in enumerate(padded):
            header = headers[i].strip().lower()
            css = " class='score-col'" if header == "score" else (" class='status-col'" if header == "status" else "")
            cells.append(f"<td{css}>{_inline(cell)}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table class='doc-score-table'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _list_items_html(items: list[dict], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    parts = [f"<li>{_inline(i.get('text', ''))}{i.get('children_html', '') or ''}</li>" for i in items]
    return f"<{tag}>{''.join(parts)}</{tag}>"


def _md_chunk_html(chunk: str) -> str:
    lines = str(chunk or "").splitlines()
    out: list[str] = []
    stack: list[tuple[int, list[dict], bool]] = []

    def close_deeper(indent: int) -> None:
        while stack and stack[-1][0] > indent:
            _lvl, items, ordered = stack.pop()
            nested = _list_items_html(items, ordered)
            if stack:
                plvl, pitems, pord = stack[-1]
                if pitems:
                    pitems[-1]["children_html"] = (pitems[-1].get("children_html", "") or "") + nested
                else:
                    pitems.append({"text": "", "children_html": nested})
                stack[-1] = (plvl, pitems, pord)
            else:
                out.append(nested)

    def is_list_line(line: str) -> bool:
        t = line.rstrip()
        return bool(re.match(r"^(\s*)[•\-\*]\s+(.*)$", t) or re.match(r"^(\s*)\d+\.\s+(.*)$", t))

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if stack and j < len(lines) and is_list_line(lines[j]):
                i += 1
                continue
            close_deeper(-1)
            i += 1
            continue
        if stripped.startswith("#"):
            close_deeper(-1)
            level = min(max(len(stripped) - len(stripped.lstrip("#")), 1), 3)
            out.append(f"<h{level}>{_inline(stripped[level:].strip())}</h{level}>")
            i += 1
            continue
        if re.fullmatch(r"[-_]{3,}", stripped):
            close_deeper(-1)
            out.append("<hr/>")
            i += 1
            continue
        bullet = re.match(r"^(\s*)[•\-\*]\s+(.*)$", raw.rstrip())
        numbered = re.match(r"^(\s*)\d+\.\s+(.*)$", raw.rstrip())
        match = bullet or numbered
        if match:
            indent = len(match.group(1).replace("\t", "  "))
            text = match.group(2).strip()
            ordered = numbered is not None
            close_deeper(indent)
            item = {"text": text, "children_html": ""}
            if stack and stack[-1][0] == indent:
                lvl, items, pord = stack[-1]
                if pord != ordered:
                    close_deeper(indent - 1)
                    stack.append((indent, [item], ordered))
                else:
                    items.append(item)
                    stack[-1] = (lvl, items, ordered)
            else:
                stack.append((indent, [item], ordered))
            i += 1
            continue
        close_deeper(-1)
        out.append(f"<p>{_inline(stripped)}</p>")
        i += 1
    close_deeper(-1)
    return "".join(out)


def section_content_html(text: str) -> str:
    content = str(text or "")
    if not content.strip():
        return "<p class='section-content-empty'>No content yet.</p>"
    lines = content.splitlines()
    parts: list[str] = []
    md: list[str] = []
    i = 0

    def flush():
        nonlocal md
        chunk = "\n".join(md).strip()
        if chunk:
            parts.append(_md_chunk_html(chunk))
        md = []

    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if "|" in line and _is_table_sep(nxt):
            flush()
            headers = _split_table_row(line)
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                if _is_table_sep(lines[i]):
                    break
                rows.append(_split_table_row(lines[i]))
                i += 1
            t = _table_html(headers, rows)
            if t:
                parts.append(t)
            continue
        md.append(line)
        i += 1
    flush()
    return "".join(parts)
