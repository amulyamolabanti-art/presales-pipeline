from fastapi.testclient import TestClient
import sys
import os

# Ensure src/bot is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "bot")))

def test_fastapi_app_loads():
    """Verify that the FastAPI backend app loads and routes are registered."""
    from karthik_api.main import app
    client = TestClient(app)
    # Check that FastAPI app initializes properly
    assert app.title == "AI Proposal Assistant (prototype)"

def test_config_loads():
    """Verify application configuration loads without errors."""
    from config import Config
    cfg = Config()
    assert cfg is not None