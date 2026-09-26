import os
import re
import base64
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

# --- Deobfuscation Logic ---
def fnv1a_hash(s):
    """Replicates the JS k() function to generate the 32-byte key stream."""
    a = 2166136261
    for ch in s:
        a = ((a ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    o = []
    for _ in range(32):
        a = (a ^ (a << 13)) & 0xFFFFFFFF
        a = (a ^ (a >> 17)) & 0xFFFFFFFF
        a = (a ^ (a << 5)) & 0xFFFFFFFF
        o.append(a & 255)
    return o

def b64_decode(x):
    return list(base64.b64decode(x))

def find_key(w_strings, d_bytes):
    """Brute-forces the correct hostname hash to find the decryption key."""
    target = "/*ts*/"
    # Common hostnames and their suffixes
    domains = ["file:", "localhost", "127.0.0.1", "trongnhi.trongnhi110266.workers.dev", "workers.dev", "trongnhi110266.workers.dev"]
    q_candidates = [fnv1a_hash(dom) for dom in domains]
    
    for w_b64 in w_strings:
        w = b64_decode(w_b64)
        if len(w) != 32: continue
        for q in q_candidates:
            K = [w[n] ^ q[n] for n in range(32)]
            # Check if the first 6 bytes decrypt to the target signature
            sig = "".join(chr(d_bytes[n] ^ K[n % 32] ^ ((n * 7 + (n >> 8)) & 255)) for n in range(6))
            if sig == target:
                return K
    return None

def deobfuscate_and_clean(html):
    """Finds the obfuscated loader, decrypts it, removes the hostname blocker, and replaces it."""
    pattern = r'<script>\s*\(function\(\)\{var W=\[.*?\}\)\(\);\s*</script>'
    match = re.search(pattern, html, re.DOTALL)
    
    if not match:
        print("Obfuscated loader not found.")
        return html
        
    script_content = match.group(0)
    
    # Extract W array and D string
    w_match = re.search(r'var W=\[(.*?)\]', script_content, re.DOTALL)
    d_match = re.search(r'D="([^"]+)"', script_content)
    
    if not w_match or not d_match:
        print("Could not extract W or D from loader.")
        return html
        
    w_strings = re.findall(r'"([^"]+)"', w_match.group(1))
    d_bytes = b64_decode(d_match.group(1))
    
    K = find_key(w_strings, d_bytes)
    if not K:
        print("Could not find decryption key. Add the correct hostname to the domains list.")
        return html
        
    # Decrypt the payload
    decrypted_bytes = bytearray()
    for n in range(len(d_bytes)):
        val = d_bytes[n] ^ K[n % 32] ^ ((n * 7 + (n >> 8)) & 255)
        decrypted_bytes.append(val)
        
    js_code = decrypted_bytes.decode('utf-8', errors='replace')
    
    # Strip the hostname blockers
    js_code = js_code.replace("if(!window.tsHostOk||!window.tsHostOk())throw new Error('host');", "")
    js_code = js_code.replace("if(window.tsHostOk &&!window.tsHostOk())return;", "")
    
    # Fallback regex in case of slight spacing variations
    js_code = re.sub(r'if\s*\(\s*!window\.tsHostOk\s*\|\|\s*!window\.tsHostOk\s*\(\)\s*\)\s*throw\s+new\s+Error\s*\(\s*[\'"]host[\'"]\s*\)\s*;', '', js_code)
    js_code = re.sub(r'if\s*\(\s*window\.tsHostOk\s*&&\s*!window\.tsHostOk\s*\(\)\s*\)\s*return\s*;', '', js_code)
    
    # Replace the original obfuscated tag with the clean decrypted code
    new_script_tag = f"<script>{js_code}</script>"
    html = html[:match.start()] + new_script_tag + html[match.end():]
    
    print("Successfully deobfuscated and cleaned game loader.")
    return html

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
        
    # Process the HTML (Deobfuscate & Clean)
    html = deobfuscate_and_clean(html)
    
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
        # Fallback regexes if sw.js fails
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