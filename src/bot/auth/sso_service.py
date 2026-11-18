"""SSO and On-Behalf-Of (OBO) identity resolution with config-driven Mock/Entra switch."""
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

from azure.identity import OnBehalfOfCredential

from auth.circle_mapper import resolve_circle
from auth.directory_service import (
    detect_local_directory_user,
    load_sharepoint_directories,
    resolve_coe_by_circle,
    resolve_directory_user,
)
from config import Config

GRAPH_ME_ENDPOINT = (
    "https://graph.microsoft.com/v1.0/me"
    "?$select=id,displayName,mail,userPrincipalName,department,jobTitle"
)
GRAPH_USER_READ_SCOPE = "https://graph.microsoft.com/User.Read"
MOCK_PROFILES_PATH = Path(__file__).parent / "mock_profiles.json"


def load_mock_profiles(profiles_path: Path = MOCK_PROFILES_PATH) -> Dict[str, Any]:
    """Load synthetic mock user profiles and persona aliases from JSON."""
    if not profiles_path.exists():
        raise FileNotFoundError(f"Mock profiles JSON not found at {profiles_path}")
    with open(profiles_path, "r", encoding="utf-8") as f:
        return json.load(f)


_MOCK_DATA = load_mock_profiles()
MOCK_PROFILES: Dict[str, Dict[str, str]] = dict(_MOCK_DATA["profiles"])
MOCK_PERSONA_ALIASES: Dict[str, str] = {
    k.strip().lower(): v for k, v in _MOCK_DATA["persona_aliases"].items()
}


class SSOConfigurationError(RuntimeError):
    """Raised when real Entra SSO is enabled without required App Registration settings."""


class SSOAuthenticationError(RuntimeError):
    """Raised when Teams SSO token exchange or Graph profile lookup fails."""


@dataclass(frozen=True)
class UserProfile:
    """Resolved pre-sales user identity and assigned Circle."""

    user_id: str
    display_name: str
    email: str
    department: str
    job_title: str
    circle: str
    auth_source: str  # "directory_auto", "directory_user", "mock_profile", or "entra_obo"
    circle_id: str = ""
    coe_email_id: str = ""


def resolve_mock_key(identifier: Optional[str], fallback_key: str = "presales-fsi-01") -> str:
    """Resolve a user ID or Circle alias to a canonical key in MOCK_PROFILES."""
    if not identifier:
        return fallback_key
    normalized = identifier.strip().lower()
    if normalized in MOCK_PROFILES:
        return normalized
    if normalized in MOCK_PERSONA_ALIASES:
        return MOCK_PERSONA_ALIASES[normalized]
    return fallback_key


def _fetch_graph_me(access_token: str) -> Dict[str, Any]:
    """Fetch user profile from Microsoft Graph /me using an OBO access token."""
    req = urllib_request.Request(
        GRAPH_ME_ENDPOINT,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload)
    except (urllib_error.HTTPError, urllib_error.URLError, json.JSONDecodeError) as exc:
        raise SSOAuthenticationError(f"Failed to query Microsoft Graph /me: {exc}") from exc


class SSOService:
    """Resolves pre-sales user identity and Circle via SharePoint directory, Mock profile, or Entra ID OBO."""

    def __init__(
        self,
        config: Optional[Config] = None,
        graph_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
        credential_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.config = config or Config()
        self._graph_fetcher = graph_fetcher or _fetch_graph_me
        self._credential_factory = credential_factory or OnBehalfOfCredential

    def resolve_user_profile(
        self,
        user_assertion: Optional[str] = None,
        mock_user_id: Optional[str] = None,
        user_hint: Optional[str] = None,
    ) -> UserProfile:
        """Resolve user profile using config-selected strategy (Directory/Mock vs real Entra OBO)."""
        if self.config.is_mock_sso:
            return self._resolve_mock_profile(mock_user_id, user_hint=user_hint)
        return self._resolve_entra_obo_profile(user_assertion)

    def _build_directory_profile(
        self,
        entry: Dict[str, str],
        directories: Dict[str, Any],
        auth_source: str,
    ) -> UserProfile:
        """Build a UserProfile strictly from User_Directory and COE_Directory records."""
        raw_circle = entry.get("circleName", "").strip()
        coe = resolve_coe_by_circle(raw_circle, directories)
        circle = (coe.get("circleName") if coe else raw_circle) or "Unassigned"
        circle_id = coe.get("circleId", "") if coe else ""
        coe_name = coe.get("coeName", "") if coe else ""
        coe_email = coe.get("coeEmailId", "") if coe else ""
        email = entry.get("userEmail", "").strip()
        display_name = entry.get("userName", "").strip() or email
        return UserProfile(
            user_id=email or display_name,
            display_name=display_name,
            email=email,
            department=coe_name or circle,
            job_title=f"{circle} ({circle_id})" if circle_id else "SharePoint User Directory",
            circle=circle,
            auth_source=auth_source,
            circle_id=circle_id,
            coe_email_id=coe_email,
        )

    def _build_unassigned_profile(
        self,
        identifier: str,
        auth_source: str,
        email: str = "",
        display_name: str = "",
    ) -> UserProfile:
        """Fail closed to an Unassigned Circle so unmapped users cannot view any bids."""
        return UserProfile(
            user_id=identifier or "unassigned",
            display_name=display_name or identifier or "Unmapped User",
            email=email,
            department="Unassigned",
            job_title="Not found in User_Directory",
            circle="Unassigned",
            auth_source=auth_source,
            circle_id="",
            coe_email_id="",
        )

    def _resolve_mock_profile(
        self,
        mock_user_id: Optional[str] = None,
        user_hint: Optional[str] = None,
    ) -> UserProfile:
        """Resolve local user via SharePoint directory first, keeping legacy mock compatibility."""
        directories = load_sharepoint_directories(self.config)

        hint = (user_hint or "").strip()
        if hint:
            matched_hint = resolve_directory_user(hint, directories)
            if matched_hint is not None:
                return self._build_directory_profile(
                    matched_hint, directories, auth_source="directory_hint"
                )
            return self._build_unassigned_profile(
                hint,
                auth_source="directory_hint",
                email=hint if "@" in hint else "",
            )

        raw_id = (mock_user_id or self.config.DEFAULT_MOCK_USER_ID or "auto").strip()
        if raw_id.lower() == "auto":
            detected = detect_local_directory_user(
                directories,
                active_user_email=getattr(self.config, "ACTIVE_USER_EMAIL", ""),
            )
            if detected is not None:
                return self._build_directory_profile(
                    detected, directories, auth_source="directory_auto"
                )
            return self._build_unassigned_profile("auto", auth_source="directory_auto")

        matched_dir = resolve_directory_user(raw_id, directories)
        if matched_dir is not None:
            return self._build_directory_profile(
                matched_dir, directories, auth_source="directory_user"
            )

        normalized = raw_id.lower()
        if normalized in MOCK_PROFILES or normalized in MOCK_PERSONA_ALIASES:
            profile_key = resolve_mock_key(
                raw_id,
                fallback_key=self.config.DEFAULT_MOCK_USER_ID,
            )
            raw = MOCK_PROFILES.get(profile_key, MOCK_PROFILES["presales-fsi-01"])
            department = raw.get("department", "")
            circle = resolve_circle(department, default_circle=self.config.DEFAULT_CIRCLE)
            coe = resolve_coe_by_circle(circle, directories)
            return UserProfile(
                user_id=raw["user_id"],
                display_name=raw["display_name"],
                email=raw["email"],
                department=department,
                job_title=raw["job_title"],
                circle=circle,
                auth_source="mock_profile",
                circle_id=coe.get("circleId", "") if coe else "",
                coe_email_id=coe.get("coeEmailId", "") if coe else "",
            )

        return self._build_unassigned_profile(
            raw_id,
            auth_source="directory_user",
            email=raw_id if "@" in raw_id else "",
        )

    def _resolve_entra_obo_profile(self, user_assertion: Optional[str]) -> UserProfile:
        """Exchange Teams SSO token via OBO for Microsoft Graph /me profile and map via User_Directory."""
        self._validate_entra_config()
        if not user_assertion or not user_assertion.strip():
            raise SSOAuthenticationError(
                "Missing Teams SSO user token (user_assertion) for Entra OBO exchange."
            )

        try:
            credential = self._credential_factory(
                tenant_id=self.config.AAD_APP_TENANT_ID,
                client_id=self.config.AAD_APP_CLIENT_ID,
                client_secret=self.config.AAD_APP_CLIENT_SECRET,
                user_assertion=user_assertion,
            )
            graph_token = credential.get_token(GRAPH_USER_READ_SCOPE).token
        except Exception as exc:
            raise SSOAuthenticationError(f"Entra ID OBO token exchange failed: {exc}") from exc

        profile_data = self._graph_fetcher(graph_token)
        email = profile_data.get("mail") or profile_data.get("userPrincipalName") or ""
        display_name = profile_data.get("displayName", "Unknown User")
        department = (profile_data.get("department") or "").strip()

        directories = load_sharepoint_directories(self.config)
        matched_dir = resolve_directory_user(email, directories) or resolve_directory_user(
            display_name, directories
        )
        if matched_dir is not None:
            coe = resolve_coe_by_circle(matched_dir.get("circleName"), directories)
            circle = (coe.get("circleName") if coe else matched_dir.get("circleName", "")) or "Unassigned"
            circle_id = coe.get("circleId", "") if coe else ""
            coe_email = coe.get("coeEmailId", "") if coe else ""
            return UserProfile(
                user_id=profile_data.get("id") or email,
                display_name=display_name or matched_dir.get("userName", "Unknown User"),
                email=email or matched_dir.get("userEmail", ""),
                department=department or (coe.get("coeName", "") if coe else circle),
                job_title=profile_data.get("jobTitle") or f"{circle} ({circle_id})".strip(),
                circle=circle,
                auth_source="entra_obo",
                circle_id=circle_id,
                coe_email_id=coe_email,
            )

        if department:
            circle = resolve_circle(department, default_circle="Unassigned")
            coe = resolve_coe_by_circle(circle, directories)
            return UserProfile(
                user_id=profile_data.get("id", ""),
                display_name=display_name,
                email=email,
                department=department,
                job_title=profile_data.get("jobTitle") or "",
                circle=circle,
                auth_source="entra_obo",
                circle_id=coe.get("circleId", "") if coe else "",
                coe_email_id=coe.get("coeEmailId", "") if coe else "",
            )

        return UserProfile(
            user_id=profile_data.get("id", ""),
            display_name=display_name,
            email=email,
            department="",
            job_title=profile_data.get("jobTitle") or "",
            circle="Unassigned",
            auth_source="entra_obo",
            circle_id="",
            coe_email_id="",
        )

    def _validate_entra_config(self) -> None:
        """Verify required Entra App Registration credentials (from S0-AM-03) are present."""
        missing = []
        if not self.config.AAD_APP_CLIENT_ID:
            missing.append("AAD_APP_CLIENT_ID")
        if not self.config.AAD_APP_TENANT_ID:
            missing.append("AAD_APP_TENANT_ID")
        if not self.config.AAD_APP_CLIENT_SECRET:
            missing.append("AAD_APP_CLIENT_SECRET")

        if missing:
            raise SSOConfigurationError(
                f"Real Entra SSO requires {', '.join(missing)} "
                "(provisioned by S0-AM-03 / IT #13)."
            )
