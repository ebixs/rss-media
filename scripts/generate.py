"""Generate the AI background for every post that has no final image yet,
then compose the branded final image.

Runs in GitHub Actions. Needs two repository secrets:
    CF_ACCOUNT_ID   Cloudflare account id
    CF_API_TOKEN    Cloudflare API token with the "Workers AI" permission

Each post lives in posts/<slug>/post.md with a header like:

    ---
    publish_at: 2026-10-13T20:30:00+03:30
    service: پانسمان سوختگی
    headline: ...
    subline: ...
    image_prompt: English scene description (no text in the image)
    ---
    caption ...

Results per post: background.jpg, final.jpg and status.json
({"ok": true/false, "error": "...", "model": "..."}). Nothing secret is printed.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
MODEL = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

STYLE = (
    "Editorial healthcare brand-campaign photograph, photorealistic, natural soft daylight, "
    "calm premium colour palette of deep navy, ivory white and soft natural medical green with "
    "a subtle indigo accent, clean modern upscale Tehran apartment interior, shallow depth of "
    "field, 50mm lens, realistic skin and hands, natural faces, Iranian people; any woman wears a "
    "chic, modern, loosely draped hijab or elegant scarf (never a tight white wrap), "
    "professional nurse in a well-fitted navy medical uniform, uncluttered composition with calm "
    "empty space in the lower half for a headline, absolutely no text, no letters, no logos, "
    "no watermark, no signage."
)

sys.path.insert(0, str(ROOT / "scripts"))
from compose import compose, read_header  # noqa: E402


def call_model(prompt: str) -> bytes:
    account = os.environ["CF_ACCOUNT_ID"]
    token = os.environ["CF_API_TOKEN"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}"
    body = json.dumps({"prompt": prompt[:2048], "steps": 8}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as err:
        raw = err.read() or b"{}"
        try:
            errors = json.loads(raw).get("errors", [])
            detail = "; ".join(e.get("message", "") for e in errors) or raw[:200].decode("utf-8", "replace")
        except ValueError:
            detail = raw[:200].decode("utf-8", "replace")
        raise RuntimeError(f"Cloudflare HTTP {err.code}: {detail}") from None
    except urllib.error.URLError as err:
        raise RuntimeError(f"Network error: {err.reason}") from None
    image = (payload.get("result") or {}).get("image")
    if not payload.get("success", True) or not image:
        raise RuntimeError(f"Cloudflare returned no image: {str(payload.get('errors'))[:200]}")
    return base64.b64decode(image)


def process(post_dir: pathlib.Path) -> dict:
    meta = read_header(post_dir / "post.md")
    prompt = meta.get("image_prompt", "").strip()
    if not prompt:
        return {"ok": False, "error": "image_prompt is missing in post.md"}
    data = call_model(f"{prompt}. {STYLE}")
    (post_dir / "background.jpg").write_bytes(data)
    compose(post_dir)
    return {"ok": True, "model": MODEL}


def main() -> int:
    for var in ("CF_ACCOUNT_ID", "CF_API_TOKEN"):
        if not os.environ.get(var):
            print(f"::error title=Config::secret {var} is missing")
            return 1
    failures = 0
    for post_md in sorted(POSTS.glob("*/post.md")):
        post_dir = post_md.parent
        status_file = post_dir / "status.json"
        if (post_dir / "final.jpg").exists() and not (post_dir / "REGENERATE").exists():
            continue
        (post_dir / "REGENERATE").unlink(missing_ok=True)
        try:
            status = process(post_dir)
        except Exception as err:  # keep going with the next post
            status = {"ok": False, "error": str(err)[:400], "model": MODEL}
        status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{post_dir.name}: {status}")
        if not status.get("ok"):
            failures += 1
            print(f"::error title={post_dir.name}::{status.get('error')}")
    print(f"done, failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
