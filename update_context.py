"""
update_context.py — Auto-update PROJECT_CONTEXT.md with file checksums & structure.

Run after any code modification to keep the context file fresh for LLM analysis.

Usage:
    python update_context.py              # Update checksums + timestamp
    python update_context.py --watch      # Watch for changes and auto-update
    python update_context.py --full       # Full regeneration (structure + checksums)
"""

import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ──────────────────────────────────────────────────────────────── config
ROOT = Path(__file__).resolve().parent
CONTEXT_FILE = ROOT / "PROJECT_CONTEXT.md"

# Key files to track (relative to ROOT)
TRACKED_FILES = [
    "src/bot/app.py",
    "src/bot/config.py",
    "src/bot/tab_api.py",
    "src/bot/requirements.txt",
    "src/bot/auth/__init__.py",
    "src/bot/auth/sso_service.py",
    "src/bot/auth/directory_service.py",
    "src/bot/auth/circle_mapper.py",
    "src/bot/auth/mock_profiles.json",
    "src/bot/auth/circle_mapping.json",
    "src/bot/auth/coe_mapping.json",
    "src/bot/auth/user_circle_mapping.json",
    "src/bot/cards/rfp_catalog.py",
    "src/bot/cards/intake_card.json",
    "src/bot/karthik_api/main.py",
    "src/bot/karthik_api/schema.py",
    "src/bot/karthik_api/repo.py",
    "src/bot/karthik_api/backends.py",
    "src/bot/karthik_api/calc.py",
    "src/bot/karthik_api/seed.py",
    "src/tab/package.json",
    "src/tab/vite.config.ts",
    "src/tab/tsconfig.json",
    "contracts/dashboard/dashboard.schema.json",
    "db/001_create_tables.sql",
    "db/002_seed_data.sql",
    ".env",
    "m365agents.yml",
    "m365agents.local.yml",
    "m365agents.playground.yml",
    "AI_CODING_RULES.md",
    "README.md",
]

# Directories to scan for additional files (only .py, .ts, .tsx, .json, .sql, .txt)
SCAN_DIRS = [
    "src/bot",
    "src/tab/src",
    "contracts",
    "db",
    "prompts",
    "env",
]

TRACKED_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".sql", ".txt", ".md", ".yml", ".yaml", ".css"}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".pytest_cache", "dist",
    ".vscode", ".aava", "venv", ".vite", "eval",
}


# ──────────────────────────────────────────────────────────────── helpers

def file_hash(path: Path) -> str:
    """Return MD5 hex digest of a file, or 'MISSING' if not found."""
    if not path.exists():
        return "MISSING"
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def file_lines(path: Path) -> int:
    """Return line count, or 0 if missing."""
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def discover_extra_files() -> list[str]:
    """Discover files in SCAN_DIRS not already in TRACKED_FILES."""
    tracked_set = set(TRACKED_FILES)
    extra = []
    for scan_dir in SCAN_DIRS:
        dirpath = ROOT / scan_dir
        if not dirpath.exists():
            continue
        for root, dirs, files in os.walk(dirpath):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fname in sorted(files):
                ext = Path(fname).suffix.lower()
                if ext not in TRACKED_EXTENSIONS:
                    continue
                full = Path(root) / fname
                rel = str(full.relative_to(ROOT)).replace("\\", "/")
                if rel not in tracked_set:
                    extra.append(rel)
    return sorted(extra)


def now_iso() -> str:
    """Return ISO 8601 timestamp with IST offset."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%dT%H:%M:%S+05:30")


def build_checksums_block() -> str:
    """Build the checksums markdown table."""
    all_files = list(TRACKED_FILES) + discover_extra_files()
    lines = [
        "| File | Lines | MD5 | Status |",
        "|------|-------|-----|--------|",
    ]
    for rel_path in all_files:
        full = ROOT / rel_path
        md5 = file_hash(full)
        lc = file_lines(full)
        status = "✅" if md5 != "MISSING" else "❌ MISSING"
        lines.append(f"| `{rel_path}` | {lc} | `{md5[:10]}…` | {status} |")
    return "\n".join(lines)


def update_context_file() -> bool:
    """Update the PROJECT_CONTEXT.md with fresh checksums and timestamp.
    Returns True if changes were made."""
    if not CONTEXT_FILE.exists():
        print(f"ERROR: {CONTEXT_FILE} not found. Please create it first.")
        return False

    content = CONTEXT_FILE.read_text(encoding="utf-8")
    original = content

    # Update "Last Updated" timestamp
    content = re.sub(
        r"\*\*Last Updated\*\*:\s*\S+",
        f"**Last Updated**: {now_iso()}",
        content,
    )

    # Update checksums block
    checksums = build_checksums_block()
    content = re.sub(
        r"<!-- CHECKSUMS_START -->.*?<!-- CHECKSUMS_END -->",
        f"<!-- CHECKSUMS_START -->\n{checksums}\n<!-- CHECKSUMS_END -->",
        content,
        flags=re.DOTALL,
    )

    if content != original:
        CONTEXT_FILE.write_text(content, encoding="utf-8")
        print(f"[{now_iso()}] PROJECT_CONTEXT.md updated ({len(content):,} bytes)")
        return True
    else:
        print(f"[{now_iso()}] No changes detected.")
        return False


def watch_mode():
    """Watch tracked files for changes and auto-update."""
    print(f"Watching for file changes in: {ROOT}")
    print("   Press Ctrl+C to stop.\n")

    # Build initial state
    all_files = list(TRACKED_FILES) + discover_extra_files()
    last_hashes = {f: file_hash(ROOT / f) for f in all_files}
    update_context_file()  # Initial update

    try:
        while True:
            time.sleep(3)  # Poll every 3 seconds
            all_files = list(TRACKED_FILES) + discover_extra_files()
            changed = False
            for f in all_files:
                current = file_hash(ROOT / f)
                if last_hashes.get(f) != current:
                    print(f"   Changed: {f}")
                    last_hashes[f] = current
                    changed = True
            if changed:
                update_context_file()
    except KeyboardInterrupt:
        print("\nWatch stopped.")


# ──────────────────────────────────────────────────────────────── main
if __name__ == "__main__":
    args = sys.argv[1:]
    if "--watch" in args:
        watch_mode()
    elif "--full" in args:
        print("Full update mode:")
        update_context_file()
    else:
        update_context_file()
