import urllib.request
import re
import os

BASE_URL = "https://trongnhi.trongnhi110266.workers.dev/"

def download_asset(path):
    if path.startswith("http"):
        return
    url = BASE_URL + path
    local_path = path.split("?")[0]
    
    # Don't download if we're not in a directory where we can write safely,
    # but the action runs in the repo root.
    if os.path.dirname(local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
    if not os.path.exists(local_path):
        print(f"Downloading new asset: {local_path}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urllib.request.urlopen(req).read()
            with open(local_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def main():
    print("Fetching index.html...")
    try:
        req = urllib.request.Request(BASE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch index.html: {e}")
        return
    
    # Comment out BAD array to disable bad events
    print("Commenting out BAD array...")
    # Regex to find const BAD = [ ... ]; and comment it out
    pattern = re.compile(r'(const\s+BAD\s*=\s*\[.*?\];)', re.DOTALL)
    replacement = r'/* \1 */\nconst BAD = [];'
    
    if pattern.search(html):
        html = pattern.sub(replacement, html)
        print("Successfully commented out BAD array.")
    else:
        print("WARNING: Could not find BAD array to comment out.")
        
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # Find all local assets to download
    assets = set()
    print("Fetching sw.js for asset list...")
    try:
        sw_req = urllib.request.Request(BASE_URL + "sw.js", headers={'User-Agent': 'Mozilla/5.0'})
        sw_js = urllib.request.urlopen(sw_req).read().decode('utf-8')
        sw_assets = re.findall(r'[\'"]\.\/([^\'"]+)[\'"]', sw_js)
        for a in sw_assets:
            if a != "" and not a.endswith('/'):
                assets.add(a)
    except Exception as e:
        print(f"Failed to fetch sw.js: {e}")
        assets.update(re.findall(r'["\'](img/[^"\']+\.(?:png|jpg|webp))["\']', html))
        assets.update(re.findall(r'["\'](snd/[^"\']+\.(?:mp3|wav))["\']', html))
        assets.update(re.findall(r'["\'](s/baloo2/[^"\']+\.woff2)["\']', html))
        
    assets.add("sw.js")
    assets.add("manifest.webmanifest")
    assets.add("icon-192.png")
    
    for asset in assets:
        download_asset(asset)
        
    print("Sync complete.")

if __name__ == "__main__":
    main()
