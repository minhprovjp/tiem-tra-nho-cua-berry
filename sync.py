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
        return True
    local_path = path.split("?", 1)[0]
    directory = os.path.dirname(local_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    if local_path != "sw.js" and os.path.isfile(local_path) and os.path.getsize(local_path) > 0:
        return True
    url = BASE_URL + path
    print(f"Downloading new asset: {local_path}")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        if not content.strip():
            raise ValueError("Downloaded asset is empty")
        with open(local_path, "wb") as output:
            output.write(content)
        return True
    except Exception as error:
        print(f"Failed to download {url}: {error}")
        return os.path.isfile(local_path) and os.path.getsize(local_path) > 0

def remove_unofficial_site_gate(html):
    removed = False
    
    # 1. Remove the specific obfuscated script block (var W=[...])
    obfuscated_pattern = r'<script\b[^>]*>\s*\(function\(\)\{var W=\[[\s\S]*?\}\)\(\);\s*<\/script>'
    if re.search(obfuscated_pattern, html, re.IGNORECASE):
        html = re.sub(obfuscated_pattern, '', html)
        removed = True
        print("Removed the obfuscated anti-bot/unofficial-host script.")

    # 2. Remove the other known gate script (window.tsHostOk)
    def strip_gate(match):
        nonlocal removed
        script = match.group(0)
        if re.search(r"window\.tsHostOk", script) and re.search(r"document\.open\s*\(", script):
            removed = True
            return ""
        return script
        
    cleaned = re.sub(r"<script\b[^>]*>[\s\S]*?</script\s*>", strip_gate, html, flags=re.IGNORECASE)
    
    if removed:
        print("Successfully removed unofficial-host gate(s).")
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
        downloaded = download_asset(asset)
        if asset == "sw.js" and not downloaded:
            raise SystemExit("Could not obtain a non-empty sw.js; aborting sync.")
            
    print("Sync complete.")

if __name__ == "__main__":
    main()