"""Motion-graphics reel: 15 s, 1080x1920, 30 fps, with original music.

    python scripts/reel_motion.py posts/<slug>/

Same inputs as scripts/reel.py (post.md header scene_1..3, scene_sub_2/3, service;
background-1..3.jpg). The picture is an HTML/CSS animation rendered frame by frame
in headless Chromium (so Persian text is shaped perfectly), then encoded with
ffmpeg together with a music bed made by scripts/music.py.

Motion: slow camera push and drift on every photo, circular wipes between scenes,
a light sweep, words rising in one by one, floating light particles, a story-style
progress bar, and an animated end card (logo pop + pulse ring, phone pill with a
shine). Writes reel.mp4, cover.jpg and frame-1..4.jpg (review stills).
"""
from __future__ import annotations

import html
import pathlib
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from compose import BRAND_FA, HANDLE, LOGO, PHONE, read_header  # noqa: E402
import music  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
W, H, FPS = 1080, 1920, 30
STARTS = [0.0, 3.8, 7.4, 11.0]   # scene 1, 2, 3, end card
TOTAL = 15.0
WIPE = 0.55


def words(text: str, t0: float, cls: str, step: float = 0.09) -> tuple[str, float]:
    out, t = [], t0
    for w in text.split():
        out.append(f'<span class="w {cls}" style="animation-delay:{t:.2f}s">{html.escape(w)}</span>')
        t += step
    return " ".join(out), t


def page(meta: dict, imgs: list[pathlib.Path], seed: int) -> str:
    rnd = random.Random(seed)
    service = html.escape(meta.get("service", "").strip())
    scenes = []
    for i in range(3):
        s = STARTS[i]
        dur = STARTS[i + 1] - s + WIPE
        line = meta.get(f"scene_{i + 1}", "").strip()
        sub = meta.get(f"scene_sub_{i + 1}", "").strip()
        big, t_end = words(line, s + (0.25 if i == 0 else 0.45), "big")
        sub_html = ""
        if sub:
            sw, _ = words(sub, t_end + 0.15, "sub", 0.05)
            sub_html = f'<div class="subline">{sw}</div>'
        chip = (f'<div class="chip" style="animation-delay:{s + 0.15:.2f}s">{service}</div>'
                if i == 0 and service else "")
        dx = [-40, 40, -30][i]
        enter = "" if i == 0 else f"animation: wipe {WIPE}s cubic-bezier(.7,0,.2,1) {s:.2f}s both;"
        scenes.append(f"""
<div class="scene" style="z-index:{10 + i};{enter}">
  <div class="photo" style="background-image:url('{imgs[i].as_uri()}');
       --dx:{dx}px; animation: kb{i} {dur:.2f}s cubic-bezier(.25,.1,.25,1) {s:.2f}s both;"></div>
  <div class="shade"></div>
  <div class="sweep" style="animation-delay:{s + 0.35:.2f}s"></div>
  <div class="text">
    {chip}
    <div class="bar" style="animation-delay:{s + 0.2:.2f}s"></div>
    <div class="line">{big}</div>
    {sub_html}
  </div>
</div>""")
    kb = "\n".join(
        f"@keyframes kb{i} {{ from {{ transform: scale(1.20) translateX(calc(var(--dx) * -1)); }} "
        f"to {{ transform: scale(1.04) translateX(var(--dx)); }} }}" for i in range(3))
    particles = []
    for k in range(18):
        x, size = rnd.uniform(4, 96), rnd.uniform(4, 11)
        dur, delay = rnd.uniform(6, 11), -rnd.uniform(0, 10)
        op = rnd.uniform(.25, .7)
        particles.append(f'<i class="p" style="left:{x:.1f}%;width:{size:.1f}px;height:{size:.1f}px;'
                         f'opacity:{op:.2f};animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s"></i>')
    e = STARTS[3]
    brand_words, t = words(BRAND_FA, e + 0.75, "eb", 0.12)
    logo = f'<img class="logo" src="{LOGO.as_uri()}" style="animation-delay:{e + 0.35:.2f}s">' if LOGO.is_file() else ""
    return f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><style>
@font-face {{ font-family: V; font-weight: 500; src: url('{(FONTS / "Vazirmatn-Medium.ttf").as_uri()}'); }}
@font-face {{ font-family: V; font-weight: 700; src: url('{(FONTS / "Vazirmatn-Bold.ttf").as_uri()}'); }}
@font-face {{ font-family: V; font-weight: 900; src: url('{(FONTS / "Vazirmatn-Black.ttf").as_uri()}'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #0F2D4A; font-family: V, sans-serif; }}
.stage {{ position: absolute; inset: 0; overflow: hidden; }}
.scene {{ position: absolute; inset: 0; overflow: hidden; }}
.photo {{ position: absolute; inset: -2%; background-size: cover; background-position: center 30%; will-change: transform; }}
{kb}
@keyframes wipe {{ from {{ clip-path: circle(0% at 78% 62%); filter: brightness(1.5); }} to {{ clip-path: circle(150% at 78% 62%); filter: brightness(1); }} }}
.shade {{ position: absolute; inset: 0; background:
  linear-gradient(180deg, rgba(15,45,74,.55) 0%, rgba(15,45,74,0) 18%, rgba(15,45,74,0) 42%, rgba(15,45,74,.80) 70%, rgba(15,45,74,.95) 100%); }}
.sweep {{ position: absolute; top: -10%; bottom: -10%; width: 38%; left: 110%;
  background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,240,210,.35), rgba(255,255,255,0));
  transform: skewX(-18deg); mix-blend-mode: screen; animation: sweep 1.3s ease-in-out both; }}
@keyframes sweep {{ from {{ left: 110%; }} to {{ left: -60%; }} }}
.text {{ position: absolute; right: 84px; left: 84px; bottom: 520px; text-align: right; }}
.line {{ color: #FAF7F0; font-weight: 900; font-size: 92px; line-height: 1.3; text-wrap: balance; text-shadow: 0 6px 30px rgba(0,0,0,.35); }}
.subline {{ margin-top: 26px; color: #E2E8F0; font-weight: 500; font-size: 46px; line-height: 1.5; text-wrap: balance; }}
.w {{ display: inline-block; animation: rise .7s cubic-bezier(.2,.8,.2,1) both; }}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(46px) scale(.96); filter: blur(10px); }} to {{ opacity: 1; transform: none; filter: blur(0); }} }}
.bar {{ position: absolute; right: -30px; top: 18px; width: 10px; height: 0; border-radius: 6px; background: #8A90FF;
  box-shadow: 0 0 22px #5458DA; animation: grow .6s cubic-bezier(.2,.8,.2,1) both; }}
@keyframes grow {{ to {{ height: calc(100% - 30px); }} }}
.chip {{ display: inline-block; margin-bottom: 30px; padding: 12px 32px; border-radius: 40px; background: #CDE8D6; color: #0F2D4A;
  font-weight: 700; font-size: 38px; animation: pop .55s cubic-bezier(.34,1.56,.64,1) both; }}
@keyframes pop {{ from {{ opacity: 0; transform: scale(.4); }} to {{ opacity: 1; transform: scale(1); }} }}
.brand {{ position: absolute; z-index: 30; top: 120px; right: 84px; padding: 12px 30px; border-radius: 40px;
  background: rgba(15,45,74,.62); backdrop-filter: blur(8px); color: #FAF7F0; font-weight: 700; font-size: 36px;
  border: 1px solid rgba(255,255,255,.18); animation: slidein .7s cubic-bezier(.2,.8,.2,1) .15s both; }}
@keyframes slidein {{ from {{ opacity: 0; transform: translateX(80px); }} to {{ opacity: 1; transform: none; }} }}
.progress {{ position: absolute; z-index: 40; top: 64px; left: 84px; right: 84px; height: 7px; border-radius: 4px; background: rgba(255,255,255,.22); overflow: hidden; }}
.progress b {{ display: block; height: 100%; width: 100%; background: linear-gradient(90deg, #CDE8D6, #8A90FF); transform-origin: right;
  animation: prog {TOTAL}s linear both; }}
@keyframes prog {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
.p {{ position: absolute; z-index: 25; bottom: -20px; border-radius: 50%; background: #FFE9C2; box-shadow: 0 0 14px #FFD58A;
  animation-name: float; animation-timing-function: linear; animation-iteration-count: infinite; }}
@keyframes float {{ from {{ transform: translateY(0); }} to {{ transform: translateY(-2000px); }} }}
.end {{ position: absolute; inset: 0; z-index: 35; background: radial-gradient(circle at 50% 38%, #24508A 0%, #0F2D4A 55%, #0A2038 100%);
  animation: wipe {WIPE}s cubic-bezier(.7,0,.2,1) {e:.2f}s both; display: flex; flex-direction: column; align-items: center; padding-top: 360px; }}
.ring {{ position: absolute; top: 330px; left: 50%; width: 330px; height: 330px; margin-left: -165px; border-radius: 50%;
  border: 4px solid rgba(138,144,255,.7); animation: ring 1.6s ease-out {e + 0.6:.2f}s 2 both; }}
@keyframes ring {{ from {{ opacity: .9; transform: scale(.8); }} to {{ opacity: 0; transform: scale(1.8); }} }}
.logo {{ width: 270px; height: 270px; border-radius: 50%; background: #fff; box-shadow: 0 0 60px rgba(138,144,255,.55);
  animation: logo .9s cubic-bezier(.34,1.56,.64,1) both; }}
@keyframes logo {{ from {{ opacity: 0; transform: scale(.3) rotate(-25deg); }} to {{ opacity: 1; transform: none; }} }}
.eb {{ }}
.ename {{ margin-top: 70px; color: #FAF7F0; font-weight: 900; font-size: 88px; }}
.etag {{ margin-top: 18px; color: #CDE8D6; font-weight: 500; font-size: 50px; animation: fadeup .7s ease {e + 1.25:.2f}s both; }}
@keyframes fadeup {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: none; }} }}
.phone {{ position: relative; overflow: hidden; margin-top: 70px; padding: 26px 70px; border-radius: 90px; background: #FAF7F0; color: #0F2D4A;
  font-weight: 900; font-size: 84px; direction: ltr; letter-spacing: 2px; animation: pop .7s cubic-bezier(.34,1.56,.64,1) {e + 1.55:.2f}s both; }}
.phone::after {{ content: ""; position: absolute; top: 0; bottom: 0; width: 120px; left: -200px; transform: skewX(-20deg);
  background: linear-gradient(90deg, rgba(255,255,255,0), rgba(138,144,255,.45), rgba(255,255,255,0)); animation: shine 1.1s ease-in-out {e + 2.3:.2f}s both; }}
@keyframes shine {{ from {{ left: -200px; }} to {{ left: 120%; }} }}
.ecta {{ margin-top: 40px; color: #FAF7F0; font-weight: 700; font-size: 46px; animation: fadeup .7s ease {e + 2.0:.2f}s both; }}
.ehours {{ margin-top: 18px; color: #E2E8F0; font-weight: 500; font-size: 42px; animation: fadeup .7s ease {e + 2.25:.2f}s both; }}
.ehandle {{ margin-top: 26px; color: #CDE8D6; font-weight: 700; font-size: 40px; direction: ltr; animation: fadeup .7s ease {e + 2.5:.2f}s both; }}
</style></head><body><div class="stage">
{''.join(scenes)}
<div class="brand">{html.escape(BRAND_FA)}</div>
{''.join(particles)}
<div class="end"><div class="ring"></div>{logo}
  <div class="ename">{brand_words}</div>
  <div class="etag">پرستار و پزشک در منزل</div>
  <div class="phone">{PHONE}</div>
  <div class="ecta">برای هماهنگی تماس بگیرید</div>
  <div class="ehours">هر روز ۷ صبح تا ۱۱ شب</div>
  <div class="ehandle">{HANDLE}</div>
</div>
<div class="progress"><b></b></div>
</div>
{''.join(f'<img src="{i.as_uri()}" style="display:none">' for i in imgs)}
</body></html>"""


def build(post_dir: pathlib.Path) -> pathlib.Path:
    from playwright.sync_api import sync_playwright

    meta = read_header(post_dir / "post.md")
    if not all(meta.get(f"scene_{n}", "").strip() for n in (1, 2, 3)):
        raise SystemExit("scene_1, scene_2 and scene_3 are required for a reel")
    imgs = [(post_dir / f"background-{n}.jpg").resolve() for n in (1, 2, 3)]
    seed = sum(map(ord, post_dir.name)) % 1000
    out = post_dir / "reel.mp4"
    stills = {round(2.9 * FPS): "frame-1.jpg", round(6.6 * FPS): "frame-2.jpg",
              round(10.3 * FPS): "frame-3.jpg", round(14.2 * FPS): "frame-4.jpg"}
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        (t / "reel.html").write_text(page(meta, imgs, seed), encoding="utf-8")
        music.save(str(t / "music.wav"), music.make(TOTAL, seed, STARTS[3]))
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
             "-i", str(t / "music.wav"), "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-b:v", "7M", "-maxrate", "9M", "-bufsize", "14M", "-c:a", "aac", "-b:a", "160k",
             "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            pg.goto((t / "reel.html").as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_function("Array.from(document.images).every(i => i.complete)")
            pg.wait_for_timeout(300)
            pg.evaluate("document.getAnimations().forEach(a => a.pause())")
            for f in range(int(TOTAL * FPS)):
                ms = f * 1000 / FPS
                pg.evaluate(f"document.getAnimations().forEach(a => a.currentTime = {ms})")
                shot = pg.screenshot(type="jpeg", quality=92)
                enc.stdin.write(shot)
                if f in stills:
                    (post_dir / stills[f]).write_bytes(shot)
            browser.close()
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
    (post_dir / "cover.jpg").write_bytes((post_dir / "frame-1.jpg").read_bytes())
    return out


if __name__ == "__main__":
    print(build(pathlib.Path(sys.argv[1])))
