import base64
import re
import sys

def fnv1a_key(hostname):
    """Replicate the JS k() function to generate the 32-byte key stream."""
    a = 2166136261
    for ch in hostname:
        a = ((a ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    o = []
    for _ in range(32):
        a = (a ^ (a << 13)) & 0xFFFFFFFF
        a = (a ^ (a >> 17)) & 0xFFFFFFFF
        a = (a ^ (a << 5)) & 0xFFFFFFFF
        o.append(a & 255)
    return o

def deobfuscate(js_code):
    # Fixed regex: W and D are in the same var statement
    # var W=["...","..."],D="...";
    m = re.search(r'var\s+W\s*=\s*\[([^\]]+)\]\s*,\s*D\s*=\s*"([^"]+)"', js_code)
    if not m:
        raise ValueError("Could not find W or D in the script.")

    w_strings = re.findall(r'"([^"]+)"', m.group(1))
    d_b64 = m.group(2)

    d_bytes = list(base64.b64decode(d_b64))

    # Try known hostnames
    hostnames = [
        "file:",
        "localhost",
        "127.0.0.1",
        "trongnhi.trongnhi110266.workers.dev",
        "workers.dev",
        # Add the official hostname here if different
    ]

    target = "/*ts*/"

    for host in hostnames:
        q = fnv1a_key(host)
        for w_b64 in w_strings:
            w = list(base64.b64decode(w_b64))
            if len(w) != 32:
                continue
            K = [w[n] ^ q[n] for n in range(32)]

            # Check signature
            sig = ""
            for n in range(6):
                sig += chr(d_bytes[n] ^ K[n % 32] ^ ((n * 7 + (n >> 8)) & 255))

            if sig == target:
                print(f"[+] Key found! Hostname: {host}")
                # Decrypt full payload
                out = bytearray(len(d_bytes))
                for n in range(len(d_bytes)):
                    out[n] = d_bytes[n] ^ K[n % 32] ^ ((n * 7 + (n >> 8)) & 255)
                return out.decode("utf-8", errors="replace")

    raise ValueError("No matching key found. Add the correct hostname to the list.")

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    with open(input_file, "r", encoding="utf-8") as f:
        js = f.read()
    result = deobfuscate(js)
    out_file = "decrypted.js"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"[+] Decrypted {len(result)} bytes -> {out_file}")