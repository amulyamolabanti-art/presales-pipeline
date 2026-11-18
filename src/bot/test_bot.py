"""Unit tests for bot config, Adaptive Cards (S0-YK-05), SSO/Circle isolation & Tab API (S0-YK-04)."""
import asyncio
import json
import os
import sys
from unittest.mock import MagicMock

from fastapi import FastAPI
import pytest
from starlette.requests import Request

# Ensure src/bot is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app import INTAKE_CARD_PATH, load_intake_card  # noqa: E402
from auth import (  # noqa: E402
    CIRCLE_ENTERPRISE,
    CIRCLE_FINANCIAL_SERVICES,
    CIRCLE_HEALTHCARE,
    CIRCLE_MAPPING_PATH,
    CIRCLE_RETAIL,
    CIRCLE_TO_TAB_CODE,
    DEPARTMENT_TO_CIRCLE_MAP,
    MOCK_PERSONA_ALIASES,
    MOCK_PROFILES,
    MOCK_PROFILES_PATH,
    SAMPLE_BIDS,
    SSOAuthenticationError,
    SSOConfigurationError,
    SSOService,
    filter_bids_for_circle,
    load_circle_mapping,
    load_mock_profiles,
    resolve_circle,
)
from cards.rfp_catalog import (  # noqa: E402
    SAMPLE_RFPS,
    create_intake_card,
    create_rfp_selector_card,
    get_rfp_by_query,
)
from config import Config  # noqa: E402
from tab_api import (  # noqa: E402
    assign_intake_bid_owner,
    build_bids_payload,
    confirm_intake_team,
    register_tab_routes,
    reset_intake_states,
)


def _make_fake_request(headers=None, body=None):
    """Build a lightweight Starlette Request without external httpx test client."""
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in (headers or {}).items()
    ]
    req = Request({"type": "http", "headers": raw_headers})
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")

        async def _json():
            return json.loads(encoded.decode("utf-8"))

        req.json = _json  # type: ignore[method-assign]
    return req


def _find_route_endpoint(fastapi_app: FastAPI, path: str):
    """Locate a registered FastAPI route endpoint callable by URL path."""
    for route in fastapi_app.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(f"Route {path} not registered")


def test_bot_config_defaults():
    """Verify bot and SSO configuration attributes exist."""
    config = Config()
    assert hasattr(config, "APP_ID")
    assert hasattr(config, "APP_PASSWORD")
    assert hasattr(config, "APP_TYPE")
    assert hasattr(config, "APP_TENANTID")
    assert hasattr(config, "SSO_MODE")
    assert hasattr(config, "USE_MOCK_SSO")
    assert hasattr(config, "AAD_APP_CLIENT_ID")
    assert hasattr(config, "AAD_APP_TENANT_ID")


def test_bot_app_structure():
    """Verify S0-YK-04 and S0-YK-05 handlers are defined on the unified app."""
    import app
    assert hasattr(app, "app")
    assert hasattr(app, "handle_greeting")
    assert hasattr(app, "handle_whoami")
    assert hasattr(app, "handle_my_bids")
    assert hasattr(app, "handle_persona_switch")
    assert hasattr(app, "handle_intake_command")
    assert hasattr(app, "handle_message")
    assert hasattr(app, "load_intake_card")


def test_rfp_catalog_has_all_repository_clients():
    """Verify catalog covers all 3 repository sample files in samples/rfp/."""
    assert "harborline" in SAMPLE_RFPS
    assert "cedarbrook" in SAMPLE_RFPS
    assert "velora" in SAMPLE_RFPS

    assert get_rfp_by_query("1")["client"] == "Harborline Mutual Insurance Company"
    assert get_rfp_by_query("2")["client"] == "Cedarbrook Health System"
    assert get_rfp_by_query("3")["client"] == "Velora Retail Group plc"
    assert get_rfp_by_query("cedarbrook")["key"] == "cedarbrook"
    assert get_rfp_by_query("velora")["key"] == "velora"


def test_all_client_cards_render_with_acceptance_criteria():
    """Verify every client Adaptive Card has required metadata and action buttons."""
    for _, rfp in SAMPLE_RFPS.items():
        card = create_intake_card(rfp)
        assert card.type == "AdaptiveCard"
        assert card.version == "1.5"

        raw = card.model_dump()
        card_str = json.dumps(raw)

        assert rfp["client"] in card_str
        assert rfp["rfp_id"] in card_str
        assert rfp["circle"] in card_str
        assert "Suggested Bid Team" in card_str
        assert "Pending Pre-Sales Confirmation" in card_str

        actions = raw.get("actions", [])
        action_titles = [a.get("title") for a in actions]
        assert "Assign bid owner" in action_titles
        assert "Confirm team" in action_titles


def test_rfp_selector_hub_card():
    """Verify the Hub card offers buttons for all 3 clients."""
    hub = create_rfp_selector_card()
    assert hub.type == "AdaptiveCard"
    raw = hub.model_dump()
    actions = raw.get("actions", [])
    targets = [a.get("data", {}).get("target") for a in actions]
    assert "harborline" in targets
    assert "cedarbrook" in targets
    assert "velora" in targets


def test_default_intake_card_json():
    """Verify intake_card.json exists and loads cleanly."""
    assert INTAKE_CARD_PATH.exists()
    card = load_intake_card()
    assert card.type == "AdaptiveCard"
    assert card.version == "1.5"


@pytest.mark.parametrize(
    "department,expected_circle",
    [
        ("Financial Services", CIRCLE_FINANCIAL_SERVICES),
        ("Financial Services & Insurance", CIRCLE_FINANCIAL_SERVICES),
        ("BFSI", CIRCLE_FINANCIAL_SERVICES),
        ("P&C Insurance", CIRCLE_FINANCIAL_SERVICES),
        ("Healthcare", CIRCLE_HEALTHCARE),
        ("Healthcare & Clinical Analytics", CIRCLE_HEALTHCARE),
        ("Life Sciences", CIRCLE_HEALTHCARE),
        ("Retail", CIRCLE_RETAIL),
        ("Retail & E-Commerce", CIRCLE_RETAIL),
        ("Enterprise", CIRCLE_ENTERPRISE),
        ("Cloud & Enterprise Architecture", CIRCLE_ENTERPRISE),
    ],
)
def test_department_to_circle_exact_mappings(department, expected_circle):
    """Verify known department names map to canonical Circles."""
    assert resolve_circle(department) == expected_circle


@pytest.mark.parametrize(
    "department,expected_circle",
    [
        ("  bfsi  ", CIRCLE_FINANCIAL_SERVICES),
        ("Global Banking & Wealth", CIRCLE_FINANCIAL_SERVICES),
        ("clinical informatics division", CIRCLE_HEALTHCARE),
        ("Consumer E-Commerce Ops", CIRCLE_RETAIL),
        ("Core Cloud Infrastructure", CIRCLE_ENTERPRISE),
    ],
)
def test_department_to_circle_case_whitespace_and_keywords(department, expected_circle):
    """Verify case-insensitive whitespace handling and keyword fallback rules."""
    assert resolve_circle(department) == expected_circle


@pytest.mark.parametrize("department", [None, "", "   ", "Facilities Management"])
def test_department_to_circle_fallback(department):
    """Verify missing or unknown departments fall back safely to Enterprise."""
    assert resolve_circle(department) == CIRCLE_ENTERPRISE


def test_filter_bids_for_circle_enforces_isolation():
    """Verify a pre-sales user only sees bids matching their assigned Circle."""
    fsi_bids = filter_bids_for_circle(list(SAMPLE_BIDS), CIRCLE_FINANCIAL_SERVICES)
    assert len(fsi_bids) == 1
    assert fsi_bids[0]["clientName"] == "Harborline Mutual Insurance"

    health_bids = filter_bids_for_circle(list(SAMPLE_BIDS), CIRCLE_HEALTHCARE)
    assert len(health_bids) == 1
    assert health_bids[0]["clientName"] == "Cedarbrook Health System"

    retail_bids = filter_bids_for_circle(list(SAMPLE_BIDS), CIRCLE_RETAIL)
    assert len(retail_bids) == 1
    assert retail_bids[0]["clientName"] == "Velora Retail Group plc"

    assert filter_bids_for_circle(list(SAMPLE_BIDS), None) == []


def test_sso_service_resolves_mock_profiles():
    """Verify Mock SSO resolves mock user profile and Circle properly."""
    cfg = Config()
    cfg.SSO_MODE = "mock"
    cfg.USE_MOCK_SSO = True

    service = SSOService(config=cfg)

    fsi_user = service.resolve_user_profile(mock_user_id="presales-fsi-01")
    assert fsi_user.auth_source == "mock_profile"
    assert fsi_user.circle == CIRCLE_FINANCIAL_SERVICES

    health_user = service.resolve_user_profile(mock_user_id="healthcare")
    assert health_user.auth_source == "mock_profile"
    assert health_user.display_name == "Elena Rostova"
    assert health_user.circle == CIRCLE_HEALTHCARE


def test_real_sso_switch_is_a_config_change():
    """Verify toggling config switches SSOService cleanly from Mock to Entra OBO."""
    cfg = Config()
    cfg.SSO_MODE = "entra"
    cfg.USE_MOCK_SSO = False
    cfg.AAD_APP_CLIENT_ID = ""
    cfg.AAD_APP_TENANT_ID = ""
    cfg.AAD_APP_CLIENT_SECRET = ""

    service = SSOService(config=cfg)
    assert cfg.is_mock_sso is False

    with pytest.raises(SSOConfigurationError):
        service.resolve_user_profile(user_assertion="dummy-teams-token")

    cfg.AAD_APP_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
    cfg.AAD_APP_TENANT_ID = "00000000-0000-0000-0000-000000000002"
    cfg.AAD_APP_CLIENT_SECRET = "dummy-secret-from-keyvault"

    with pytest.raises(SSOAuthenticationError):
        service.resolve_user_profile(user_assertion=None)

    mock_cred = MagicMock()
    mock_cred.get_token.return_value = MagicMock(token="graph-obo-access-token")
    mock_cred_factory = MagicMock(return_value=mock_cred)
    mock_graph_fetcher = MagicMock(
        return_value={
            "id": "entra-user-123",
            "displayName": "Maya Lin",
            "mail": "maya.lin@presales.example",
            "department": "Healthcare & Life Sciences",
            "jobTitle": "Senior Pre-Sales Architect",
        }
    )

    real_service = SSOService(
        config=cfg,
        graph_fetcher=mock_graph_fetcher,
        credential_factory=mock_cred_factory,
    )
    profile = real_service.resolve_user_profile(user_assertion="teams-sso-jwt-assertion")

    assert profile.auth_source == "entra_obo"
    assert profile.display_name == "Maya Lin"
    assert profile.email == "maya.lin@presales.example"
    assert profile.circle == CIRCLE_HEALTHCARE
    mock_cred_factory.assert_called_once()
    mock_graph_fetcher.assert_called_once_with("graph-obo-access-token")


def test_combined_tab_api_sso_and_intake_actions():
    """Verify Tab API combines Circle isolation (S0-YK-04) & Intake Card (S0-YK-05)."""
    reset_intake_states()
    cfg = Config()
    cfg.SSO_MODE = "mock"
    cfg.USE_MOCK_SSO = True
    cfg.DEFAULT_MOCK_USER_ID = "presales-fsi-01"
    service = SSOService(config=cfg)

    fsi_payload = build_bids_payload(service, cfg)
    assert fsi_payload["circle"] == CIRCLE_FINANCIAL_SERVICES
    assert len(fsi_payload["bids"]) == 1
    fsi_bid = fsi_payload["bids"][0]
    assert fsi_bid["rfpId"] == "HMI-IT-2026-114"
    assert len(fsi_bid["suggestedTeam"]) == 3
    assert "Pending Pre-Sales Confirmation" in fsi_bid["intakeStatus"]

    # Assign bid owner and confirm team inside same Circle
    assign_result = assign_intake_bid_owner(
        "HMI-IT-2026-114", "Yasaswini K (Bid Lead)", CIRCLE_FINANCIAL_SERVICES
    )
    assert assign_result["bid"]["bidOwner"] == "Yasaswini K (Bid Lead)"
    confirm_result = confirm_intake_team("HMI-IT-2026-114", CIRCLE_FINANCIAL_SERVICES)
    assert confirm_result["bid"]["teamConfirmed"] is True
    assert "Team Confirmed" in confirm_result["bid"]["intakeStatus"]

    # Cross-Circle mutation must be blocked (S0-YK-04 isolation on S0-YK-05 actions)
    with pytest.raises(PermissionError):
        confirm_intake_team("CHS-RFI-2026-042", CIRCLE_FINANCIAL_SERVICES)

    # Verify HTTP endpoints via FastAPI route registration
    fastapi_app = FastAPI()
    dummy_app = MagicMock()
    dummy_app.server.adapter.app = fastapi_app
    register_tab_routes(dummy_app, service, cfg)

    index_resp = asyncio.run(_find_route_endpoint(fastapi_app, "/")())
    assert "text/html" in index_resp.media_type

    reset_intake_states()
    assign_endpoint = _find_route_endpoint(fastapi_app, "/api/intake/assign-owner")
    assign_resp = asyncio.run(
        assign_endpoint(
            _make_fake_request(
                body={"rfpId": "CHS-RFI-2026-042", "bidOwner": "Elena Rostova"}
            ),
            persona="healthcare",
        )
    )
    assert assign_resp.status_code == 200
    assign_json = json.loads(assign_resp.body.decode("utf-8"))
    assert assign_json["bids"][0]["bidOwner"] == "Elena Rostova"
    reset_intake_states()


def test_tab_api_enforces_entra_sso_fail_closed():
    """Verify Entra SSO rejects unauthenticated tab requests without leaking bids."""
    cfg = Config()
    cfg.SSO_MODE = "entra"
    cfg.USE_MOCK_SSO = False
    cfg.AAD_APP_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
    cfg.AAD_APP_TENANT_ID = "00000000-0000-0000-0000-000000000002"
    cfg.AAD_APP_CLIENT_SECRET = "dummy-secret"

    mock_cred = MagicMock()
    mock_cred.get_token.return_value = MagicMock(token="graph-token")
    mock_graph = MagicMock(
        return_value={
            "id": "entra-user-456",
            "displayName": "Nadia Patel",
            "mail": "nadia.patel@presales.example",
            "department": "Retail & E-Commerce",
            "jobTitle": "Retail Bid Lead",
        }
    )
    service = SSOService(
        config=cfg,
        graph_fetcher=mock_graph,
        credential_factory=MagicMock(return_value=mock_cred),
    )

    fastapi_app = FastAPI()
    dummy_app = MagicMock()
    dummy_app.server.adapter.app = fastapi_app
    register_tab_routes(dummy_app, service, cfg)

    bids_endpoint = _find_route_endpoint(fastapi_app, "/api/bids")
    unauth_resp = asyncio.run(bids_endpoint(_make_fake_request(), persona="healthcare"))
    assert unauth_resp.status_code == 401
    unauth_data = json.loads(unauth_resp.body.decode("utf-8"))
    assert unauth_data["requiresAuth"] is True
    assert "bids" not in unauth_data

    auth_req = _make_fake_request({"Authorization": "Bearer valid-teams-jwt"})
    auth_resp = asyncio.run(bids_endpoint(auth_req, persona="healthcare"))
    assert auth_resp.status_code == 200
    auth_data = json.loads(auth_resp.body.decode("utf-8"))
    assert auth_data["circle"] == CIRCLE_RETAIL
    assert auth_data["user"]["authSource"] == "entra_obo"
    assert auth_data["availablePersonas"] == []
    assert len(auth_data["bids"]) == 1
    assert auth_data["bids"][0]["clientName"] == "Velora Retail Group plc"


def test_mapping_loaded_from_json_files():
    """Verify Circle mapping tables and mock SSO profiles are loaded cleanly from JSON files."""
    assert CIRCLE_MAPPING_PATH.name == "circle_mapping.json"
    assert CIRCLE_MAPPING_PATH.is_file()
    assert MOCK_PROFILES_PATH.name == "mock_profiles.json"
    assert MOCK_PROFILES_PATH.is_file()

    circle_cfg = load_circle_mapping()
    assert circle_cfg["department_to_circle"] == DEPARTMENT_TO_CIRCLE_MAP
    assert circle_cfg["circle_to_tab_code"] == CIRCLE_TO_TAB_CODE

    profile_cfg = load_mock_profiles()
    assert profile_cfg["profiles"] == MOCK_PROFILES
    assert profile_cfg["persona_aliases"] == MOCK_PERSONA_ALIASES

    custom_json_mapping = {
        "department_to_circle": {"custom fintech ops": CIRCLE_FINANCIAL_SERVICES},
        "keyword_rules": [],
    }
    assert (
        resolve_circle("Custom Fintech Ops", mapping=custom_json_mapping)
        == CIRCLE_FINANCIAL_SERVICES
    )


def test_sharepoint_directory_loading_and_step2_coe_rules(tmp_path):
    """Verify SharePoint-style COE/User directory exports load and Step 2 COE rules resolve emails."""
    from pathlib import Path
    from auth import (
        FALLBACK_COE_MAPPING_PATH,
        FALLBACK_USER_MAPPING_PATH,
        load_sharepoint_directories,
        match_coes_from_rfp_text,
        resolve_directory_user,
    )

    coe_export = tmp_path / "COE_Directory.json"
    user_export = tmp_path / "User_Directory.csv"

    coe_export.write_text(
        json.dumps([
            {
                "Title": "Testing",
                "CircleID": "CIR-TST-01",
                "COEName": "Quality Engineering & Testing COE",
                "COEEmailID": "qe-coe@presales.example",
            },
            {
                "Title": "Platform",
                "CircleID": "CIR-PLT-02",
                "COEName": "Cloud & Platform Engineering COE",
                "COEEmailID": "platform-coe@presales.example",
            },
            {
                "Title": "Data & Insights",
                "CircleID": "CIR-DNI-03",
                "COEName": "Data & Insights / AI COE",
                "COEEmailID": "data-insights-coe@presales.example",
            },
            {
                "Title": "Salesforce",
                "CircleID": "CIR-SFDC-04",
                "COEName": "Salesforce & Enterprise Apps COE",
                "COEEmailID": "salesforce-coe@presales.example",
            },
        ]),
        encoding="utf-8",
    )
    user_export.write_text(
        "Title,UserEmail,CircleName\n"
        "Alex Morgan,alex.morgan@presales.example,Platform\n"
        "Priya Sharma,priya.sharma@presales.example,D&I\n",
        encoding="utf-8",
    )

    cfg = Config()
    directories = load_sharepoint_directories(cfg, coe_path=Path(coe_export), user_path=Path(user_export))
    assert directories["source"] == "sharepoint_local"
    assert len(directories["coeDirectory"]) == 4
    assert len(directories["userDirectory"]) == 2

    user = resolve_directory_user("priya.sharma@presales.example", directories)
    assert user is not None
    assert user["circleName"] == "Data & Insights"
    assert user["circleId"] == "CIR-DNI-03"

    # Verify all 7 Step 2 strict COE rules trigger and resolve directory emails
    rfp_excerpt = (
        "Must migrate S3 and Redshift on AWS, support GCP BigQuery, "
        "Microsoft Fabric / Azure ADF, Snowflake, Databricks, "
        "Dimensional Modelling star schema, and Power BI reporting."
    )
    matches = match_coes_from_rfp_text(rfp_excerpt, directories)
    matched_rules = {m["ruleCoeName"]: m for m in matches}
    assert set(matched_rules.keys()) == {
        "AWS COE",
        "GCP COE",
        "Azure COE",
        "Snowflake COE",
        "Databricks COE",
        "Data Modelling COE",
        "Reporting COE",
    }
    assert matched_rules["AWS COE"]["coeEmailId"] == "platform-coe@presales.example"
    assert matched_rules["Snowflake COE"]["coeEmailId"] == "data-insights-coe@presales.example"

    # Verify Git-tracked sanitized fallback JSON files also load cleanly
    fallback_dirs = load_sharepoint_directories(
        cfg,
        coe_path=FALLBACK_COE_MAPPING_PATH,
        user_path=FALLBACK_USER_MAPPING_PATH,
    )
    assert fallback_dirs["source"] == "json_fallback"
    assert len(fallback_dirs["coeDirectory"]) == 4
    assert len(fallback_dirs["userDirectory"]) == 4


def test_tab_api_directories_and_coe_match_routes():
    """Verify /api/directories and /api/coe/match routes return directory data and COE matches."""
    app_mock = MagicMock()
    app_mock.server.adapter.app = FastAPI()
    cfg = Config()
    cfg.SSO_MODE = "mock"
    cfg.USE_MOCK_SSO = True

    register_tab_routes(app_mock, SSOService(config=cfg), cfg)

    dir_ep = _find_route_endpoint(app_mock.server.adapter.app, "/api/directories")
    dir_resp = asyncio.run(dir_ep())
    assert dir_resp.status_code == 200
    dir_body = json.loads(dir_resp.body.decode("utf-8"))
    assert len(dir_body["coeDirectory"]) == 4
    assert len(dir_body["userDirectory"]) == 4

    match_ep = _find_route_endpoint(app_mock.server.adapter.app, "/api/coe/match")
    match_req = _make_fake_request(body={"rfpText": "Build Snowflake and AWS S3 pipelines with BI Reporting."})
    match_resp = asyncio.run(match_ep(match_req))
    assert match_resp.status_code == 200
    match_body = json.loads(match_resp.body.decode("utf-8"))
    matched_names = {m["ruleCoeName"] for m in match_body["matches"]}
    assert {"AWS COE", "Snowflake COE", "Reporting COE"} <= matched_names



def test_directory_auto_detection_and_dynamic_rfp_filtering(tmp_path, monkeypatch):
    """Verify MOCK_USER_ID=auto detects users solely via SharePoint directories and isolates RFPs."""
    from pathlib import Path

    coe_export = tmp_path / "COE_Directory.json"
    user_export = tmp_path / "User_Directory.json"
    coe_export.write_text(
        json.dumps(
            [
                {
                    "Title": "Testing",
                    "CircleID": "CIR-TST-01",
                    "COEName": "Quality Engineering & Testing COE",
                    "COEEmailID": "qe-coe@presales.example",
                },
                {
                    "Title": "Platform",
                    "CircleID": "CIR-PLT-02",
                    "COEName": "Cloud & Platform Engineering COE",
                    "COEEmailID": "platform-coe@presales.example",
                },
                {
                    "Title": "Data & Insights",
                    "CircleID": "CIR-DNI-03",
                    "COEName": "Data & Insights / AI COE",
                    "COEEmailID": "data-insights-coe@presales.example",
                },
                {
                    "Title": "Salesforce",
                    "CircleID": "CIR-SFDC-04",
                    "COEName": "Salesforce & Enterprise Apps COE",
                    "COEEmailID": "salesforce-coe@presales.example",
                },
            ]
        ),
        encoding="utf-8",
    )
    user_export.write_text(
        json.dumps(
            [
                {
                    "Title": "Jordan Lee",
                    "UserEmail": "jordan.lee@presales.example",
                    "CircleName": "Testing",
                },
                {
                    "Title": "Alex Morgan",
                    "UserEmail": "alex.morgan@presales.example",
                    "CircleName": "Platform",
                },
                {
                    "Title": "Priya Nair",
                    "UserEmail": "priya.nair@presales.example",
                    "CircleName": "Data & Insights",
                },
                {
                    "Title": "Elena Rostova",
                    "UserEmail": "elena.rostova@presales.example",
                    "CircleName": "Salesforce",
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("LOCAL_COE_DIRECTORY_PATH", str(coe_export))
    monkeypatch.setenv("LOCAL_USER_DIRECTORY_PATH", str(user_export))
    monkeypatch.setenv("ACTIVE_USER_EMAIL", "")
    monkeypatch.setenv("TEAMS_USER_EMAIL", "")
    monkeypatch.setenv("USERNAME", "alex.morgan")

    cfg = Config()
    cfg.SSO_MODE = "mock"
    cfg.USE_MOCK_SSO = True
    cfg.DEFAULT_MOCK_USER_ID = "auto"
    cfg.ACTIVE_USER_EMAIL = ""
    cfg.LOCAL_COE_DIRECTORY_PATH = str(Path(coe_export))
    cfg.LOCAL_USER_DIRECTORY_PATH = str(Path(user_export))
    svc = SSOService(config=cfg)

    # Auto-detects Alex Morgan -> Platform via local username matching User_Directory
    plt_payload = build_bids_payload(svc, cfg)
    assert plt_payload["user"]["displayName"] == "Alex Morgan"
    assert plt_payload["user"]["circle"] == "Platform"
    assert plt_payload["user"]["circleId"] == "CIR-PLT-02"
    assert plt_payload["user"]["coeEmailId"] == "platform-coe@presales.example"
    assert plt_payload["user"]["authSource"] == "directory_auto"
    assert [b["opportunityId"] for b in plt_payload["bids"]] == ["OPP-2026-PLT-01"]
    assert plt_payload["availablePersonas"] == []

    # Query ?persona impersonation cannot switch users in auto/directory mode
    no_impersonation = build_bids_payload(svc, cfg, persona="priya.nair@presales.example")
    assert no_impersonation["user"]["displayName"] == "Alex Morgan"
    assert [b["opportunityId"] for b in no_impersonation["bids"]] == ["OPP-2026-PLT-01"]

    # X-Teams-User-Hint overrides auto-detect to Priya Nair -> Data & Insights
    dni_payload = build_bids_payload(svc, cfg, user_hint="priya.nair@presales.example")
    assert dni_payload["user"]["displayName"] == "Priya Nair"
    assert dni_payload["circle"] == "Data & Insights"
    assert [b["opportunityId"] for b in dni_payload["bids"]] == ["OPP-2026-DNI-01"]

    # Dynamic edit to User_Directory.json immediately moves Alex Morgan -> Testing
    user_export.write_text(
        json.dumps(
            [
                {
                    "Title": "Alex Morgan",
                    "UserEmail": "alex.morgan@presales.example",
                    "CircleName": "Testing",
                },
                {
                    "Title": "Priya Nair",
                    "UserEmail": "priya.nair@presales.example",
                    "CircleName": "Data & Insights",
                },
            ]
        ),
        encoding="utf-8",
    )
    updated_payload = build_bids_payload(svc, cfg)
    assert updated_payload["circle"] == "Testing"
    assert updated_payload["user"]["circleId"] == "CIR-TST-01"
    assert [b["opportunityId"] for b in updated_payload["bids"]] == ["OPP-2026-TST-01"]

    # Unmapped Teams user and unlisted local OS user are strictly restricted (403 / PermissionError)
    with pytest.raises(PermissionError):
        build_bids_payload(svc, cfg, user_hint="stranger@outside.example")

    monkeypatch.setenv("USERNAME", "unlisted.person")
    with pytest.raises(PermissionError):
        build_bids_payload(svc, cfg)

    fastapi_app = FastAPI()
    dummy_app = MagicMock()
    dummy_app.server.adapter.app = fastapi_app
    register_tab_routes(dummy_app, svc, cfg)
    bids_ep = _find_route_endpoint(fastapi_app, "/api/bids")
    denied_resp = asyncio.run(bids_ep(_make_fake_request()))
    assert denied_resp.status_code == 403
    denied_body = json.loads(denied_resp.body.decode("utf-8"))
    assert denied_body["accessDenied"] is True
    assert "bids" not in denied_body


def test_entra_obo_matches_graph_user_against_user_directory(tmp_path):
    """Verify real Entra OBO resolves Graph /me email via User_Directory & fails closed when unmapped."""
    coe_export = tmp_path / "COE_Directory.json"
    user_export = tmp_path / "User_Directory.json"
    coe_export.write_text(
        json.dumps(
            [
                {
                    "Title": "Salesforce",
                    "CircleID": "CIR-SFDC-04",
                    "COEName": "Salesforce & Enterprise Apps COE",
                    "COEEmailID": "salesforce-coe@presales.example",
                }
            ]
        ),
        encoding="utf-8",
    )
    user_export.write_text(
        json.dumps(
            [
                {
                    "Title": "Elena Rostova",
                    "UserEmail": "elena.rostova@presales.example",
                    "CircleName": "Salesforce",
                }
            ]
        ),
        encoding="utf-8",
    )

    cfg = Config()
    cfg.SSO_MODE = "entra"
    cfg.USE_MOCK_SSO = False
    cfg.AAD_APP_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
    cfg.AAD_APP_TENANT_ID = "00000000-0000-0000-0000-000000000002"
    cfg.AAD_APP_CLIENT_SECRET = "synthetic-secret-for-unit-test"
    cfg.LOCAL_COE_DIRECTORY_PATH = str(coe_export)
    cfg.LOCAL_USER_DIRECTORY_PATH = str(user_export)

    class _FakeCred:
        def __init__(self, **_kwargs):
            pass

        def get_token(self, *_scopes):
            tok = MagicMock()
            tok.token = "graph-tok"
            return tok

    svc = SSOService(
        config=cfg,
        graph_fetcher=lambda _tok: {
            "id": "aad-oid-42",
            "displayName": "Elena Rostova",
            "mail": "elena.rostova@presales.example",
            "department": "",
        },
        credential_factory=_FakeCred,
    )
    payload = build_bids_payload(svc, cfg, sso_token="teams-jwt")
    assert payload["user"]["authSource"] == "entra_obo"
    assert payload["user"]["circle"] == "Salesforce"
    assert payload["user"]["circleId"] == "CIR-SFDC-04"
    assert [b["opportunityId"] for b in payload["bids"]] == ["OPP-2026-SFDC-01"]

    # Unmapped Entra user with empty department fails closed
    svc_unmapped = SSOService(
        config=cfg,
        graph_fetcher=lambda _tok: {
            "id": "aad-oid-99",
            "displayName": "External Guest",
            "mail": "guest@outside.example",
            "department": "",
        },
        credential_factory=_FakeCred,
    )
    with pytest.raises(PermissionError):
        build_bids_payload(svc_unmapped, cfg, sso_token="teams-jwt")
