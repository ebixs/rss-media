"""Render character / scene images with FLUX.2 klein, optionally with reference images
(up to 4, each sent below 512x512) so one brand character stays the same everywhere.

Reads characters/jobs.json: [{"id", "prompt", "refs": ["characters/ref/x.png", ...],
"width": 1024, "height": 1024, "seeds": [1, 2]}]. Writes characters/out/<id>-<seed>.jpg,
skipping images that already exist. Free Workers AI allocation; nothing secret printed.
"""
from __future__ import annotations

import base64, io, json, os, pathlib, sys, urllib.error, urllib.request, uuid

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "@cf/black-forest-labs/flux-2-klein-9b"


def small_png(path: pathlib.Path) -> bytes:
    im = Image.open(path).convert("RGB")
    im.thumbnail((508, 508), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def run(prompt: str, refs: list[pathlib.Path], w: int, h: int, seed: int) -> bytes:
    try:
        return run_on(prompt, refs, w, h, seed, os.environ.get("CF_REEL_ACCOUNT_ID") or os.environ["CF_ACCOUNT_ID"],
                      os.environ.get("CF_REEL_API_TOKEN") or os.environ["CF_API_TOKEN"])
    except RuntimeError as err:
        if "429" not in str(err) or not os.environ.get("CF_REEL_ACCOUNT_ID"):
            raise
        print("reel account quota used up; using the main account")
        return run_on(prompt, refs, w, h, seed, os.environ["CF_ACCOUNT_ID"], os.environ["CF_API_TOKEN"])


def run_on(prompt, refs, w, h, seed, acc, tok) -> bytes:
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc.strip()}/ai/run/{MODEL}"
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
             for k, v in {"prompt": prompt[:2048], "width": w, "height": h, "seed": seed}.items()]
    for i, r in enumerate(refs[:4]):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="input_image_{i}"; filename="r{i}.png"\r\n'
                     f'Content-Type: image/png\r\n\r\n'.encode() + small_png(r) + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(url, data=b"".join(parts), headers={
        "Authorization": f"Bearer {tok.strip()}", "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw, ctype = resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"HTTP {err.code}: {(err.read() or b'')[:300].decode('utf-8', 'replace')}") from None
    if ctype.startswith("image/"):
        return raw
    img = (json.loads(raw).get("result") or {}).get("image")
    if not img:
        raise RuntimeError(f"no image: {raw[:200]!r}")
    return base64.b64decode(img)


def main() -> int:
    jobs = json.loads((ROOT / "characters" / "jobs.json").read_text(encoding="utf-8"))
    out = ROOT / "characters" / "out"
    out.mkdir(parents=True, exist_ok=True)
    fails = 0
    # seed-major order: every job gets its first image before any job gets a second
    order = [(j, seed) for k in range(max(len(j.get("seeds", [1])) for j in jobs))
             for j in jobs if k < len(j.get("seeds", [1])) for seed in [j["seeds"][k] if "seeds" in j else 1]]
    for j, seed in order:
        refs = [ROOT / r for r in j.get("refs", [])]
        if True:
            dest = out / f"{j['id']}-{seed}.jpg"
            if dest.exists():
                continue
            try:
                data = run(j["prompt"], refs, int(j.get("width", 1024)), int(j.get("height", 1024)), int(seed))
                Image.open(io.BytesIO(data)).convert("RGB").save(dest, "JPEG", quality=92)
                print("ok", dest.name)
            except Exception as e:
                fails += 1
                print(f"::error title={dest.name}::{str(e)[:300]}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
