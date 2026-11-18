"""Department-to-Circle mapping loaded from JSON and Circle-level bid isolation."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CIRCLE_MAPPING_PATH = Path(__file__).parent / "circle_mapping.json"


def load_circle_mapping(mapping_path: Path = CIRCLE_MAPPING_PATH) -> Dict[str, Any]:
    """Load Department-to-Circle mapping and Circle configuration from JSON."""
    if not mapping_path.exists():
        raise FileNotFoundError(f"Circle mapping JSON not found at {mapping_path}")
    with open(mapping_path, "r", encoding="utf-8") as f:
        return json.load(f)


_MAPPING_DATA = load_circle_mapping()
_CIRCLES = _MAPPING_DATA["circles"]

CIRCLE_FINANCIAL_SERVICES: str = _CIRCLES["financial_services"]
CIRCLE_HEALTHCARE: str = _CIRCLES["healthcare"]
CIRCLE_RETAIL: str = _CIRCLES["retail"]
CIRCLE_ENTERPRISE: str = _CIRCLES["enterprise"]

CIRCLE_CATALOG: Tuple[str, ...] = (
    CIRCLE_FINANCIAL_SERVICES,
    CIRCLE_HEALTHCARE,
    CIRCLE_RETAIL,
    CIRCLE_ENTERPRISE,
)

CIRCLE_TO_TAB_CODE: Dict[str, str] = dict(_MAPPING_DATA["circle_to_tab_code"])
DEPARTMENT_TO_CIRCLE_MAP: Dict[str, str] = {
    k.strip().lower(): v for k, v in _MAPPING_DATA["department_to_circle"].items()
}
_CIRCLE_KEYWORD_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = tuple(
    (rule["circle"], tuple(rule["keywords"]))
    for rule in _MAPPING_DATA["keyword_rules"]
)
SAMPLE_BIDS: Tuple[Dict[str, str], ...] = tuple(_MAPPING_DATA["sample_bids"])
DIRECTORY_SAMPLE_BIDS: Tuple[Dict[str, str], ...] = tuple(
    _MAPPING_DATA.get("directory_sample_bids", [])
)
BID_TO_RFP_KEY: Dict[str, str] = dict(_MAPPING_DATA["bid_to_rfp_key"])
BID_UI_METADATA: Dict[str, Dict[str, Any]] = dict(_MAPPING_DATA["bid_ui_metadata"])
CIRCLE_METRICS: Dict[str, Dict[str, Any]] = dict(_MAPPING_DATA["circle_metrics"])
OWNER_CANDIDATES: Tuple[str, ...] = tuple(_MAPPING_DATA["owner_candidates"])


def resolve_circle(
    department: Optional[str],
    default_circle: str = CIRCLE_ENTERPRISE,
    mapping: Optional[Dict[str, Any]] = None,
) -> str:
    """Resolve an Entra ID department string to a canonical Circle using JSON config."""
    if not department or not isinstance(department, str):
        return default_circle

    normalized = " ".join(department.strip().lower().split())
    if not normalized:
        return default_circle

    exact_map = (
        {k.strip().lower(): v for k, v in mapping.get("department_to_circle", {}).items()}
        if mapping is not None
        else DEPARTMENT_TO_CIRCLE_MAP
    )
    if normalized in exact_map:
        return exact_map[normalized]

    keyword_rules = (
        [(rule["circle"], rule["keywords"]) for rule in mapping.get("keyword_rules", [])]
        if mapping is not None
        else _CIRCLE_KEYWORD_RULES
    )
    for circle_name, keywords in keyword_rules:
        if any(keyword in normalized for keyword in keywords):
            return circle_name

    return default_circle


def filter_bids_for_circle(
    bids: List[Dict[str, Any]],
    user_circle: Optional[str],
) -> List[Dict[str, Any]]:
    """Filter opportunity/bid records to include only those belonging to user_circle."""
    if not user_circle:
        return []
    target = user_circle.strip().lower()
    return [
        bid for bid in bids
        if isinstance(bid.get("circle"), str) and bid["circle"].strip().lower() == target
    ]
