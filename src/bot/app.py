import asyncio
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional

import os
import sys

# Dynamically resolve repository paths for Azure App Service, containers, and local dev
_BOT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BOT_DIR.parent.parent
for _p in (str(_BOT_DIR), str(_PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from azure.identity import ManagedIdentityCredential
from microsoft_teams.api import MessageActivity, TypingActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.cards import AdaptiveCard

from auth import (
    DIRECTORY_SAMPLE_BIDS,
    MOCK_PROFILES,
    SAMPLE_BIDS,
    SSOService,
    UserProfile,
    filter_bids_for_circle,
    load_sharepoint_directories,
    resolve_directory_user,
    resolve_mock_key,
)
from cards.rfp_catalog import (
    SAMPLE_RFPS,
    create_intake_card,
    create_rfp_selector_card,
    get_rfp_by_query,
)
from config import Config
from tab_api import (
    assign_intake_bid_owner,
    confirm_intake_team,
    register_tab_routes,
)

config = Config()
sso_service = SSOService(config=config)

# Per-conversation active mock persona override for Playground testing (Mock SSO mode)
_conversation_personas: Dict[str, str] = {}

CARDS_DIR = Path(__file__).parent / "cards"
INTAKE_CARD_PATH = CARDS_DIR / "intake_card.json"


def load_intake_card() -> AdaptiveCard:
    """Load default Harborline Intake Adaptive Card from JSON."""
    if not INTAKE_CARD_PATH.exists():
        raise FileNotFoundError(f"Card template not found at {INTAKE_CARD_PATH}")
    with open(INTAKE_CARD_PATH, "r", encoding="utf-8") as f:
        card_data = json.load(f)
    return AdaptiveCard.model_validate(card_data)


def create_token_factory():
    """Create Managed Identity token factory when bot uses UserAssignedMsi."""
    def get_token(scopes, tenant_id=None):
        credential = ManagedIdentityCredential(client_id=config.APP_ID)
        scopes_list = [scopes] if isinstance(scopes, str) else scopes
        token = credential.get_token(*scopes_list)
        return token.token
    return get_token


app = App(
    token=create_token_factory() if config.APP_TYPE == "UserAssignedMsi" else None,
    skip_auth=not config.APP_ID,
)
register_tab_routes(app, sso_service, config)

# Expose the underlying FastAPI ASGI application for Uvicorn
api = app.server.adapter.app
fastapi_app = app.server.adapter.app

# Dynamically enable App to be called directly by ASGI servers (Uvicorn / Gunicorn)
async def _app_asgi_call(self, scope, receive, send):
    return await self.server.adapter.app(scope, receive, send)

App.__call__ = _app_asgi_call


def _get_conversation_id(ctx: ActivityContext[MessageActivity]) -> str:
    """Safely extract conversation identifier from incoming activity."""
    conversation = getattr(ctx.activity, "conversation", None)
    return getattr(conversation, "id", "default") or "default"


def _extract_sso_token(ctx: ActivityContext[MessageActivity]) -> Optional[str]:
    """Extract SSO token from activity value payload if present."""
    value = getattr(ctx.activity, "value", None)
    if isinstance(value, dict):
        return value.get("token") or value.get("ssoToken")
    return None


def resolve_current_user(ctx: ActivityContext[MessageActivity]) -> UserProfile:
    """Resolve the active pre-sales user and Circle from SSO or directory/mock persona."""
    conv_id = _get_conversation_id(ctx)
    mock_user_id = _conversation_personas.get(conv_id, config.DEFAULT_MOCK_USER_ID)
    sso_token = _extract_sso_token(ctx)
    return sso_service.resolve_user_profile(
        user_assertion=sso_token,
        mock_user_id=mock_user_id,
    )


def _format_bids_summary(profile: UserProfile) -> str:
    """Format Circle-filtered bids message for the resolved user."""
    if profile.circle == "Unassigned":
        return "⛔ Access restricted: Only users listed in `User_Directory` can access Circle bids."
    all_bids = list(SAMPLE_BIDS) + list(DIRECTORY_SAMPLE_BIDS)
    bids = filter_bids_for_circle(all_bids, profile.circle)
    if not bids:
        return f"No active bids found for the **{profile.circle}** Circle."

    lines = [
        f"🎯 **Bids Visible for {profile.display_name} ({profile.circle} Circle)**\n"
    ]
    for bid in bids:
        lines.append(
            f"• **{bid['opportunityId']}** — {bid['clientName']} "
            f"(*{bid['bidTitle']}*, Due: {bid['dueDate']})"
        )
    lines.append(
        "\n*(Multi-bid isolation active: bids from other Circles are hidden)*"
    )
    return "\n".join(lines)


async def _handle_intake_card_action(
    ctx: ActivityContext[MessageActivity],
    value: Dict[str, Any],
) -> bool:
    """Process Adaptive Card submit actions from the S0-YK-05 Intake Card."""
    action = value.get("action")
    target = value.get("target")

    if action == "select_rfp" and target in SAMPLE_RFPS:
        await ctx.send(create_intake_card(SAMPLE_RFPS[target]))
        return True

    rfp_id = str(value.get("rfpId", "Unknown"))
    client = str(value.get("client", "Client"))
    circle = str(value.get("circle", "Circle"))

    if action == "assign_bid_owner":
        profile = resolve_current_user(ctx)
        try:
            assign_intake_bid_owner(rfp_id, profile.display_name, profile.circle)
        except (PermissionError, ValueError):
            pass
        await ctx.send(
            f"👤 **Action Received: Assign Bid Owner**\n\n"
            f"• **Client:** {client}\n"
            f"• **Opportunity ID:** `{rfp_id}`\n"
            f"• **Target Circle:** {circle}\n\n"
            "A presales owner reassignment request has been dispatched to the Circle Lead."
        )
        return True

    if action == "confirm_team":
        profile = resolve_current_user(ctx)
        try:
            confirm_intake_team(rfp_id, profile.circle)
        except (PermissionError, ValueError):
            pass
        await ctx.send(
            f"✅ **Success: Bid Team Confirmed!**\n\n"
            f"• **Client:** {client}\n"
            f"• **Opportunity ID:** `{rfp_id}`\n"
            f"• **Target Circle:** {circle}\n\n"
            "The proposed team has been approved. Proceeding to "
            "**Step 3: Proposal Channel & Workspace Scaffolding**."
        )
        return True

    return False


@app.on_message_pattern(re.compile(r"^(hello|hi|greetings)\b", re.IGNORECASE))
async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle greeting messages with S0-YK-04 Circle awareness & S0-YK-05 Intake."""
    profile = resolve_current_user(ctx)
    if profile.circle == "Unassigned":
        await ctx.send(
            "⛔ **Access Restricted:** Your account is not listed in the SharePoint `User_Directory`."
        )
        return
    await ctx.send(
        f"👋 **Hello {profile.display_name}!** You are mapped to the **{profile.circle}** Circle.\n\n"
        "**SSO & Circle Commands (S0-YK-04):**\n"
        "• `whoami` — View your resolved SSO profile and Circle\n"
        "• `my bids` — See only your Circle's bids\n\n"
        "**RFP Intake Card Commands (S0-YK-05):**\n"
        "• `intake` — Open the Repository RFP Hub\n"
        "• `intake 1`, `intake 2`, or `intake 3` — View client Step 2 Intake Cards"
    )


@app.on_message_pattern(re.compile(r"^(whoami|profile)\b", re.IGNORECASE))
async def handle_whoami(ctx: ActivityContext[MessageActivity]) -> None:
    """Return resolved user identity, department, Circle, and auth mode."""
    await ctx.reply(TypingActivityInput())
    profile = resolve_current_user(ctx)
    if profile.circle == "Unassigned":
        await ctx.send(
            "⛔ **Access Restricted:** Only users listed in the SharePoint `User_Directory` can access this assistant."
        )
        return
    coe_line = (
        f"\n• **COE Routing:** `{profile.circle_id}` — {profile.coe_email_id}"
        if profile.circle_id or profile.coe_email_id
        else ""
    )
    await ctx.send(
        f"👤 **Resolved User Profile (`{profile.auth_source}`)**\n\n"
        f"• **Name:** {profile.display_name}\n"
        f"• **Email:** {profile.email}\n"
        f"• **Title:** {profile.job_title}\n"
        f"• **Department:** {profile.department}\n"
        f"• **Resolved Circle:** **{profile.circle}**"
        f"{coe_line}\n"
        f"• **SSO Config Switch:** `USE_MOCK_SSO={config.USE_MOCK_SSO}` (`SSO_MODE={config.SSO_MODE}`)"
    )


@app.on_message_pattern(re.compile(r"^(my bids|bids)\b", re.IGNORECASE))
async def handle_my_bids(ctx: ActivityContext[MessageActivity]) -> None:
    """Show only the bids matching the signed-in user's Circle."""
    await ctx.reply(TypingActivityInput())
    profile = resolve_current_user(ctx)
    await ctx.send(_format_bids_summary(profile))


@app.on_message_pattern(re.compile(r"^persona\s+(.+)$", re.IGNORECASE))
async def handle_persona_switch(ctx: ActivityContext[MessageActivity]) -> None:
    """Switch active directory/mock profile for Playground testing (Mock SSO mode only)."""
    if not config.is_mock_sso or (config.DEFAULT_MOCK_USER_ID or "auto").strip().lower() == "auto":
        await ctx.send("Persona switching is disabled; user access is strictly controlled by SharePoint `User_Directory`.")
        return

    text = (ctx.activity.text or "").strip()
    match = re.match(r"^persona\s+(.+)$", text, re.IGNORECASE)
    target = match.group(1).strip() if match else ""
    directories = load_sharepoint_directories(config)

    selected_id = ""
    matched_user = resolve_directory_user(target, directories)
    if matched_user is not None:
        selected_id = matched_user.get("userEmail") or matched_user.get("userName") or ""
    else:
        circle_aliases = {"d&i": "data & insights", "data and insights": "data & insights"}
        normalized_target = circle_aliases.get(target.lower(), target.lower())
        for entry in directories.get("userDirectory", []):
            if entry.get("circleName", "").strip().lower() == normalized_target:
                selected_id = entry.get("userEmail") or entry.get("userName") or ""
                break

    if not selected_id:
        key = resolve_mock_key(target, fallback_key="")
        if key in MOCK_PROFILES:
            selected_id = key

    if not selected_id:
        dir_names = ", ".join(
            f"`{u.get('userName')}`" for u in directories.get("userDirectory", []) if u.get("userName")
        )
        available = ", ".join(MOCK_PROFILES.keys())
        await ctx.send(
            f"Unknown persona `{target}`. Directory users: {dir_names}. "
            f"Legacy aliases: `financial`, `healthcare`, `retail`, `enterprise` ({available})."
        )
        return

    conv_id = _get_conversation_id(ctx)
    _conversation_personas[conv_id] = selected_id
    profile = resolve_current_user(ctx)
    await ctx.send(
        f"🔄 Switched active user to **{profile.display_name}** "
        f"(Department: *{profile.department}* &rarr; Circle: **{profile.circle}**).\n\n"
        f"{_format_bids_summary(profile)}"
    )


@app.on_message_pattern(re.compile(r"^intake\s*(\S*)", re.IGNORECASE))
async def handle_intake_command(ctx: ActivityContext[MessageActivity]) -> None:
    """Post either the Hub selector or a specific client's Step 2 intake card."""
    await ctx.reply(TypingActivityInput())
    text = (ctx.activity.text or "").strip()
    match = re.search(r"intake\s*(\S*)", text, re.IGNORECASE)
    arg = match.group(1).strip() if match else ""

    if arg:
        rfp = get_rfp_by_query(arg)
        if rfp:
            await ctx.send(create_intake_card(rfp))
            return

    await ctx.send(create_rfp_selector_card())


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle general message activities and Adaptive Card action submissions."""
    await ctx.reply(TypingActivityInput())

    value = getattr(ctx.activity, "value", None)
    if isinstance(value, dict) and await _handle_intake_card_action(ctx, value):
        return

    text = (ctx.activity.text or "").strip()
    if "reply" in text.lower():
        await ctx.reply(
            "Hello! Type `whoami`, `my bids`, or `intake` to browse repository RFPs."
        )
    else:
        await ctx.send(
            f"You said '{text}'. Try `whoami`, `my bids`, or `intake`."
        )


if __name__ == "__main__":
    print("Teams Tab Dashboard URL: http://localhost:3978/", flush=True)
    asyncio.run(app.start())

# Verified production baseline
