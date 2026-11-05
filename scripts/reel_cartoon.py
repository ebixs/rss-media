"""Cartoon dialogue reel: the brand characters (مهتاب، ابراهیم، خونه‌جان) move, react and
talk to each other in comic speech bubbles, over soft drawn backgrounds, with music and
sound effects. 1080x1920, 30 fps, free (no image quota needed).

    python scripts/reel_cartoon.py <script.json> <out.mp4>

script.json:
{
  "scenes": [
    {"start": 0, "end": 4.6, "bg": "street" | "door" | "room",
     "actors": [{"name": "khonejan", "x": 540, "h": 900, "enter": "pop"|"walk-left"|"walk-right"|"none",
                 "at": 0.2, "mood": "worried"|"happy"}],
     "lines": [{"who": "khonejan", "text": "...", "at": 0.7, "dur": 3.4}],
     "sfx": [{"kind": "ding"|"pop"|"whoosh", "at": 6.0}]}
  ],
  "end_at": 12.0, "total": 15.0, "seed": 3
}
Character cut-outs come from characters/cut/<name>.png (made by scripts/cutouts.py).
"""
from __future__ import annotations

import html
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from compose import BRAND_FA, HANDLE, LOGO, PHONE  # noqa: E402
import music  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
CUT = ROOT / "characters" / "cut"
W, H, FPS = 1080, 1920, 30
FLOOR = 1520            # feet line, clear of Instagram's caption area

BACKGROUNDS = {
    "street": """
<div class="bg" style="background:linear-gradient(180deg,#2B3F73 0%,#6C6FA8 38%,#E8A97E 70%,#F4D1A6 100%)">
 <svg viewBox="0 0 1080 1920" preserveAspectRatio="none">
  <path d="M0 980 L180 760 L330 900 L520 700 L700 880 L860 740 L1080 940 V1920 H0Z" fill="#8E86B5" opacity=".55"/>
  <g fill="#3A3F6B"><rect x="-20" y="900" width="300" height="760" rx="18"/><rect x="760" y="860" width="360" height="800" rx="18"/>
   <rect x="300" y="1060" width="200" height="600" rx="14"/><rect x="560" y="1000" width="220" height="660" rx="14"/></g>
  <g fill="#FFD58A">%WINDOWS%</g>
  <rect x="0" y="1500" width="1080" height="420" fill="#4A4E7E"/><rect x="0" y="1500" width="1080" height="16" fill="#6A6FA0"/>
  <g fill="#2E5A44"><circle cx="120" cy="880" r="120"/><circle cx="980" cy="840" r="140"/></g>
 </svg></div>""",
    "door": """
<div class="bg" style="background:linear-gradient(180deg,#F3E6D3 0%,#EAD7BE 60%,#D9C2A3 100%)">
 <svg viewBox="0 0 1080 1920" preserveAspectRatio="none">
  <rect x="330" y="560" width="420" height="960" rx="200" fill="#8A5A3B"/>
  <rect x="360" y="590" width="360" height="930" rx="180" fill="#A06A45"/>
  <circle cx="680" cy="1080" r="16" fill="#E6C27A"/>
  <rect x="790" y="900" width="70" height="110" rx="14" fill="#CDE8D6"/><circle cx="825" cy="955" r="18" fill="#0F2D4A"/>
  <g fill="#FFE2A8" opacity=".9"><circle cx="230" cy="700" r="46"/><circle cx="850" cy="700" r="46"/></g>
  <g fill="#3E7A58"><ellipse cx="170" cy="1400" rx="120" ry="150"/><ellipse cx="930" cy="1420" rx="110" ry="140"/></g>
  <g fill="#C26B4A"><rect x="110" y="1440" width="120" height="90" rx="12"/><rect x="870" y="1450" width="110" height="80" rx="12"/></g>
  <rect x="0" y="1520" width="1080" height="400" fill="#B99A78"/><rect x="250" y="1500" width="580" height="40" rx="10" fill="#CDB394"/>
 </svg></div>""",
    "room": """
<div class="bg" style="background:linear-gradient(180deg,#E6F1EA 0%,#D4E7DC 70%,#BFD7C9 100%)">
 <svg viewBox="0 0 1080 1920" preserveAspectRatio="none">
  <rect x="120" y="420" width="380" height="520" rx="24" fill="#FFFFFF" opacity=".75"/><rect x="140" y="440" width="340" height="480" rx="18" fill="#BFE0F2"/>
  <rect x="640" y="760" width="320" height="420" rx="30" fill="#0F2D4A" opacity=".85"/>
  <rect x="0" y="1520" width="1080" height="400" fill="#A9C7B5"/>
 </svg></div>""",
}


def windows(seed: int) -> str:
    rng = np.random.default_rng(seed)
    out = []
    for bx, by, bw, bh in ((20, 960, 240, 640), (790, 920, 300, 680), (320, 1110, 160, 500), (580, 1050, 180, 560)):
        for wy in range(by, by + bh - 80, 110):
            for wx in range(bx, bx + bw - 40, 70):
                if rng.random() < 0.55:
                    out.append(f'<rect x="{wx}" y="{wy}" width="38" height="52" rx="6" opacity="{rng.uniform(.55, 1):.2f}"/>')
    return "".join(out)


def typed(text: str, at: float, dur: float) -> str:
    """Words appear one by one over ~45% of the line's time (typewriter feel, RTL-safe)."""
    ws = text.split()
    span = min(dur * 0.45, 0.12 * len(ws) + 0.3)
    step = span / max(1, len(ws))
    return " ".join(f'<span class="tw" style="animation-delay:{at + 0.15 + i * step:.2f}s">{html.escape(w)}</span>'
                    for i, w in enumerate(ws))


def actor_html(a: dict, sc: dict, speaking: list[tuple[float, float]]) -> str:
    img = (CUT / f"{a['name']}.png").resolve()
    h, x, at = a.get("h", 900), a.get("x", 540), a.get("at", sc["start"])
    enter = a.get("enter", "none")
    anims = []
    if enter == "pop":
        anims.append(f"popin .7s cubic-bezier(.34,1.56,.64,1) {at:.2f}s both")
    elif enter in ("walk-left", "walk-right"):
        anims.append(f"{enter} 1.1s cubic-bezier(.25,.8,.3,1) {at:.2f}s both")
    else:
        anims.append(f"fadein .4s ease {at:.2f}s both")
    idle = f"breathe 2.4s ease-in-out {at:.2f}s {int((sc['end'] - at) / 2.4) + 1}"
    mood = a.get("mood", "happy")
    talk = ", ".join(f"talk .22s ease-in-out {s:.2f}s {max(1, int(d / 0.22))}" for s, d in speaking)
    walk = f", bob .28s ease-in-out {at:.2f}s 4" if enter.startswith("walk") else ""
    tilt = f", worry 1.6s ease-in-out {at + 0.6:.2f}s 2" if mood == "worried" else ""
    happy = "".join(f", hop .5s cubic-bezier(.3,1.6,.5,1) {t:.2f}s 1" for t in a.get("hops", []))
    flip = "scaleX(-1)" if a.get("flip") else "none"
    return (f'<div class="actor" style="left:{x}px;height:{h}px;animation:{", ".join(anims)}">'
            f'<div class="inner" style="animation:{idle}{walk}{tilt}{happy}{"," + talk if talk else ""}">'
            f'<img src="{img.as_uri()}" style="height:{h}px;transform:{flip}"></div></div>')


def bubble_html(line: dict, actor: dict) -> str:
    x, h = actor.get("x", 540), actor.get("h", 900)
    top = FLOOR - h - 60
    side = "right" if x > W / 2 else "left"
    pos = f"right:{max(40, W - x - 260)}px" if side == "right" else f"left:{max(40, x - 260)}px"
    end = line["at"] + line["dur"]
    return (f'<div class="bubble {side}" style="{pos};bottom:{H - top}px;'
            f'animation:bin .35s cubic-bezier(.34,1.56,.64,1) {line["at"]:.2f}s both, bout .25s ease-in {end:.2f}s forwards">'
            f'{typed(line["text"], line["at"], line["dur"])}</div>')


ICONS = {
    "pill": '<svg viewBox="0 0 100 100"><rect x="18" y="38" width="64" height="26" rx="13" fill="#FAF7F0" stroke="#0F2D4A" stroke-width="5" transform="rotate(-30 50 51)"/><path d="M50 30v42" stroke="#0F2D4A" stroke-width="5" transform="rotate(-30 50 51)"/><rect x="50" y="38" width="32" height="26" rx="13" fill="#8A90FF" transform="rotate(-30 50 51)"/></svg>',
    "calendar": '<svg viewBox="0 0 100 100"><rect x="14" y="20" width="72" height="66" rx="12" fill="#FAF7F0" stroke="#0F2D4A" stroke-width="5"/><rect x="14" y="20" width="72" height="18" rx="8" fill="#E86A6A"/><g fill="#0F2D4A"><circle cx="34" cy="55" r="5"/><circle cx="50" cy="55" r="5"/><circle cx="66" cy="55" r="5"/><circle cx="34" cy="71" r="5"/><circle cx="50" cy="71" r="5"/></g></svg>',
    "clock": '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="38" fill="#FAF7F0" stroke="#0F2D4A" stroke-width="6"/><path d="M50 28v24l16 10" stroke="#0F2D4A" stroke-width="6" fill="none" stroke-linecap="round"/></svg>',
    "check": '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#3DBE7A"/><path d="M30 52l13 13 27-29" stroke="#fff" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "heart": '<svg viewBox="0 0 100 100"><path d="M50 84C22 64 10 50 10 34a20 20 0 0 1 40-6 20 20 0 0 1 40 6c0 16-12 30-40 50z" fill="#E86A6A"/></svg>',
    "phone": '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="42" fill="#3DBE7A"/><path d="M36 28c4 0 8 9 8 12s-5 4-5 6 9 15 15 15 3-5 6-5 12 4 12 8-6 10-12 10C42 74 26 58 26 40c0-6 6-12 10-12z" fill="#fff"/></svg>',
    "prescription": '<svg viewBox="0 0 100 100"><rect x="22" y="12" width="56" height="76" rx="8" fill="#FAF7F0" stroke="#0F2D4A" stroke-width="5"/><g stroke="#B8C2CC" stroke-width="5" stroke-linecap="round"><path d="M34 34h32"/><path d="M34 48h32"/><path d="M34 62h20"/></g><circle cx="64" cy="70" r="9" fill="#8A90FF"/></svg>',
}


def props_html(sc: dict) -> str:
    out = []
    for pr in sc.get("props", []):
        icon = ICONS.get(pr.get("icon", ""), "")
        if icon:
            out.append(f'<div class="prop" style="left:{pr.get("x", 540)}px;top:{pr.get("y", 700)}px;width:{pr.get("size", 150)}px;'
                       f'animation:propin .6s cubic-bezier(.34,1.56,.64,1) {pr["at"]:.2f}s both, floaty 2s ease-in-out {pr["at"] + .6:.2f}s 6">{icon}</div>')
    return "".join(out)


def checklist_html(sc: dict) -> str:
    """A card that ticks items off one by one (for 'what to prepare' moments)."""
    items = []
    for k, it in enumerate(sc["items"]):
        at = sc.get("items_at", sc["start"] + 0.9) + k * sc.get("items_step", 1.1)
        items.append(f'<li style="animation:fu .5s ease {at:.2f}s both"><span class="tick" style="animation:pp .5s cubic-bezier(.34,1.56,.64,1) {at + .35:.2f}s both">✓</span>{html.escape(it)}</li>')
    title = html.escape(sc.get("title", ""))
    return (f'<div class="card" style="animation:pp .6s cubic-bezier(.34,1.56,.64,1) {sc["start"] + .3:.2f}s both">'
            f'<h3>{title}</h3><ul>{"".join(items)}</ul></div>')


def bg_html(sc: dict, script: dict, i: int) -> str:
    img = sc.get("bg_image")
    if img and pathlib.Path(img).is_file():
        return f'<div class="bg photo" style="background-image:url(\'{pathlib.Path(img).resolve().as_uri()}\')"></div>'
    return BACKGROUNDS[sc.get("bg", "door")].replace("%WINDOWS%", windows(script.get("seed", 3) + i))


def page(script: dict) -> str:
    parts = []
    for i, sc in enumerate(script["scenes"]):
        bg = bg_html(sc, script, i)
        enter = "" if i == 0 else f"animation:wipe .5s cubic-bezier(.7,0,.2,1) {sc['start']:.2f}s both;"
        actors = {a["name"]: a for a in sc.get("actors", [])}
        body = []
        for a in sc.get("actors", []):
            sp = [(l["at"] + 0.15, l["dur"] * 0.5) for l in sc.get("lines", []) if l["who"] == a["name"]]
            body.append(actor_html(a, sc, sp))
        for l in sc.get("lines", []):
            body.append(bubble_html(l, actors[l["who"]]))
        body.append(props_html(sc))
        if sc.get("items"):
            body.append(checklist_html(sc))
        for s in sc.get("sfx", []):
            if s["kind"] == "ding":
                body.append(f'<div class="ding" style="animation:dingpop 1s ease-out {s["at"]:.2f}s both"><svg viewBox="0 0 100 100" width="130" height="130"><path d="M50 12c-16 0-26 13-26 30v18l-9 13h70l-9-13V42c0-17-10-30-26-30z" fill="#F6C343" stroke="#0F2D4A" stroke-width="5"/><circle cx="50" cy="82" r="8" fill="#0F2D4A"/></svg></div>')
        parts.append(f'<div class="scene" style="z-index:{10 + i};{enter}"><div class="cam" style="animation:cam {sc["end"] - sc["start"] + .5:.2f}s linear {sc["start"]:.2f}s both">{bg}</div>{"".join(body)}</div>')
    e, total = script["end_at"], script["total"]
    logo = f'<img class="logo" src="{LOGO.as_uri()}" style="animation-delay:{e + 0.35:.2f}s">' if LOGO.is_file() else ""
    return f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><style>
@font-face {{ font-family: V; font-weight: 500; src: url('{(FONTS / "Vazirmatn-Medium.ttf").as_uri()}'); }}
@font-face {{ font-family: V; font-weight: 700; src: url('{(FONTS / "Vazirmatn-Bold.ttf").as_uri()}'); }}
@font-face {{ font-family: V; font-weight: 900; src: url('{(FONTS / "Vazirmatn-Black.ttf").as_uri()}'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #0F2D4A; font-family: V, sans-serif; }}
.scene {{ position: absolute; inset: 0; overflow: hidden; }}
.cam {{ position: absolute; inset: -3%; }}
.bg {{ position: absolute; inset: 0; filter: blur(5px) saturate(1.05); }}
.bg.photo {{ background-size: cover; background-position: center 40%; filter: blur(2.5px) saturate(1.05) brightness(.97); }}
.prop {{ position: absolute; z-index: 45; filter: drop-shadow(0 10px 12px rgba(10,20,40,.3)); }}
.prop svg {{ width: 100%; height: auto; display: block; }}
@keyframes propin {{ from {{ opacity: 0; transform: scale(.2) rotate(-40deg); }} to {{ opacity: 1; transform: none; }} }}
@keyframes floaty {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-16px) rotate(4deg); }} }}
.card {{ position: absolute; z-index: 55; left: 90px; right: 90px; top: 330px; padding: 44px 50px; border-radius: 48px; background: rgba(250,247,240,.96);
  border: 5px solid #0F2D4A; box-shadow: 0 24px 50px rgba(10,20,40,.3); }}
.card h3 {{ color: #0F2D4A; font-weight: 900; font-size: 60px; margin-bottom: 26px; }}
.card ul {{ list-style: none; }}
.card li {{ color: #0F2D4A; font-weight: 700; font-size: 50px; line-height: 1.35; margin: 20px 0; display: flex; gap: 22px; align-items: center; }}
.tick {{ flex: 0 0 auto; width: 70px; height: 70px; border-radius: 50%; background: #3DBE7A; color: #fff; font-size: 46px; display: flex; align-items: center; justify-content: center; }}
.bg svg {{ width: 100%; height: 100%; display: block; }}
@keyframes cam {{ from {{ transform: scale(1.06) translateX(14px); }} to {{ transform: scale(1.0) translateX(-14px); }} }}
@keyframes wipe {{ from {{ clip-path: circle(0% at 50% 60%); }} to {{ clip-path: circle(150% at 50% 60%); }} }}
.actor {{ position: absolute; bottom: {H - FLOOR}px; transform: translateX(-50%); }}
.actor .inner {{ transform-origin: 50% 100%; }}
.actor img {{ display: block; filter: drop-shadow(0 26px 18px rgba(10,20,40,.35)); }}
@keyframes popin {{ from {{ opacity: 0; transform: translateX(-50%) translateY(120px) scale(.4); }} to {{ opacity: 1; transform: translateX(-50%) scale(1); }} }}
@keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes walk-left {{ from {{ transform: translateX(calc(-50% - 900px)); }} to {{ transform: translateX(-50%); }} }}
@keyframes walk-right {{ from {{ transform: translateX(calc(-50% + 900px)); }} to {{ transform: translateX(-50%); }} }}
@keyframes breathe {{ 0%,100% {{ transform: scale(1,1); }} 50% {{ transform: scale(1.012,.988); }} }}
@keyframes bob {{ 0%,100% {{ transform: translateY(0) rotate(-1.5deg); }} 50% {{ transform: translateY(-18px) rotate(1.5deg); }} }}
@keyframes talk {{ 0%,100% {{ transform: scale(1,1); }} 50% {{ transform: scale(1.02,1.035) translateY(-4px); }} }}
@keyframes worry {{ 0%,100% {{ transform: rotate(0); }} 25% {{ transform: rotate(-3deg); }} 75% {{ transform: rotate(3deg); }} }}
@keyframes hop {{ 0%,100% {{ transform: translateY(0) scale(1); }} 30% {{ transform: translateY(0) scale(1.06,.92); }} 60% {{ transform: translateY(-70px) scale(.97,1.04); }} }}
.bubble {{ position: absolute; z-index: 50; max-width: 760px; padding: 30px 40px; border-radius: 46px; background: #FFFFFF; color: #0F2D4A;
  font-weight: 800; font-size: 52px; line-height: 1.5; text-align: right; text-wrap: balance; box-shadow: 0 18px 40px rgba(10,20,40,.28); border: 5px solid #0F2D4A; }}
.bubble::after {{ content: ""; position: absolute; bottom: -42px; width: 0; height: 0; border: 22px solid transparent; border-top: 30px solid #0F2D4A; }}
.bubble.left::after {{ left: 120px; }} .bubble.right::after {{ right: 120px; }}
.tw {{ display: inline-block; animation: twin .25s ease-out both; }}
@keyframes twin {{ from {{ opacity: 0; transform: translateY(14px) scale(.9); }} to {{ opacity: 1; transform: none; }} }}
@keyframes bin {{ from {{ opacity: 0; transform: scale(.3) translateY(60px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes bout {{ from {{ opacity: 1; }} to {{ opacity: 0; transform: scale(.85); }} }}
.ding {{ position: absolute; z-index: 60; top: 760px; right: 170px; font-size: 120px; }}
@keyframes dingpop {{ 0% {{ opacity: 0; transform: scale(.2) rotate(-30deg); }} 25% {{ opacity: 1; transform: scale(1.2) rotate(18deg); }} 45% {{ transform: rotate(-14deg); }} 65% {{ transform: rotate(8deg); opacity: 1; }} 100% {{ opacity: 0; transform: scale(.9); }} }}
.brand {{ position: absolute; z-index: 70; top: 120px; right: 84px; padding: 12px 30px; border-radius: 40px; background: rgba(15,45,74,.7);
  color: #FAF7F0; font-weight: 700; font-size: 36px; animation: fadein .6s ease .2s both; }}
.progress {{ position: absolute; z-index: 80; top: 64px; left: 84px; right: 84px; height: 7px; border-radius: 4px; background: rgba(255,255,255,.25); overflow: hidden; }}
.progress b {{ display: block; height: 100%; background: linear-gradient(90deg, #CDE8D6, #8A90FF); transform-origin: right; animation: prog {total}s linear both; }}
@keyframes prog {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
.end {{ position: absolute; inset: 0; z-index: 90; background: radial-gradient(circle at 50% 38%, #24508A 0%, #0F2D4A 55%, #0A2038 100%);
  animation: wipe .55s cubic-bezier(.7,0,.2,1) {e:.2f}s both; display: flex; flex-direction: column; align-items: center; padding-top: 360px; }}
.logo {{ width: 270px; height: 270px; border-radius: 50%; background: #fff; box-shadow: 0 0 60px rgba(138,144,255,.55); animation: logo .9s cubic-bezier(.34,1.56,.64,1) both; }}
@keyframes logo {{ from {{ opacity: 0; transform: scale(.3) rotate(-25deg); }} to {{ opacity: 1; transform: none; }} }}
.ename {{ margin-top: 70px; color: #FAF7F0; font-weight: 900; font-size: 88px; animation: fu .7s ease {e + .8:.2f}s both; }}
.etag {{ margin-top: 18px; color: #CDE8D6; font-weight: 500; font-size: 50px; animation: fu .7s ease {e + 1.1:.2f}s both; }}
.phone {{ margin-top: 70px; padding: 26px 70px; border-radius: 90px; background: #FAF7F0; color: #0F2D4A; font-weight: 900; font-size: 84px;
  direction: ltr; animation: pp .7s cubic-bezier(.34,1.56,.64,1) {e + 1.4:.2f}s both; }}
@keyframes pp {{ from {{ opacity: 0; transform: scale(.4); }} to {{ opacity: 1; transform: none; }} }}
.ecta {{ margin-top: 40px; color: #FAF7F0; font-weight: 700; font-size: 46px; animation: fu .7s ease {e + 1.8:.2f}s both; }}
.ehours {{ margin-top: 18px; color: #E2E8F0; font-weight: 500; font-size: 42px; animation: fu .7s ease {e + 2.0:.2f}s both; }}
@keyframes fu {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: none; }} }}
</style></head><body>
{''.join(parts)}
<div class="brand">{html.escape(BRAND_FA)}</div>
<div class="end">{logo}<div class="ename">{html.escape(BRAND_FA)}</div><div class="etag">پرستار و پزشک در منزل</div>
<div class="phone">{PHONE}</div><div class="ecta">برای هماهنگی تماس بگیرید</div><div class="ehours">هر روز ۷ صبح تا ۱۱ شب · {HANDLE}</div></div>
<div class="progress"><b></b></div>
</body></html>"""


# ---------- sound effects, mixed over the music ----------
SR = music.SR


def sfx(kind: str) -> np.ndarray:
    t = np.arange(int(SR * {"ding": 1.6, "pop": 0.18, "whoosh": 0.6}[kind])) / SR
    if kind == "pop":
        f = 900 * np.exp(-t * 18) + 380
        return 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 26)
    if kind == "whoosh":
        rng = np.random.default_rng(1)
        n = rng.standard_normal(len(t))
        env = np.sin(np.pi * t / t[-1]) ** 2
        return 0.25 * (n - music.lowpass(n, 900)) * env
    out = np.zeros_like(t)                     # ding-dong
    for start, freq in ((0.0, 1318.5), (0.42, 1046.5)):
        tt = np.clip(t - start, 0, None)
        on = (t >= start).astype(float)
        out += on * np.exp(-tt * 3.2) * (np.sin(2 * np.pi * freq * tt) + 0.4 * np.sin(2 * np.pi * 2.76 * freq * tt))
    return 0.32 * out


def soundtrack(script: dict) -> np.ndarray:
    total = script["total"]
    bed = music.make(total, script.get("seed", 3), script["end_at"]) * 0.55     # music under the dialogue
    events = []
    for sc in script["scenes"]:
        if sc["start"] > 0:
            events.append(("whoosh", sc["start"] - 0.1))
        events += [("pop", l["at"]) for l in sc.get("lines", [])]
        events += [("pop", a.get("at", sc["start"]) + 0.15) for a in sc.get("actors", []) if a.get("enter") == "pop"]
        events += [(s["kind"], s["at"]) for s in sc.get("sfx", [])]
        events += [("pop", p["at"]) for p in sc.get("props", [])]
        if sc.get("items"):
            base = sc.get("items_at", sc["start"] + 0.9)
            events += [("pop", base + k * sc.get("items_step", 1.1) + .35) for k in range(len(sc["items"]))]
    events.append(("whoosh", script["end_at"] - 0.1))
    for kind, at in events:
        s = sfx(kind)
        i = int(max(0, at) * SR)
        j = min(len(bed), i + len(s))
        bed[i:j] += s[: j - i, None]
    return np.tanh(bed * 1.1) / max(1e-9, np.abs(np.tanh(bed * 1.1)).max()) * 0.9


def build(script: dict, out: pathlib.Path, stills: dict | None = None) -> pathlib.Path:
    from playwright.sync_api import sync_playwright

    total = script["total"]
    stills = stills or {}
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        (t / "reel.html").write_text(page(script), encoding="utf-8")
        music.save(str(t / "audio.wav"), soundtrack(script))
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
            for f in range(int(total * FPS)):
                pg.evaluate(f"document.getAnimations().forEach(a => a.currentTime = {f * 1000 / FPS})")
                shot = pg.screenshot(type="jpeg", quality=92)
                enc.stdin.write(shot)
                if f in stills:
                    pathlib.Path(stills[f]).write_bytes(shot)
            browser.close()
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
        part.rename(out)
    return out


def frames(script: dict, times: list[float], outdir: pathlib.Path) -> None:
    """Draw single frames at full size (to check before a full render)."""
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        (t / "reel.html").write_text(page(script), encoding="utf-8")
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto((t / "reel.html").as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_function("Array.from(document.images).every(i => i.complete)")
            pg.evaluate("document.getAnimations().forEach(a => a.pause())")
            for x in times:
                pg.evaluate(f"document.getAnimations().forEach(a => a.currentTime = {x * 1000})")
                pg.screenshot(path=str(outdir / f"check-{x:05.2f}.jpg"), type="jpeg", quality=88)
            b.close()


if __name__ == "__main__":
    s = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(build(s, pathlib.Path(sys.argv[2])))
