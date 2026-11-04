"""Generate AI backgrounds for every post that has no images yet, then compose
the branded final images.

Runs in GitHub Actions. Needs two repository secrets:
    CF_ACCOUNT_ID   Cloudflare account id
    CF_API_TOKEN    Cloudflare API token with the "Workers AI" permission

Each post lives in posts/<slug>/post.md with a header like:

    ---
    publish_at: 2026-10-13T20:30:00+03:30
    service: پانسمان سوختگی
    headline: ...
    subline: ...
    candidates: 2            (optional, 1-3, default 2)
    format: reel             (optional) -> 3 vertical photos from image_prompt_1..3 and a
                             15 s reel.mp4 built by scripts/reel.py (needs scene_1..3)
    image_prompt: English scene description (no text in the image)
    ---
    caption ...

Output per post:
    background-<n>.jpg   raw AI photo for candidate n
    final-<n>.jpg        branded 1080x1350 image for candidate n
    status.json          {"ok", "model", "candidates", "errors"}
Claude reviews the candidates, picks one, and copies it to final.jpg.

Models are tried in order (all within the free daily Workers AI allocation);
the first that works is used. Nothing secret is ever printed.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"

# (short name, model id, request kind, extra fields)
MODELS = [
    ("flux-2-klein-9b", "@cf/black-forest-labs/flux-2-klein-9b", "multipart",
     {"width": "1088", "height": "1360"}),
    ("lucid-origin", "@cf/leonardo/lucid-origin", "json",
     {"width": 1088, "height": 1360, "steps": 30, "guidance": 4.5}),
    ("flux-1-schnell", "@cf/black-forest-labs/flux-1-schnell", "json", {"steps": 8}),
]

STYLE = (
    "Editorial healthcare brand-campaign photograph, photorealistic, natural soft daylight, "
    "calm premium colour palette of deep navy, ivory white and soft natural medical green with "
    "a subtle indigo accent, clean modern upscale Tehran apartment interior, shallow depth of "
    "field, 50mm lens, realistic skin texture, natural hands and faces, Iranian people; any woman "
    "wears a chic, modern, loosely draped hijab or elegant scarf (never a tight white wrap); "
    "uncluttered composition with calm space in the lower part of the frame for a headline; "
    "absolutely no text, no letters, no labels, no logos, no watermark, no signage."
)

sys.path.insert(0, str(ROOT / "scripts"))
from compose import compose, read_header  # noqa: E402
from reel import build as build_reel  # noqa: E402
from reel_motion import build as build_motion  # noqa: E402


# For one-off brand/campaign posts whose scene is not a home interior.
CAMPAIGN_STYLE = (
    "Cinematic editorial brand-campaign photograph, photorealistic, premium and hopeful mood, "
    "colour palette of deep navy, ivory white and warm golden light with a subtle indigo accent, "
    "realistic skin texture, natural hands and faces, Iranian people; any woman wears a chic, "
    "modern, loosely draped hijab or elegant scarf (never a tight white wrap); calm uncluttered "
    "space in the lower part of the frame for a headline; absolutely no text, no letters, no "
    "labels, no logos, no watermark, no signage, no screens showing writing."
)


def run_model(model: str, kind: str, extra: dict, prompt: str, seed: int) -> bytes:
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}
    fields = {"prompt": prompt[:2048], "seed": seed, **extra}
    if kind == "json":
        body = json.dumps(fields).encode()
        headers["Content-Type"] = "application/json"
    else:
        boundary = uuid.uuid4().hex
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
            for k, v in fields.items()
        ]
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        detail = (err.read() or b"")[:300].decode("utf-8", "replace")
        raise RuntimeError(f"{model}: HTTP {err.code}: {detail}") from None
    except urllib.error.URLError as err:
        raise RuntimeError(f"{model}: network error: {err.reason}") from None
    if ctype.startswith("image/"):
        return raw
    payload = json.loads(raw)
    image = (payload.get("result") or {}).get("image")
    if not image:
        raise RuntimeError(f"{model}: no image: {str(payload.get('errors'))[:200]}")
    return base64.b64decode(image)


VERTICAL = {"flux-2-klein-9b": {"width": "864", "height": "1536"},
            "lucid-origin": {"width": 864, "height": 1536, "steps": 30, "guidance": 4.5}}


def generate(prompt: str, seed: int, vertical: bool = False) -> tuple[bytes, str, list[str]]:
    errors = []
    for short, model, kind, extra in MODELS:
        if vertical:
            extra = VERTICAL.get(short, extra)
        try:
            return run_model(model, kind, extra, prompt, seed), short, errors
        except RuntimeError as err:
            errors.append(str(err)[:300])
    raise RuntimeError(" | ".join(errors))


def process(post_dir: pathlib.Path) -> dict:
    meta = read_header(post_dir / "post.md")
    prompt = meta.get("image_prompt", "").strip()
    if not prompt:
        return {"ok": False, "error": "image_prompt is missing in post.md"}
    is_reel = meta.get("format", "").strip() == "reel"
    count = 3 if is_reel else max(1, min(3, int(meta.get("candidates", "2") or 2)))
    style = CAMPAIGN_STYLE if meta.get("style", "").strip() == "campaign" else STYLE
    base_seed = int.from_bytes(os.urandom(3), "big")
    made, models, errors = [], [], []
    for n in range(1, count + 1):
        # image_prompt_<n> lets one post try different creative concepts
        full = f"{(meta.get(f'image_prompt_{n}') or prompt).strip()}. {style}"
        try:
            data, model, errs = generate(full, base_seed + n * 7919, vertical=is_reel)
        except RuntimeError as err:
            errors.append(str(err))
            continue
        errors += errs
        (post_dir / f"background-{n}.jpg").write_bytes(data)
        if not is_reel:
            compose(post_dir, f"background-{n}.jpg", f"final-{n}.jpg")
            made.append(f"final-{n}.jpg")
        models.append(model)
    if is_reel:
        if len(models) < 3:
            return {"ok": False, "format": "reel", "error": "a reel needs all 3 scene photos", "errors": errors[:5]}
        try:
            build_motion(post_dir)          # motion graphics + original music
            engine = "motion"
        except Exception as err:            # never lose the post: fall back to the simple reel
            errors.append(f"motion reel failed, simple reel used: {err}"[:300])
            build_reel(post_dir)
            engine = "simple"
        made = ["reel.mp4", "cover.jpg", "frame-1.jpg", "frame-2.jpg", "frame-3.jpg", "frame-4.jpg"]
        return {"ok": True, "format": "reel", "engine": engine, "candidates": made, "models": models, "errors": errors[:5]}
    return {"ok": bool(made), "candidates": made, "models": models, "errors": errors[:5]}


def needs_work(post_dir: pathlib.Path) -> bool:
    if (post_dir / "REGENERATE").exists():
        return True
    if (post_dir / "reel.mp4").exists():
        return False
    return not any(post_dir.glob("final*.jpg"))


def main() -> int:
    for var in ("CF_ACCOUNT_ID", "CF_API_TOKEN"):
        if not os.environ.get(var):
            print(f"::error title=Config::secret {var} is missing")
            return 1
    failures = 0
    for post_md in sorted(POSTS.glob("*/post.md")):
        post_dir = post_md.parent
        if not needs_work(post_dir):
            continue
        (post_dir / "REGENERATE").unlink(missing_ok=True)
        for old in (list(post_dir.glob("final-*.jpg")) + list(post_dir.glob("background-*.jpg"))
                    + list(post_dir.glob("frame-*.jpg")) + list(post_dir.glob("reel.mp4"))):
            old.unlink()
        try:
            status = process(post_dir)
        except Exception as err:  # keep going with the next post
            status = {"ok": False, "error": str(err)[:400]}
        (post_dir / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{post_dir.name}: {status}")
        if not status.get("ok"):
            failures += 1
            print(f"::error title={post_dir.name}::{status.get('error') or status.get('errors')}")
    print(f"done, failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
