"""Validation tests for Teams Tab frontend."""
import os


def test_tab_html_exists():
    """Verify that Teams Tab index.html exists and contains valid structure."""
    tab_dir = os.path.dirname(__file__)
    index_file = os.path.join(tab_dir, "index.html")
    assert os.path.isfile(index_file)

    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "<title>AI Proposal Assistant" in content
        assert "MicrosoftTeams.min.js" in content
