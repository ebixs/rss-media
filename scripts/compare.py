"""Render one prompt with several Cloudflare Workers AI image models side by side.

Reads compare/prompt.txt, writes compare/<model-short>.jpg and compare/results.json.
Used to pick the best free model; not part of the daily pipeline.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "compare"

MODELS = [
    ("lucid-origin", "@cf/leonardo/lucid-origin", "json", {"width": 896, "height": 1120, "steps": 30, "guidance": 4.5}),
    ("flux-2-klein-9b", "@cf/black-forest-labs/flux-2-klein-9b", "multipart", {"width": "896", "height": "1120"}),
    ("phoenix", "@cf/leonardo/phoenix-1.0", "json", {"width": 896, "height": 1120, "num_steps": 25, "guidance": 4}),
    ("flux-1-schnell", "@cf/black-forest-labs/flux-1-schnell", "json", {"steps": 8}),
]


def run(model: str, kind: str, extra: dict, prompt: str) -> bytes:
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}
    if kind == "json":
        body = json.dumps({"prompt": prompt, **extra}).encode()
        headers["Content-Type"] = "application/json"
    else:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in {"prompt": prompt, **extra}.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"HTTP {err.code}: {(err.read() or b'')[:300].decode('utf-8', 'replace')}") from None
    if ctype.startswith("image/"):
        return raw
    payload = json.loads(raw)
    image = (payload.get("result") or {}).get("image")
    if not image:
        raise RuntimeError(f"no image: {str(payload)[:300]}")
    return base64.b64decode(image)


def main() -> int:
    prompt = (OUT / "prompt.txt").read_text(encoding="utf-8").strip()
    results = {}
    for short, model, kind, extra in MODELS:
        t = time.time()
        try:
            data = run(model, kind, extra, prompt)
            (OUT / f"{short}.jpg").write_bytes(data)
            results[short] = {"ok": True, "seconds": round(time.time() - t, 1), "bytes": len(data)}
        except Exception as err:
            results[short] = {"ok": False, "error": str(err)[:400]}
        print(short, results[short])
    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
