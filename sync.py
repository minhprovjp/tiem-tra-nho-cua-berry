import os
import re
import urllib.request

BASE_URL = "https://trongnhi.trongnhi110266.workers.dev/"


def fetch_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def download_asset(path):
    if path.startswith(("http://", "https://", "data:")):
        return

    local_path = path.split("?", 1)[0]
    directory = os.path.dirname(local_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if os.path.exists(local_path):
        return

    url = BASE_URL + path
    print(f"Downloading new asset: {local_path}")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            with open(local_path, "wb") as output:
                output.write(response.read())
    except Exception as error:
        print(f"Failed to download {url}: {error}")


def remove_unofficial_site_gate(html):
    removed = False

    def strip_gate(match):
        nonlocal removed
        script = match.group(0)
        if re.search(r"window\.tsHostOk", script) and re.search(r"document\.open\s*\(", script):
            removed = True
            return ""
        return script

    cleaned = re.sub(r"<script\b[^>]*>[\s\S]*?</script\s*>", strip_gate, html, flags=re.IGNORECASE)

    if removed:
        print("Removed the unofficial-host warning page.")
    else:
        print("No unofficial-host warning page found.")
    return cleaned


def main():
    print("Fetching index.html...")
    try:
        html = fetch_text(BASE_URL)
    except Exception as error:
        print(f"Failed to fetch index.html: {error}")
        raise SystemExit(1)

    html = remove_unofficial_site_gate(html)
    with open("index.html", "w", encoding="utf-8", newline="") as output:
        output.write(html)

    assets = set()
    print("Fetching sw.js for asset list...")
    try:
        sw_js = fetch_text(BASE_URL + "sw.js")
        assets.update(
            asset
            for asset in re.findall(r"['\"]\.\/([^'\"]+)['\"]", sw_js)
            if asset and not asset.endswith("/")
        )
    except Exception as error:
        print(f"Failed to fetch sw.js: {error}")
        assets.update(re.findall(r"['\"](img/[^'\"]+\.(?:png|jpg|webp))['\"]", html))
        assets.update(re.findall(r"['\"](snd/[^'\"]+\.(?:mp3|wav))['\"]", html))
        assets.update(re.findall(r"['\"](s/baloo2/[^'\"]+\.woff2)['\"]", html))

    assets.update({"sw.js", "manifest.webmanifest", "icon-192.png"})

    for asset in sorted(assets):
        download_asset(asset)

    print("Sync complete.")


if __name__ == "__main__":
    main()
