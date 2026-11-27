"""«یک مفهوم» concept reels: one health idea explained precisely on a clean white set,
with real-colour product photos (from characters/out) and exact, code-drawn motion on top
(falling drops, highlight rings, ticks). Brand colours only on the end card.

    python scripts/reel_concept.py posts/<folder>/concept.json posts/<folder>/reel.mp4

concept.json:
{
  "total": 28.5, "end_at": 25.0, "seed": 11,
  "images": {"chamber": "characters/out/concept-serum-chamber-131.jpg", ...},
  "anchors": {"chamber": {"tip": [0.494, 0.305], "surface": 0.525, "walls": [0.34, 0.66]}},
  "beats": [
    {"kind": "hero", "start": 0, "end": 3.2, "image": "chamber", "drops": 0.35, "text": "..."},
    {"kind": "focus", "start": .., "end": .., "image": "set", "ring": [x, y, r], "label": "...", "big": "نه.", "text": "..."},
    {"kind": "compare", ..., "image": "chamber", "left": {"label": "...", "ok": true, "drops": 1.6},
                                                 "right": {"label": "...", "ok": false, "drops": 0.3}, "text": "..."},
    {"kind": "checklist", ..., "title": "...", "items": ["..."], "alarm": "...", "step": 1.6},
    {"kind": "takeaway", ..., "text": "..."}
  ],
  "end": {"tag": "پرستار در منزل", "phone": "۰۹۱۹۰۴۲۳۴۰۰"}
}
Fractions in anchors/ring are of the source image (0..1). Every frame is rendered from
CSS animations paused at an exact time, so motion is deterministic and frame-accurate.
"""
from __future__ import annotations

import base64, json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import music  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONTS = ROOT / "assets" / "fonts"
INK, MUTED, OK, BAD, NAVY = "#1B2430", "#5B6675", "#15803D", "#C62828", "#0F2D4A"


def data_uri(path: pathlib.Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def fade(start: float, end: float) -> str:
    d = end - start
    return f"animation: show {d:.3f}s linear {start:.3f}s both;"


def drops(box_w: float, box_h: float, a: dict, period: float, t0: float, t1: float, n_max: int = 40) -> str:
    """Drops forming at the needle tip and falling to the liquid surface, every `period` s."""
    x = a["tip"][0] * box_w
    y0, y1 = a["tip"][1] * box_h, a["surface"] * box_h
    fall = min(0.5, period * 0.55)
    out = []
    k = 0
    t = t0
    while t < t1 and k < n_max:
        out.append(f'<i class="drop" style="left:{x - 13:.1f}px; top:{y0:.1f}px; --fall:{y1 - y0 - 18:.1f}px;'
                    f' animation: drop {period:.3f}s linear {t:.3f}s both;"></i>'
                    f'<i class="ripple" style="left:{x - 40:.1f}px; top:{y1 - 10:.1f}px;'
                    f' animation: ripple {period:.3f}s linear {t:.3f}s both;"></i>')
        t += period
        k += 1
    # keyframe timing inside one period: grow 0-55%, fall 55-55+fall, gone after
    return "".join(out)


def img_box(src: str, left: float, top: float, w: float, a_img: tuple[int, int]) -> tuple[str, float]:
    h = w * a_img[1] / a_img[0]
    return f'<img class="ph" src="{src}" style="left:{left:.1f}px; top:{top:.1f}px; width:{w:.1f}px; height:{h:.1f}px;">', h


def beat_html(b: dict, imgs: dict, sizes: dict, anchors: dict) -> str:
    s, e = b["start"], b["end"]
    k = b["kind"]
    inner = ""
    if k == "hero":
        w = 760
        left, top = (W - w) / 2, 520
        im, h = img_box(imgs[b["image"]], 0, 0, w, sizes[b["image"]])
        inner += f'<div class="stage zoom" style="left:{left}px; top:{top}px; width:{w}px; height:{h:.1f}px; animation-delay:{s}s; animation-duration:{e - s}s;">{im}'
        inner += drops(w, h, anchors[b["image"]], b["drops"], s, e) + "</div>"
        inner += f'<p class="hook" style="{fade(s, e)}">{b["text"]}</p>'
    elif k == "focus":
        w = 560
        left, top = (W - w) / 2, 600
        im, h = img_box(imgs[b["image"]], 0, 0, w, sizes[b["image"]])
        rx, ry, rr = b["ring"]
        inner += f'<div class="stage" style="left:{left}px; top:{top}px; width:{w}px; height:{h:.1f}px;">{im}'
        inner += (f'<i class="ring" style="left:{rx * w - rr * w:.1f}px; top:{ry * h - rr * w:.1f}px; width:{2 * rr * w:.1f}px;'
                  f' height:{2 * rr * w:.1f}px; animation: ring 1.6s ease-out {s + 0.8:.2f}s infinite both;"></i>')
        inner += (f'<span class="tag" style="top:{ry * h - 34:.1f}px; right:{w - rx * w + rr * w + 24:.1f}px;'
                  f' animation: pop .5s ease {s + 1.0:.2f}s both;">{b["label"]}</span></div>')
        if b.get("big"):
            inner += f'<p class="big" style="animation: pop .45s ease {s + .1:.2f}s both;">{b["big"]}</p>'
        inner += f'<p class="cap" style="animation: up .5s ease {s + .4:.2f}s both;">{b["text"]}</p>'
    elif k == "compare":
        w = 440
        tops = 470
        for side, x in (("right", W - 60 - w), ("left", 60)):  # RTL: right panel first
            c = b[side]
            im, h = img_box(imgs[b["image"]], 0, 0, w, sizes[b["image"]])
            col = OK if c["ok"] else BAD
            inner += (f'<div class="stage panel" style="left:{x}px; top:{tops}px; width:{w}px; height:{h:.1f}px;'
                      f' border-color:{col}; animation: up .5s ease {s + (0 if side == "right" else .25):.2f}s both;">{im}')
            inner += drops(w, h, anchors[b["image"]], c["drops"], s, e) + "</div>"
            inner += (f'<p class="plabel" style="left:{x}px; width:{w}px; top:{tops - 96}px; color:{col};'
                      f' animation: up .5s ease {s + (0 if side == "right" else .25):.2f}s both;">'
                      f'<b class="mark" style="background:{col}">{"✓" if c["ok"] else "✕"}</b>{c["label"]}</p>')
        inner += f'<p class="cap low" style="animation: up .5s ease {s + .9:.2f}s both;">{b["text"]}</p>'
    elif k == "checklist":
        inner += f'<p class="ctitle" style="animation: up .5s ease {s + .1:.2f}s both;">{b["title"]}</p><ul class="clist">'
        for i, it in enumerate(b["items"]):
            inner += f'<li style="animation: up .45s ease {s + .5 + i * b["step"]:.2f}s both;"><b class="mark" style="background:{INK}">{i + 1}</b>{it}</li>'
        inner += "</ul>"
        if b.get("alarm"):
            t = s + .5 + len(b["items"]) * b["step"]
            inner += f'<p class="alarm" style="animation: pop .45s ease {t:.2f}s both;">{b["alarm"]}</p>'
    elif k == "takeaway":
        inner += f'<p class="take" style="animation: pop .6s ease {s + .1:.2f}s both;">{b["text"]}</p>'
    return f'<section class="beat" style="{fade(s, e)}">{inner}</section>'


def page(sc: dict) -> str:
    imgs, sizes = {}, {}
    from PIL import Image
    for k, rel in sc["images"].items():
        p = ROOT / rel
        imgs[k] = data_uri(p)
        sizes[k] = Image.open(p).size
    beats = "".join(beat_html(b, imgs, sizes, sc.get("anchors", {})) for b in sc["beats"])
    e = sc["end_at"]
    logo = "data:image/png;base64," + base64.b64encode((ROOT / "assets" / "logo.png").read_bytes()).decode()
    end = sc["end"]
    return f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><style>
@font-face {{ font-family: V; font-weight: 500; src: url('{(FONTS / "Vazirmatn-Medium.ttf").as_uri()}'); }}
@font-face {{ font-family: V; font-weight: 700; src: url('{(FONTS / "Vazirmatn-Bold.ttf").as_uri()}'); }}
@font-face {{ font-family: V; font-weight: 900; src: url('{(FONTS / "Vazirmatn-Black.ttf").as_uri()}'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #FFFFFF; font-family: V, sans-serif; color: {INK}; }}
.beat {{ position: absolute; inset: 0; }}
.stage {{ position: absolute; }}
.ph {{ position: absolute; display: block; mix-blend-mode: multiply; }}
.zoom {{ animation-name: zoom; animation-timing-function: linear; animation-fill-mode: both; transform-origin: 50% 30%; }}
.panel {{ border: 6px solid; border-radius: 34px; overflow: hidden; background: #fff; }}
.drop {{ position: absolute; width: 26px; height: 36px; border-radius: 50% 50% 50% 50% / 62% 62% 38% 38%;
  background: radial-gradient(circle at 35% 30%, #ffffff 0 18%, #cfe4f5 40%, #8fb6d8 75%, #6d9cc6);
  border: 2px solid rgba(60,100,140,.75); box-shadow: 0 2px 6px rgba(40,80,120,.35); opacity: 0; transform-origin: 50% 0; }}
.ripple {{ position: absolute; width: 80px; height: 20px; border-radius: 50%; border: 4px solid rgba(70,115,160,.8); opacity: 0; }}
.ring {{ position: absolute; border-radius: 50%; border: 7px solid {OK}; }}
.tag {{ position: absolute; white-space: nowrap; background: {INK}; color: #fff; font-weight: 700; font-size: 40px; padding: 10px 26px; border-radius: 40px; }}
.hook {{ position: absolute; top: 170px; right: 80px; left: 80px; text-align: center; font-weight: 900; font-size: 74px; line-height: 1.45; text-wrap: balance; }}
.big {{ position: absolute; top: 150px; width: 100%; text-align: center; font-weight: 900; font-size: 150px; color: {BAD}; }}
.cap {{ position: absolute; top: 360px; right: 90px; left: 90px; text-align: center; font-weight: 700; font-size: 54px; line-height: 1.55; text-wrap: balance; }}
.cap.low {{ top: auto; bottom: 150px; font-size: 50px; color: {INK}; }}
.plabel {{ position: absolute; text-align: center; font-weight: 900; font-size: 50px; display: flex; gap: 16px; justify-content: center; align-items: center; }}
.mark {{ flex: 0 0 auto; width: 66px; height: 66px; border-radius: 50%; color: #fff; font-size: 40px; display: inline-flex; align-items: center; justify-content: center; font-weight: 900; }}
.ctitle {{ position: absolute; top: 330px; right: 100px; left: 100px; font-weight: 900; font-size: 72px; }}
.clist {{ position: absolute; top: 520px; right: 100px; left: 100px; list-style: none; }}
.clist li {{ display: flex; gap: 28px; align-items: center; font-weight: 700; font-size: 56px; line-height: 1.45; margin-bottom: 64px; }}
.alarm {{ position: absolute; top: 1240px; right: 100px; left: 100px; padding: 40px 44px; border-radius: 34px; background: #FDECEC; color: {BAD};
  font-weight: 900; font-size: 60px; line-height: 1.45; text-align: center; border: 5px solid {BAD}; }}
.take {{ position: absolute; top: 760px; right: 90px; left: 90px; text-align: center; font-weight: 900; font-size: 84px; line-height: 1.5; text-wrap: balance; }}
.endc {{ position: absolute; inset: 0; background: {NAVY}; display: flex; flex-direction: column; align-items: center; justify-content: center; {fade(e, sc["total"] + 1)} }}
.endc img {{ width: 300px; height: 300px; border-radius: 50%; animation: pop .6s ease {e + .2:.2f}s both; }}
.ename {{ margin-top: 60px; color: #fff; font-weight: 900; font-size: 86px; animation: up .6s ease {e + .5:.2f}s both; }}
.etag {{ margin-top: 16px; color: #C9CCFF; font-weight: 500; font-size: 50px; animation: up .6s ease {e + .7:.2f}s both; }}
.phone {{ margin-top: 70px; padding: 24px 70px; border-radius: 90px; background: #fff; color: {NAVY}; font-weight: 900; font-size: 80px; direction: ltr; animation: pop .6s ease {e + 1:.2f}s both; }}
@keyframes show {{ 0% {{ opacity: 0; }} 4% {{ opacity: 1; }} 96% {{ opacity: 1; }} 100% {{ opacity: 0; }} }}
@keyframes zoom {{ from {{ transform: scale(1); }} to {{ transform: scale(1.08); }} }}
@keyframes up {{ from {{ opacity: 0; transform: translateY(40px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pop {{ 0% {{ opacity: 0; transform: scale(.8); }} 70% {{ opacity: 1; transform: scale(1.04); }} 100% {{ opacity: 1; transform: none; }} }}
@keyframes ring {{ 0% {{ opacity: .9; transform: scale(.85); }} 100% {{ opacity: 0; transform: scale(1.35); }} }}
@keyframes drop {{
  0% {{ opacity: 0; transform: translateY(0) scale(.2, .2); }}
  8% {{ opacity: 1; }}
  50% {{ opacity: 1; transform: translateY(0) scale(1, 1.12); }}
  56% {{ opacity: 1; transform: translateY(6px) scale(.92, 1.08); }}
  80% {{ opacity: 1; transform: translateY(var(--fall)) scale(.92, 1.08); }}
  81%, 100% {{ opacity: 0; transform: translateY(var(--fall)) scale(.9, 1); }} }}
@keyframes ripple {{ 0%, 79% {{ opacity: 0; transform: scale(.3); }} 82% {{ opacity: .9; }} 100% {{ opacity: 0; transform: scale(1.2); }} }}
</style></head><body>
{beats}
<div class="endc"><img src="{logo}" alt=""><p class="ename">رامان سلامت سهیل</p><p class="etag">{end["tag"]}</p><p class="phone">{end["phone"]}</p></div>
</body></html>"""


def build(sc: dict, out: pathlib.Path, stills: dict | None = None) -> pathlib.Path:
    from playwright.sync_api import sync_playwright
    total = sc["total"]
    stills = stills or {}
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        (t / "reel.html").write_text(page(sc), encoding="utf-8")
        audio = music.make(total, sc.get("seed", 11), sc["end_at"]) * 0.8
        music.save(str(t / "audio.wav"), audio)
        part = out.with_name(out.stem + ".part.mp4")
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
             "-i", str(t / "audio.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
             "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS), "-b:v", "7M", "-maxrate", "9M", "-bufsize", "14M",
             "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(part)], stdin=subprocess.PIPE)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            pg.goto((t / "reel.html").as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_function("Array.from(document.images).every(i => i.complete)")
            pg.wait_for_timeout(300)
            pg.evaluate("document.getAnimations().forEach(a => a.pause())")
            for f in range(int(round(total * FPS))):
                pg.evaluate(f"document.getAnimations().forEach(a => a.currentTime = {f * 1000 / FPS})")
                shot = pg.screenshot(type="jpeg", quality=92)
                enc.stdin.write(shot)
                if f in stills:
                    pathlib.Path(stills[f]).write_bytes(shot)
            browser.close()
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
        part.replace(out)
    return out


if __name__ == "__main__":
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    sc = json.loads(src.read_text(encoding="utf-8"))
    times = [b["start"] + (b["end"] - b["start"]) * .75 for b in sc["beats"]] + [sc["total"] - .3]
    stills = {int(x * FPS): str(dst.with_name(f"frame-{i + 1}.jpg")) for i, x in enumerate(times)}
    build(sc, dst, stills)
    print("ok", dst)
