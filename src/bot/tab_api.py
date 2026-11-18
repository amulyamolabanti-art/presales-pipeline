"""HTTP routes and combined S0-YK-04 (SSO/Circle) + S0-YK-05 (Intake Card) APIs."""
import os
import sys
from typing import Any, Callable, Dict, List, Optional

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path
_BOT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BOT_DIR.parent.parent
for _p in (str(_BOT_DIR), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from auth import (
    BID_TO_RFP_KEY,
    BID_UI_METADATA,
    CIRCLE_ENTERPRISE,
    CIRCLE_METRICS,
    CIRCLE_TO_TAB_CODE,
    DIRECTORY_SAMPLE_BIDS,
    MOCK_PROFILES,
    OWNER_CANDIDATES,
    SAMPLE_BIDS,
    SSOAuthenticationError,
    SSOConfigurationError,
    SSOService,
    UserProfile,
    filter_bids_for_circle,
    list_directory_personas,
    load_sharepoint_directories,
    match_coes_from_rfp_text,
    resolve_circle,
)
from cards.rfp_catalog import SAMPLE_RFPS
from config import Config

DEFAULT_INTAKE_STATUS = "Pending Pre-Sales Confirmation (business_flow_v2, Step 2)"

_BID_TECH_CONTEXT: Dict[str, str] = {
    "OPP-2026-001": "AWS S3 Lambda Azure Synapse BI Reporting Power BI claims triage",
    "OPP-2026-002": "Snowflake Databricks Azure Data Factory Synapse star schema dimensional modelling BI Reporting",
    "OPP-2026-003": "GCP BigQuery Dataflow Cloud Storage AWS S3 BI Reporting",
    "OPP-2026-004": "Azure Microsoft Fabric Databricks Snowflake Data Vault BI Reporting",
    "OPP-2026-PLT-01": "Azure Landing Zone AKS Kubernetes Microservices AWS S3 BI Reporting Power BI",
    "OPP-2026-DNI-01": "Snowflake Databricks Azure Data Factory Synapse star schema BI Reporting GenAI Analytics",
    "OPP-2026-TST-01": "GCP Playwright Selenium Performance Testing ISTQB Quality Engineering BI Reporting",
    "OPP-2026-SFDC-01": "Salesforce Financial Services Cloud Agentforce CRM MuleSoft BI Reporting",
}
_ALL_SAMPLE_BIDS: List[Dict[str, str]] = list(SAMPLE_BIDS) + list(DIRECTORY_SAMPLE_BIDS)
_ZERO_METRICS: Dict[str, Any] = {
    "draftProgress": "0%",
    "activeBids": 0,
    "reqsMapped": 0,
    "compliance": "0%",
    "smeGaps": 0,
    "dueThisWeek": 0,
}

# In-memory workflow state keyed by RFP ID (e.g. HMI-IT-2026-114)
_intake_states: Dict[str, Dict[str, Any]] = {}


def reset_intake_states() -> None:
    """Clear mutable intake workflow state (primarily for unit testing)."""
    _intake_states.clear()


def extract_http_sso_token(request: Request) -> Optional[str]:
    """Extract Teams SSO JWT from Authorization Bearer or X-Teams-SSO-Token header."""
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    sso_header = request.headers.get("x-teams-sso-token")
    if sso_header and sso_header.strip():
        return sso_header.strip()
    return None


def extract_http_user_hint(request: Request) -> Optional[str]:
    """Extract optional signed-in Teams user email/UPN hint from HTTP header."""
    hint = request.headers.get("x-teams-user-hint")
    if hint and hint.strip():
        return hint.strip()
    return None


def serialize_user_profile(profile: UserProfile, config: Config) -> Dict[str, Any]:
    """Convert resolved UserProfile and config mode into JSON-ready session dict."""
    tab_code = CIRCLE_TO_TAB_CODE.get(profile.circle, profile.circle_id or "DIGITAL_AI")
    return {
        "userId": profile.user_id,
        "displayName": profile.display_name,
        "email": profile.email,
        "department": profile.department,
        "jobTitle": profile.job_title,
        "circle": profile.circle,
        "circleId": profile.circle_id,
        "coeEmailId": profile.coe_email_id,
        "tabCircleCode": tab_code,
        "authSource": profile.auth_source,
        "ssoMode": config.SSO_MODE,
        "useMockSso": config.is_mock_sso,
    }


def list_mock_personas(
    config: Config,
    directories: Optional[Dict[str, Any]] = None,
    profile: Optional[UserProfile] = None,
) -> List[Dict[str, str]]:
    """Return legacy mock personas only when explicitly configured; hidden in User_Directory auto mode."""
    if not config.is_mock_sso:
        return []
    if (config.DEFAULT_MOCK_USER_ID or "auto").strip().lower() == "auto":
        return []
    if profile is not None and profile.auth_source.startswith("directory"):
        return []
    personas: List[Dict[str, str]] = []
    for key, mock_entry in MOCK_PROFILES.items():
        circle = resolve_circle(mock_entry.get("department"), config.DEFAULT_CIRCLE)
        personas.append(
            {
                "userId": key,
                "displayName": mock_entry["display_name"],
                "department": mock_entry["department"],
                "jobTitle": mock_entry["job_title"],
                "circle": circle,
                "tabCircleCode": CIRCLE_TO_TAB_CODE.get(circle, "DIGITAL_AI"),
            }
        )
    return personas


def _build_intake_details(bid: Dict[str, str], ui_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Combine S0-YK-05 RFP catalog card data with current interactive state."""
    opp_id = bid["opportunityId"]
    rfp_key = BID_TO_RFP_KEY.get(opp_id)
    rfp_entry = SAMPLE_RFPS.get(rfp_key, {}) if rfp_key else {}

    raw_team: Dict[str, str] = rfp_entry.get(
        "team",
        ui_meta.get("suggestedTeam", {}),
    )
    suggested_team = [
        {"role": role.rstrip(":"), "member": member}
        for role, member in raw_team.items()
    ]
    rfp_id = rfp_entry.get("rfp_id") or ui_meta.get("rfpId", opp_id)
    default_owner = raw_team.get("Bid Manager:") or "Pending Assignment"
    saved_state = _intake_states.get(rfp_id, {})

    return {
        "rfpId": rfp_id,
        "intakeClientName": rfp_entry.get("client") or bid["clientName"],
        "scope": rfp_entry.get("scope") or bid["bidTitle"],
        "dueDateFormatted": rfp_entry.get("due_date") or ui_meta.get(
            "dueDateFormatted", bid.get("dueDate", "")
        ),
        "intakeCircleLabel": rfp_entry.get("circle") or ui_meta.get(
            "circleLabel", bid.get("circle", CIRCLE_ENTERPRISE)
        ),
        "icon": rfp_entry.get("icon") or ui_meta.get("icon", "📋"),
        "fileSource": rfp_entry.get("file_source") or bid.get("source", ""),
        "suggestedTeam": suggested_team,
        "bidOwner": saved_state.get("bidOwner", default_owner),
        "ownerAssigned": saved_state.get("ownerAssigned", False),
        "teamConfirmed": saved_state.get("teamConfirmed", False),
        "intakeStatus": saved_state.get("intakeStatus", DEFAULT_INTAKE_STATUS),
        "lastActionMessage": saved_state.get("lastActionMessage", ""),
    }


def enrich_bid_for_tab(
    bid: Dict[str, str],
    directories: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Attach JSON-configured Tab UI metadata, Step 2 COE routing, and Intake Card state."""
    opp_id = bid["opportunityId"]
    tab_code = CIRCLE_TO_TAB_CODE.get(bid.get("circle", ""), "DIGITAL_AI")
    ui_meta = BID_UI_METADATA.get(
        opp_id,
        {
            "rfpId": opp_id,
            "tabCircleCode": tab_code,
            "circleLabel": bid.get("circle", CIRCLE_ENTERPRISE),
            "circleBadgeClass": "badge-draft",
            "displayDueDate": bid.get("dueDate", ""),
            "stage": "Stage 2: Triage",
            "stageBadgeClass": "badge-triage",
            "detailKey": "Harborline",
            "icon": "📋",
            "compliance": [],
            "channelName": "#circle-rfp",
        },
    )
    enriched = dict(bid)
    enriched.update({k: v for k, v in ui_meta.items() if k != "suggestedTeam"})
    enriched.update(_build_intake_details(bid, ui_meta))
    if directories is not None:
        tech_text = f"{bid.get('bidTitle', '')} {_BID_TECH_CONTEXT.get(opp_id, '')}"
        enriched["coeMatches"] = match_coes_from_rfp_text(tech_text, directories)
    if enriched.get("teamConfirmed"):
        enriched["stage"] = "Stage 3: Workspace Provisioned"
        enriched["stageBadgeClass"] = "badge-submitted"
    return enriched


def _find_bid_by_rfp_id(rfp_id: str) -> Optional[Dict[str, Any]]:
    """Locate enriched bid record matching an opportunityId or S0-YK-05 rfpId."""
    target = (rfp_id or "").strip().lower()
    if not target:
        return None
    for bid in _ALL_SAMPLE_BIDS:
        enriched = enrich_bid_for_tab(bid)
        if (
            enriched["rfpId"].lower() == target
            or enriched["opportunityId"].lower() == target
        ):
            return enriched
    return None


def assign_intake_bid_owner(
    rfp_id: str,
    bid_owner: str,
    user_circle: str,
) -> Dict[str, Any]:
    """Assign a bid owner on an Intake Card while enforcing Circle isolation."""
    bid = _find_bid_by_rfp_id(rfp_id)
    if bid is None:
        raise ValueError(f"Unknown RFP reference '{rfp_id}'.")
    if bid["circle"] != user_circle:
        raise PermissionError(
            f"Access denied: {bid['rfpId']} belongs to {bid['circle']} Circle."
        )
    cleaned_owner = (bid_owner or "").strip() or "Circle Lead Reassignment Pending"
    canonical_rfp_id = bid["rfpId"]
    prior = _intake_states.get(canonical_rfp_id, {})
    confirmed = prior.get("teamConfirmed", False)
    status = (
        "Team Confirmed & Bid Owner Assigned (Step 3 Active)"
        if confirmed
        else f"Bid Owner Assigned ({cleaned_owner}) — Pending Team Confirmation"
    )
    msg = (
        f"Bid owner set to {cleaned_owner} for {bid['intakeClientName']} "
        f"({canonical_rfp_id})."
    )
    _intake_states[canonical_rfp_id] = {
        **prior,
        "bidOwner": cleaned_owner,
        "ownerAssigned": True,
        "intakeStatus": status,
        "lastActionMessage": msg,
    }
    return {"bid": _find_bid_by_rfp_id(canonical_rfp_id), "message": msg}


def confirm_intake_team(rfp_id: str, user_circle: str) -> Dict[str, Any]:
    """Confirm suggested bid team on an Intake Card while enforcing Circle isolation."""
    bid = _find_bid_by_rfp_id(rfp_id)
    if bid is None:
        raise ValueError(f"Unknown RFP reference '{rfp_id}'.")
    if bid["circle"] != user_circle:
        raise PermissionError(
            f"Access denied: {bid['rfpId']} belongs to {bid['circle']} Circle."
        )
    canonical_rfp_id = bid["rfpId"]
    prior = _intake_states.get(canonical_rfp_id, {})
    msg = (
        f"Bid team confirmed for {bid['intakeClientName']} ({canonical_rfp_id}). "
        f"Proceeding to Step 3: Channel {bid['channelName']} & Workspace Scaffolding."
    )
    _intake_states[canonical_rfp_id] = {
        **prior,
        "teamConfirmed": True,
        "intakeStatus": "Team Confirmed — Proceeding to Step 3: Channel & Workspace",
        "lastActionMessage": msg,
    }
    return {"bid": _find_bid_by_rfp_id(canonical_rfp_id), "message": msg}


def build_bids_payload(
    sso_service: SSOService,
    config: Config,
    sso_token: Optional[str] = None,
    persona: Optional[str] = None,
    user_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve user identity and return only Circle-isolated bids and SharePoint directories."""
    auto_directory_mode = (
        config.is_mock_sso and (config.DEFAULT_MOCK_USER_ID or "auto").strip().lower() == "auto"
    )
    requested_persona = (
        None
        if auto_directory_mode
        else (persona.strip() if (config.is_mock_sso and persona and persona.strip()) else None)
    )
    effective_hint = None if requested_persona else (user_hint if config.is_mock_sso else None)
    profile = sso_service.resolve_user_profile(
        user_assertion=sso_token,
        mock_user_id=requested_persona or config.DEFAULT_MOCK_USER_ID,
        user_hint=effective_hint,
    )
    if profile.circle == "Unassigned":
        raise PermissionError(
            "Access restricted: Only users listed in the SharePoint User_Directory can open this app."
        )
    directories = load_sharepoint_directories(config)
    catalog_bids = (
        list(DIRECTORY_SAMPLE_BIDS)
        if profile.auth_source.startswith("directory")
        else list(_ALL_SAMPLE_BIDS)
    )

    # Check for live SQL opportunities
    try:
        from karthik_api.repo import get_sql_connection
        conn = get_sql_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM [Opportunity]")
            cols = [c[0].lower() for c in cursor.description]
            sql_bids = []
            for row in cursor.fetchall():
                r = dict(zip(cols, row))
                opp_id = r.get("opportunityid")
                if opp_id:
                    sql_bids.append({
                        "opportunityId": str(opp_id),
                        "clientName": r.get("clientname") or r.get("client") or "",
                        "bidTitle": r.get("bidtitle") or r.get("title") or r.get("name") or str(opp_id),
                        "circle": r.get("circle") or r.get("industry") or "Enterprise",
                        "dueDate": str(r.get("duedate", "")).split()[0] if r.get("duedate") else "2026-12-31",
                        "source": "Azure SQL [Opportunity]",
                        "currentStage": r.get("currentstage") or r.get("status") or "In analysis",
                        "status": r.get("status") or "Active",
                        "bidOwnerEmail": r.get("bidowneremail") or "",
                    })
            conn.close()
            if sql_bids:
                sql_ids = {b["opportunityId"] for b in sql_bids}
                catalog_bids = sql_bids + [b for b in catalog_bids if b.get("opportunityId") not in sql_ids]
    except Exception as exc:
        print(f"[Azure SQL] Note: Could not query Opportunity table for bids: {exc}", flush=True)

    visible_bids = filter_bids_for_circle(catalog_bids, profile.circle)
    directory_circles = {b["circle"] for b in DIRECTORY_SAMPLE_BIDS}
    total_catalog = (
        len(DIRECTORY_SAMPLE_BIDS)
        if (profile.auth_source.startswith("directory") or profile.circle in directory_circles)
        else len(SAMPLE_BIDS)
    )
    circle_owners = [
        f"{member['userName']} ({member['circleName']} Circle)"
        for member in directories.get("userDirectory", [])
        if member.get("circleName", "").strip().lower() == profile.circle.strip().lower()
        and member.get("userName")
    ]
    owner_options = list(dict.fromkeys(circle_owners + list(OWNER_CANDIDATES)))
    default_metrics = _ZERO_METRICS if profile.circle == "Unassigned" else CIRCLE_METRICS[CIRCLE_ENTERPRISE]
    return {
        "user": serialize_user_profile(profile, config),
        "availablePersonas": list_mock_personas(config, directories=directories, profile=profile),
        "ownerOptions": owner_options,
        "circle": profile.circle,
        "tabCircleCode": CIRCLE_TO_TAB_CODE.get(profile.circle, profile.circle_id or "DIGITAL_AI"),
        "isolated": True,
        "metrics": CIRCLE_METRICS.get(profile.circle, default_metrics),
        "bids": [enrich_bid_for_tab(bid, directories=directories) for bid in visible_bids],
        "totalBidsInCatalog": total_catalog,
        "directory": directories,
    }


def _resolve_tab_html_file(tab_dir: str) -> Optional[str]:
    """Prefer built React bundle (dist/index.html), falling back to Vite entry (index.html)."""
    candidates = (
        os.path.join(tab_dir, "dist", "index.html"),
        os.path.join(tab_dir, "index.html"),
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _sso_error_response(exc: Exception, config: Config, status_code: int) -> JSONResponse:
    """Build structured JSON error response without exposing internal stack traces."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": str(exc),
            "requiresAuth": True,
            "ssoMode": config.SSO_MODE,
            "useMockSso": config.is_mock_sso,
        },
    )


def _access_denied_response(exc: Exception, config: Config) -> JSONResponse:
    """Return 403 Forbidden when an unlisted user tries to open the app."""
    return JSONResponse(
        status_code=403,
        content={
            "error": str(exc),
            "accessDenied": True,
            "requiresAuth": False,
            "ssoMode": config.SSO_MODE,
            "useMockSso": config.is_mock_sso,
        },
    )


async def _run_intake_mutation(
    request: Request,
    persona: Optional[str],
    sso_service: SSOService,
    config: Config,
    mutation_fn: Callable[[UserProfile, Dict[str, Any]], Dict[str, Any]],
) -> JSONResponse:
    """Execute a Circle-isolated POST mutation against intake card state."""
    token = extract_http_sso_token(request)
    user_hint = extract_http_user_hint(request)
    body = await request.json()
    payload_dict = body if isinstance(body, dict) else {}
    req_persona = persona or payload_dict.get("persona")
    auto_directory_mode = (
        config.is_mock_sso and (config.DEFAULT_MOCK_USER_ID or "auto").strip().lower() == "auto"
    )
    requested_persona = (
        None
        if auto_directory_mode
        else (
            req_persona.strip()
            if (config.is_mock_sso and isinstance(req_persona, str) and req_persona.strip())
            else None
        )
    )
    effective_hint = None if requested_persona else (user_hint if config.is_mock_sso else None)
    try:
        profile = sso_service.resolve_user_profile(
            user_assertion=token,
            mock_user_id=requested_persona or config.DEFAULT_MOCK_USER_ID,
            user_hint=effective_hint,
        )
        result = mutation_fn(profile, payload_dict)
        refreshed = build_bids_payload(
            sso_service,
            config,
            sso_token=token,
            persona=req_persona,
            user_hint=user_hint,
        )
        return JSONResponse(content={**refreshed, "actionMessage": result["message"]})
    except SSOAuthenticationError as exc:
        return _sso_error_response(exc, config, status_code=401)
    except SSOConfigurationError as exc:
        return _sso_error_response(exc, config, status_code=503)
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"error": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


def register_tab_routes(app: Any, sso_service: SSOService, config: Config) -> None:
    """Mount the Teams Tab frontend, S0-YK-04 SSO APIs, and S0-YK-05 Intake APIs."""
    adapter = getattr(getattr(app, "server", None), "adapter", None)
    fastapi_app = getattr(adapter, "app", None)
    if fastapi_app is None:
        return

    karthik_dir = os.path.join(os.path.dirname(__file__), "karthik_api")
    if karthik_dir not in sys.path:
        sys.path.insert(0, karthik_dir)
    try:
        from karthik_api.main import api_router as karthik_api_router
        fastapi_app.include_router(karthik_api_router)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Could not include karthik_api_router: %s", exc)

    tab_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tab")
    )
    dist_assets_dir = os.path.join(tab_dir, "dist", "assets")

    if os.path.isdir(dist_assets_dir):
        fastapi_app.mount(
            "/assets",
            StaticFiles(directory=dist_assets_dir),
            name="tab-dist-assets",
        )
    if os.path.isdir(tab_dir) and hasattr(app, "tab"):
        serve_dir = os.path.join(tab_dir, "dist")
        app.tab("workspace", serve_dir if os.path.isdir(serve_dir) else tab_dir)

    @fastapi_app.get("/")
    @fastapi_app.get("/tab")
    @fastapi_app.get("/index.html")
    async def serve_tab_index() -> Any:
        index_path = _resolve_tab_html_file(tab_dir)
        if not index_path:
            return JSONResponse(
                status_code=404,
                content={"error": "Teams Tab entrypoint not found."},
            )
        return FileResponse(
            index_path,
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    @fastapi_app.get("/api/sso/me")
    async def get_sso_session(
        request: Request,
        persona: Optional[str] = None,
    ) -> JSONResponse:
        token = extract_http_sso_token(request)
        user_hint = extract_http_user_hint(request)
        try:
            payload = build_bids_payload(
                sso_service, config, sso_token=token, persona=persona, user_hint=user_hint
            )
            return JSONResponse(
                content={
                    "user": payload["user"],
                    "availablePersonas": payload["availablePersonas"],
                    "circle": payload["circle"],
                    "tabCircleCode": payload["tabCircleCode"],
                    "ssoMode": config.SSO_MODE,
                    "useMockSso": config.is_mock_sso,
                }
            )
        except PermissionError as exc:
            return _access_denied_response(exc, config)
        except SSOAuthenticationError as exc:
            return _sso_error_response(exc, config, status_code=401)
        except SSOConfigurationError as exc:
            return _sso_error_response(exc, config, status_code=503)

    @fastapi_app.get("/api/bids")
    async def get_circle_bids(
        request: Request,
        persona: Optional[str] = None,
    ) -> JSONResponse:
        token = extract_http_sso_token(request)
        user_hint = extract_http_user_hint(request)
        try:
            payload = build_bids_payload(
                sso_service, config, sso_token=token, persona=persona, user_hint=user_hint
            )
            return JSONResponse(content=payload)
        except PermissionError as exc:
            return _access_denied_response(exc, config)
        except SSOAuthenticationError as exc:
            return _sso_error_response(exc, config, status_code=401)
        except SSOConfigurationError as exc:
            return _sso_error_response(exc, config, status_code=503)

    @fastapi_app.post("/api/intake/assign-owner")
    async def api_assign_bid_owner(
        request: Request,
        persona: Optional[str] = None,
    ) -> JSONResponse:
        return await _run_intake_mutation(
            request,
            persona,
            sso_service,
            config,
            lambda profile, body: assign_intake_bid_owner(
                rfp_id=str(body.get("rfpId", "")),
                bid_owner=str(body.get("bidOwner", "")),
                user_circle=profile.circle,
            ),
        )

    @fastapi_app.post("/api/intake/confirm-team")
    async def api_confirm_bid_team(
        request: Request,
        persona: Optional[str] = None,
    ) -> JSONResponse:
        return await _run_intake_mutation(
            request,
            persona,
            sso_service,
            config,
            lambda profile, body: confirm_intake_team(
                rfp_id=str(body.get("rfpId", "")),
                user_circle=profile.circle,
            ),
        )

    @fastapi_app.get("/api/db/status")
    async def get_db_status() -> JSONResponse:
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
        
        try:
            from karthik_api.repo import get_sql_connection
            conn = get_sql_connection()
            if not conn:
                return JSONResponse(
                    content={
                        "connected": False,
                        "server": server,
                        "database": database,
                        "user": user,
                        "error": "Failed to connect to Azure SQL Server (check firewall or credentials).",
                    }
                )
            cursor = conn.cursor()
            cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
            tables = [r[0] for r in cursor.fetchall()]
            
            table_stats = {}
            for t in ["Opportunity", "Document", "Requirement", "Gap", "ActionItem", "DraftSection", "StageHistory", "AuditLog"]:
                if t in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
                        count = cursor.fetchone()[0]
                        table_stats[t] = {"exists": True, "rowCount": count}
                    except Exception as e:
                        table_stats[t] = {"exists": True, "error": str(e)}
                else:
                    table_stats[t] = {"exists": False}
                    
            conn.close()
            return JSONResponse(
                content={
                    "connected": True,
                    "server": server,
                    "database": database,
                    "user": user,
                    "schemaTables": table_stats,
                }
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={
                    "connected": False,
                    "server": server,
                    "database": database,
                    "error": str(exc),
                }
            )

    @fastapi_app.get("/api/directories")
    async def get_sharepoint_directories() -> JSONResponse:
        return JSONResponse(content=load_sharepoint_directories(config))

    @fastapi_app.post("/api/coe/match")
    async def api_match_coe_rules(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            body = {}
        payload = body if isinstance(body, dict) else {}
        rfp_text = str(payload.get("rfpText", ""))
        circle_filter = payload.get("circleFilter")
        directories = load_sharepoint_directories(config)
        matches = match_coes_from_rfp_text(
            rfp_text,
            directories,
            circle_filter=str(circle_filter) if circle_filter else None,
        )
        return JSONResponse(
            content={
                "source": directories["source"],
                "matches": matches,
                "coeDirectory": directories["coeDirectory"],
            }
        )
