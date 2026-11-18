import os
import zipfile

def build_package(bot_endpoint=None, bot_domain=None):
    if not bot_endpoint:
        bot_endpoint = "https://rg-app-test-hndtc6g2g9ejhmau.indiasouthcentral-01.azurewebsites.net"
    if not bot_domain:
        bot_domain = bot_endpoint.replace("https://", "").replace("http://", "").split("/")[0]

    with open("appPackage/manifest.json", "r", encoding="utf-8") as f:
        manifest_content = f.read()

    manifest_content = manifest_content.replace("${{BOT_ENDPOINT}}", bot_endpoint)
    manifest_content = manifest_content.replace("${{BOT_DOMAIN}}", bot_domain)

    os.makedirs("appPackage/build", exist_ok=True)
    manifest_build = "appPackage/build/manifest.json"
    with open(manifest_build, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    output_zip = "app_package.zip"
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(manifest_build, "manifest.json")
        z.write("appPackage/color.png", "color.png")
        z.write("appPackage/outline.png", "outline.png")

    print(f"Created {output_zip} successfully ({os.path.getsize(output_zip)} bytes)")
    print(f"Configured endpoint: {bot_endpoint}")
    print(f"Configured domain: {bot_domain}")

if __name__ == "__main__":
    import sys
    custom_endpoint = sys.argv[1] if len(sys.argv) > 1 else None
    build_package(bot_endpoint=custom_endpoint)

