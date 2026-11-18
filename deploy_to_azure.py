"""Portable, cross-platform Azure App Service Zip Deploy script.

Usage:
    python deploy_to_azure.py [path_to_publish_settings]

If no path is provided, it automatically detects the most recent
*.PublishSettings file in the user's Downloads or current directory.
"""
import base64
import glob
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


def find_publish_settings(specified_path: str | None = None) -> str:
    if specified_path:
        if os.path.isfile(specified_path):
            return os.path.abspath(specified_path)
        print(f"Error: Specified PublishSettings file not found: {specified_path}")
        sys.exit(1)

    # Search current directory
    local_files = glob.glob("*.PublishSettings")
    # Search user's Downloads folder
    downloads_dir = os.path.expanduser("~/Downloads")
    download_files = glob.glob(os.path.join(downloads_dir, "*.PublishSettings"))

    candidates = local_files + download_files
    if not candidates:
        print("=" * 60)
        print("ERROR: No .PublishSettings file found!")
        print("Please download the publish profile from Azure Portal:")
        print("  1. Go to your Web App in Azure Portal.")
        print("  2. Click 'Download publish profile'.")
        print("  3. Place it in your Downloads folder or run:")
        print("     python deploy_to_azure.py <path_to_publish_settings>")
        print("=" * 60)
        sys.exit(1)

    # Pick the most recently modified file
    candidates.sort(key=os.path.getmtime, reverse=True)
    chosen = os.path.abspath(candidates[0])
    print(f"Discovered PublishSettings: {chosen}")
    return chosen


def build_deployment_zip() -> bytes:
    """Build deployment zip in-memory with all required production files."""
    print("Building application deployment zip package...")
    buf = io.BytesIO()

    include_dirs = ["src", "data", "prompts", "contracts", "appPackage", "db"]
    include_files = ["requirements.txt", "app.py"]

    exclude_patterns = ["node_modules", ".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".vite"]

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in include_files:
            if os.path.isfile(f):
                z.write(f, f)

        for d in include_dirs:
            if not os.path.isdir(d):
                continue
            for root, dirs, files in os.walk(d):
                dirs[:] = [sub for sub in dirs if sub not in exclude_patterns]
                for file in files:
                    if file.endswith((".pyc", ".xlsx", ".tmp", ".log")):
                        continue
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ".")
                    z.write(full_path, rel_path)

    zip_bytes = buf.getvalue()
    print(f"Deployment package created in-memory ({len(zip_bytes)/(1024*1024):.2f} MB).")
    return zip_bytes


def main():
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    settings_path = find_publish_settings(arg_path)

    tree = ET.parse(settings_path)
    root = tree.getroot()

    username = None
    password = None
    scm_host = None

    for p in root.findall("publishProfile"):
        method = p.attrib.get("publishMethod")
        if method in ("ZipDeploy", "MSDeploy"):
            username = p.attrib.get("userName")
            password = p.attrib.get("userPWD")
            scm_host = p.attrib.get("publishUrl", "").split(":")[0]
            break

    if not username or not password or not scm_host:
        print("ERROR: Could not find deployment credentials in PublishSettings.")
        print("Ensure 'SCM Basic Auth Publishing Credentials' is enabled on the App Service.")
        sys.exit(1)

    deploy_url = f"https://{scm_host}/api/zipdeploy?isAsync=true"
    print(f"Target App: https://{scm_host.replace('.scm.', '.')}")
    print(f"Target SCM: {deploy_url}")
    print(f"User:       {username}")

    zip_bytes = build_deployment_zip()

    auth_str = f"{username}:{password}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

    req = urllib.request.Request(
        deploy_url,
        data=zip_bytes,
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/zip",
        },
        method="POST",
    )

    print("Uploading package to Azure App Service...")
    poll_url = None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            status = resp.status
            poll_url = resp.headers.get("Location")
            print(f"Deployment request accepted! (HTTP {status})")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"Deployment HTTP Error {e.code}: {err_body}")
        if e.code == 401:
            print("\n>> 401 Unauthorized: SCM Basic Authentication is likely DISABLED on this Web App.")
            print(">> Fix: Azure Portal -> Web App -> Configuration -> General settings -> set 'SCM Basic Auth' to ON -> Save.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during upload: {e}")
        sys.exit(1)

    if poll_url:
        print(f"Polling Oryx build status: {poll_url}")
        status_req = urllib.request.Request(
            poll_url,
            headers={"Authorization": f"Basic {b64_auth}"},
        )
        for _ in range(60):
            time.sleep(5)
            try:
                with urllib.request.urlopen(status_req, timeout=30) as poll_resp:
                    data = json.loads(poll_resp.read().decode("utf-8"))
                    status_str = data.get("status", "unknown")
                    msg = data.get("message", "")
                    progress = data.get("progress", "")
                    print(f"Status: {status_str} | {progress} {msg}")
                    if data.get("complete"):
                        if data.get("status") == 4 or status_str.lower() == "success":
                            print("\n" + "=" * 60)
                            print(">>> DEPLOYMENT SUCCEEDED! <<<")
                            print("=" * 60)
                        else:
                            print(f"\nDeployment finished with status: {status_str}")
                        break
            except Exception as e:
                print(f"Polling check: {e}")
    else:
        print("Upload completed!")


if __name__ == "__main__":
    main()
