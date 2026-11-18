import os

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str, default: bool = True) -> bool:
    """Parse boolean environment variable values safely."""
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Bot and SSO Configuration."""

    APP_ID = os.environ.get("CLIENT_ID", "")
    APP_PASSWORD = os.environ.get("CLIENT_SECRET", "")
    APP_TYPE = os.environ.get("BOT_TYPE", "")
    APP_TENANTID = os.environ.get("TENANT_ID", "")

    # SSO / On-Behalf-Of (OBO) Configuration (S0-YK-04 / aligned with S0-AM-03)
    # Switching between mock profile and real Entra ID SSO requires only changing config/env vars.
    SSO_MODE = os.environ.get("SSO_MODE", "mock").strip().lower()
    USE_MOCK_SSO = _parse_bool(os.environ.get("USE_MOCK_SSO", "true"), default=True)

    AAD_APP_CLIENT_ID = os.environ.get("AAD_APP_CLIENT_ID", APP_ID)
    AAD_APP_CLIENT_SECRET = os.environ.get("AAD_APP_CLIENT_SECRET", APP_PASSWORD)
    AAD_APP_TENANT_ID = os.environ.get("AAD_APP_TENANT_ID", APP_TENANTID)
    AAD_APP_OAUTH_AUTHORITY_HOST = os.environ.get(
        "AAD_APP_OAUTH_AUTHORITY_HOST", "https://login.microsoftonline.com"
    )
    AAD_APP_ACCESS_AS_USER_SCOPE = os.environ.get(
        "AAD_APP_ACCESS_AS_USER_SCOPE", "access_as_user"
    )

    DEFAULT_MOCK_USER_ID = os.environ.get("MOCK_USER_ID", "auto")
    ACTIVE_USER_EMAIL = os.environ.get("ACTIVE_USER_EMAIL", "").strip()
    DEFAULT_CIRCLE = os.environ.get("DEFAULT_CIRCLE", "Enterprise")

    # Local SharePoint Directory export overrides (gitignored local_sharepoint_data/ by default)
    LOCAL_COE_DIRECTORY_PATH = os.environ.get("LOCAL_COE_DIRECTORY_PATH", "").strip()
    LOCAL_USER_DIRECTORY_PATH = os.environ.get("LOCAL_USER_DIRECTORY_PATH", "").strip()

    @property
    def is_mock_sso(self) -> bool:
        """Determine whether mock SSO should be used based on config."""
        if self.SSO_MODE == "entra":
            return False
        if self.SSO_MODE == "mock":
            return self.USE_MOCK_SSO
        return self.USE_MOCK_SSO
