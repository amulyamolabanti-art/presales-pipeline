"""SharePoint COE Directory & User Directory loader and Step 2 COE rule matcher."""
import csv
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from config import Config

AUTH_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUTH_DIR.parents[2]

LOCAL_SHAREPOINT_DIR = REPO_ROOT / "local_sharepoint_data"
DEFAULT_LOCAL_COE_CANDIDATES: Tuple[Path, ...] = (
    LOCAL_SHAREPOINT_DIR / "COE_Directory" / "COE_Directory.json",
    LOCAL_SHAREPOINT_DIR / "COE_Directory" / "COE_Directory.csv",
)
DEFAULT_LOCAL_USER_CANDIDATES: Tuple[Path, ...] = (
    LOCAL_SHAREPOINT_DIR / "User_Directory" / "User_Directory.json",
    LOCAL_SHAREPOINT_DIR / "User_Directory" / "User_Directory.csv",
)

FALLBACK_COE_MAPPING_PATH = AUTH_DIR / "coe_mapping.json"
FALLBACK_USER_MAPPING_PATH = AUTH_DIR / "user_circle_mapping.json"

_CIRCLE_ALIAS_MAP: Dict[str, str] = {
    "testing": "Testing",
    "qa": "Testing",
    "quality engineering": "Testing",
    "platform": "Platform",
    "cloud": "Platform",
    "cloud & platform": "Platform",
    "data & insights": "Data & Insights",
    "d&i": "Data & Insights",
    "d & i": "Data & Insights",
    "data insights": "Data & Insights",
    "data & ai": "Data & Insights",
    "salesforce": "Salesforce",
    "sfdc": "Salesforce",
}


def normalize_directory_circle(value: Optional[str]) -> str:
    """Normalize SharePoint Circle names and common aliases (e.g. D&I -> Data & Insights)."""
    raw = " ".join((value or "").strip().split())
    if not raw:
        return ""
    return _CIRCLE_ALIAS_MAP.get(raw.lower(), raw)


def _read_table_file(
    path: Path,
    json_list_key: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Read records uniformly from a SharePoint CSV, JSON array, or wrapper schema JSON."""
    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            rows = [dict(row) for row in csv.DictReader(handle)]
        return rows, {}

    with open(path, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], {}
    if isinstance(payload, dict):
        items = payload.get(json_list_key, [])
        return [item for item in items if isinstance(item, dict)], payload
    return [], {}


def _pick_existing_path(
    explicit_path: Optional[Path],
    env_value: str,
    local_candidates: Tuple[Path, ...],
    fallback_path: Path,
) -> Tuple[Path, bool]:
    """Select an active directory file path and flag whether it came from local SharePoint data."""
    if explicit_path is not None:
        return explicit_path, explicit_path.resolve() != fallback_path.resolve()

    if env_value:
        candidate = Path(env_value)
        if candidate.is_file():
            return candidate, True

    for local_file in local_candidates:
        if local_file.is_file():
            return local_file, True

    return fallback_path, False


def _normalize_coe_row(row: Dict[str, Any]) -> Dict[str, str]:
    """Map SharePoint COE_Directory columns (Title/CircleName, CircleID, COEName, COEEmailID)."""
    circle_raw = str(row.get("CircleName") or row.get("circle_name") or row.get("Title") or "")
    return {
        "circleName": normalize_directory_circle(circle_raw),
        "circleId": str(row.get("CircleID") or row.get("circle_id") or "").strip(),
        "coeName": str(row.get("COEName") or row.get("coe_name") or "").strip(),
        "coeEmailId": str(row.get("COEEmailID") or row.get("coe_email_id") or "").strip(),
    }


def _normalize_user_row(row: Dict[str, Any], circle_id_by_name: Dict[str, str]) -> Dict[str, str]:
    """Map SharePoint User_Directory columns (Title/UserName, UserEmail, CircleName)."""
    circle_name = normalize_directory_circle(
        str(row.get("CircleName") or row.get("circle_name") or "")
    )
    user_name = str(row.get("UserName") or row.get("user_name") or row.get("Title") or "").strip()
    user_email = str(row.get("UserEmail") or row.get("user_email") or "").strip()
    return {
        "userName": user_name,
        "userEmail": user_email,
        "circleName": circle_name,
        "circleId": circle_id_by_name.get(circle_name.lower(), ""),
    }


def load_strict_mapping_rules() -> List[Dict[str, Any]]:
    """Load Step 2 strict technology-to-COE rules from coe_mapping.json."""
    _, schema_payload = _read_table_file(FALLBACK_COE_MAPPING_PATH, "coe_mappings")
    raw_rules = schema_payload.get("strict_mapping_rules", [])
    rules: List[Dict[str, Any]] = []
    for item in raw_rules:
        if not isinstance(item, dict):
            continue
        rules.append(
            {
                "coeName": str(item.get("coe_name", "")).strip(),
                "fallbackCircle": normalize_directory_circle(str(item.get("fallback_circle", ""))),
                "ruleDescription": str(item.get("rule_description", "")).strip(),
                "matchKeywords": [str(kw).strip().lower() for kw in item.get("match_keywords", []) if kw],
            }
        )
    return rules


def load_sharepoint_directories(
    config: Optional[Config] = None,
    coe_path: Optional[Path] = None,
    user_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load SharePoint COE & User directories from local exports or sanitized JSON fallback."""
    cfg = config or Config()

    resolved_coe_path, coe_is_local = _pick_existing_path(
        coe_path,
        cfg.LOCAL_COE_DIRECTORY_PATH,
        DEFAULT_LOCAL_COE_CANDIDATES,
        FALLBACK_COE_MAPPING_PATH,
    )
    resolved_user_path, user_is_local = _pick_existing_path(
        user_path,
        cfg.LOCAL_USER_DIRECTORY_PATH,
        DEFAULT_LOCAL_USER_CANDIDATES,
        FALLBACK_USER_MAPPING_PATH,
    )

    raw_coes, _ = _read_table_file(resolved_coe_path, "coe_mappings")
    coe_directory = [
        row for row in (_normalize_coe_row(item) for item in raw_coes)
        if row["coeName"] or row["coeEmailId"]
    ]
    circle_id_by_name = {
        row["circleName"].lower(): row["circleId"]
        for row in coe_directory
        if row["circleName"] and row["circleId"]
    }

    raw_users, _ = _read_table_file(resolved_user_path, "user_mappings")
    user_directory = [
        row for row in (_normalize_user_row(item, circle_id_by_name) for item in raw_users)
        if row["userName"] or row["userEmail"]
    ]

    return {
        "source": "sharepoint_local" if (coe_is_local or user_is_local) else "json_fallback",
        "coeSourceFile": resolved_coe_path.name,
        "userSourceFile": resolved_user_path.name,
        "coeDirectory": coe_directory,
        "userDirectory": user_directory,
        "strictMappingRules": load_strict_mapping_rules(),
    }


def resolve_directory_user(
    identifier: Optional[str],
    directories: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """Find a user record in User_Directory by email, email local-part, or display name."""
    needle = (identifier or "").strip().lower()
    if not needle:
        return None
    entries = directories.get("userDirectory", [])
    for entry in entries:
        email = entry.get("userEmail", "").strip().lower()
        name = entry.get("userName", "").strip().lower()
        if email == needle or name == needle:
            return dict(entry)
    if "@" not in needle:
        normalized_needle = needle.replace(" ", ".")
        for entry in entries:
            email = entry.get("userEmail", "").strip().lower()
            name = entry.get("userName", "").strip().lower()
            local_part = email.split("@", 1)[0] if email else ""
            if local_part == needle or (name and name.replace(" ", ".") == normalized_needle):
                return dict(entry)
            first_name = name.split(" ")[0].lower() if name else ""
            email_first = local_part.split(".")[0] if "." in local_part else local_part
            if needle in (first_name, email_first) or (first_name and needle.startswith(first_name)):
                return dict(entry)
    return None


def resolve_coe_by_circle(
    circle_name: Optional[str],
    directories: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """Resolve the matching COE_Directory record for a Circle name."""
    raw = (circle_name or "").strip().lower()
    if not raw:
        return None
    aliases = {
        "d&i": "data & insights",
        "data and insights": "data & insights",
    }
    target = aliases.get(raw, raw)
    for entry in directories.get("coeDirectory", []):
        entry_circle = entry.get("circleName", "").strip().lower()
        if aliases.get(entry_circle, entry_circle) == target:
            return dict(entry)
    return None


def detect_local_directory_user(
    directories: Dict[str, Any],
    active_user_email: str = "",
) -> Optional[Dict[str, str]]:
    """Detect signed-in local user strictly against User_Directory (returns None if unlisted)."""
    import getpass
    import os

    explicit_override = (
        os.environ.get("ACTIVE_USER_EMAIL", "").strip()
        or os.environ.get("TEAMS_USER_EMAIL", "").strip()
        or active_user_email.strip()
    )
    if explicit_override:
        return resolve_directory_user(explicit_override, directories)

    os_user = (
        os.environ.get("USERNAME", "").strip()
        or os.environ.get("USER", "").strip()
        or getpass.getuser().strip()
    )
    return resolve_directory_user(os_user, directories)


def list_directory_personas(
    directories: Dict[str, Any],
    circle_to_tab_code: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    """Build UI-selectable personas dynamically from User_Directory and COE_Directory."""
    personas: List[Dict[str, str]] = []
    tab_codes = circle_to_tab_code or {}
    for entry in directories.get("userDirectory", []):
        raw_circle = entry.get("circleName", "").strip()
        coe = resolve_coe_by_circle(raw_circle, directories)
        circle = coe.get("circleName", raw_circle) if coe else raw_circle
        circle_id = coe.get("circleId", "") if coe else ""
        coe_name = coe.get("coeName", "") if coe else ""
        coe_email = coe.get("coeEmailId", "") if coe else ""
        email = entry.get("userEmail", "").strip()
        display_name = entry.get("userName", "").strip() or email
        personas.append(
            {
                "userId": email or display_name,
                "displayName": display_name,
                "email": email,
                "department": coe_name or circle,
                "jobTitle": f"{circle} ({circle_id})" if circle_id else "SharePoint User Directory",
                "circle": circle,
                "circleId": circle_id,
                "coeEmailId": coe_email,
                "tabCircleCode": tab_codes.get(circle) or circle_id or "DIGITAL_AI",
            }
        )
    return personas


def _keyword_in_text(keyword: str, lower_text: str) -> bool:
    """Check whether keyword appears on whole-word/token boundaries inside lower_text."""
    if not keyword or not lower_text:
        return False
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, lower_text) is not None


def _resolve_coe_contact(
    rule: Dict[str, Any],
    coe_directory: List[Dict[str, str]],
) -> Optional[Dict[str, str]]:
    """Resolve a Step 2 rule COE name to exact or Circle-level contact row in COE_Directory."""
    target_coe = rule.get("coeName", "").lower()
    for row in coe_directory:
        if row.get("coeName", "").strip().lower() == target_coe:
            return row

    fallback_circle = rule.get("fallbackCircle", "").lower()
    if fallback_circle:
        for row in coe_directory:
            if row.get("circleName", "").strip().lower() == fallback_circle:
                return row
    return None


def match_coes_from_rfp_text(
    rfp_text: str,
    directories: Dict[str, Any],
    circle_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply Step 2 strict mapping rules against RFP text and return COE Directory contacts."""
    lower_text = (rfp_text or "").strip().lower()
    if not lower_text:
        return []

    coe_directory: List[Dict[str, str]] = directories.get("coeDirectory", [])
    rules: List[Dict[str, Any]] = directories.get("strictMappingRules", [])
    normalized_filter = normalize_directory_circle(circle_filter).lower() if circle_filter else ""

    matches: List[Dict[str, Any]] = []
    for rule in rules:
        matched_keywords = [
            kw for kw in rule.get("matchKeywords", [])
            if _keyword_in_text(kw, lower_text)
        ]
        if not matched_keywords:
            continue

        contact = _resolve_coe_contact(rule, coe_directory)
        resolved_circle = (contact or {}).get("circleName") or rule.get("fallbackCircle", "")
        if normalized_filter and resolved_circle.lower() != normalized_filter:
            continue

        matches.append(
            {
                "ruleCoeName": rule.get("coeName", ""),
                "ruleDescription": rule.get("ruleDescription", ""),
                "matchedKeywords": matched_keywords,
                "circleName": resolved_circle,
                "circleId": (contact or {}).get("circleId", ""),
                "coeName": (contact or {}).get("coeName") or rule.get("coeName", ""),
                "coeEmailId": (contact or {}).get("coeEmailId", ""),
            }
        )

    return matches
