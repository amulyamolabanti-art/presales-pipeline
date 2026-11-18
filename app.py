"""Root ASGI entrypoint for Azure App Service, Gunicorn, and Uvicorn.

Exposes the Microsoft Teams App / FastAPI instance from src/bot/app.py.
"""
import importlib.util
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent
_BOT_DIR = _REPO_ROOT / "src" / "bot"

# Ensure both the repository root and src/bot are on Python sys.path
for _path in (str(_BOT_DIR), str(_REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Dynamically load the bot application module from src/bot/app.py
_bot_app_file = _BOT_DIR / "app.py"
_spec = importlib.util.spec_from_file_location("bot_application", str(_bot_app_file))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load bot application from {_bot_app_file}")

_bot_mod = importlib.util.module_from_spec(_spec)
sys.modules["bot_application"] = _bot_mod
_spec.loader.exec_module(_bot_mod)

# Expose standard ASGI callable attributes
app = _bot_mod.app
api = getattr(_bot_mod, "api", getattr(app, "server", None))
fastapi_app = getattr(_bot_mod, "fastapi_app", None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
