"""«داستان یک خونه» story reels: cinematic 2.5D painterly shots animated from a few key
poses. Consecutive key poses of a shot are joined by optical-flow in-between frames
(Farneback, warped from both sides and blended), so the character really moves; procedural
live layers (falling leaves, tea steam, dust in a sunbeam), slow camera moves, film grain,
vignette, short subtitles, music + ambience + knocks. Rendered at 24 fps.

    python scripts/reel_story.py posts/<folder>/story.json posts/<folder>/reel.mp4

story.json:
{
  "fps": 24, "seed": 5, "end_card": 3.5,
  "shots": [
    {"dur": 4.0, "keys": [["characters/out/a.jpg", 0], ["characters/out/b.jpg", 2.2]], "morph": 1.0,
     "cam": {"from": [1.0, 0.5, 0.5], "to": [1.08, 0.5, 0.45]},          # zoom, centre x, centre y
     "layers": [{"kind": "leaves", "n": 14}, {"kind": "steam", "x": 0.82, "y": 0.66},
                {"kind": "dust", "box": [0.0, 0.0, 0.45, 0.6]}],
     "sub": {"text": "...", "at": 0.6, "to": 3.6}, "sfx": [{"kind": "knock", "at": 2.4}]}
  ],
  "end": {"tag": "پرستار در منزل", "phone": "۰۹۱۹۰۴۲۳۴۰۰"}
}
keys: [image, time within the shot when that pose is fully reached]; the move from one pose to the
next takes `morph` seconds and ends at the next key's time. Shots cross-fade over 0.5 s.
"""
from __future__ import annotations

import json, math, pathlib, subprocess, sys, tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import music  # noqa: E402

W, H = 1080, 1920
NAVY = (15, 45, 74)
FONT = str(ROOT / "assets" / "fonts" / "Vazirmatn-Bold.ttf")
FONT_B = str(ROOT / "assets" / "fonts" / "Vazirmatn-Black.ttf")
XF = 0.5  # cross-fade between shots, seconds


def load(path: str, cache: dict) -> np.ndarray:
    if path not in cache:
        im = Image.open(ROOT / path).convert("RGB")
        # cover the 1080x1920 frame with 12% margin for camera moves
        sw, sh = int(W * 1.12), int(H * 1.12)
        s = max(sw / im.width, sh / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        l, t = (im.width - sw) // 2, (im.height - sh) // 2
        cache[path] = np.asarray(im.crop((l, t, l + sw, t + sh)), dtype=np.float32)
    return cache[path]


def flow(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    sa = cv2.cvtColor(cv2.resize(a.astype(np.uint8), None, fx=.4, fy=.4), cv2.COLOR_RGB2GRAY)
    sb = cv2.cvtColor(cv2.resize(b.astype(np.uint8), None, fx=.4, fy=.4), cv2.COLOR_RGB2GRAY)
    f = cv2.calcOpticalFlowFarneback(sa, sb, None, 0.5, 5, 25, 5, 7, 1.5, 0)
    f = cv2.resize(f, (a.shape[1], a.shape[0])) / .4
    return f


def warp(img: np.ndarray, f: np.ndarray, t: float) -> np.ndarray:
    h, w = img.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx - f[..., 0] * t, gy - f[..., 1] * t, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def inbetween(a, b, fab, fba, t):
    """Frame at fraction t between key a and key b (both warped toward each other, then blended)."""
    t = t * t * (3 - 2 * t)  # ease in-out
    wa = warp(a, fab, t)        # a's content moved t of the way toward b
    wb = warp(b, fba, 1 - t)    # b's content moved back (1 - t) of the way toward a
    return wa * (1 - t) + wb * t


def camera(img: np.ndarray, z: float, cx: float, cy: float) -> np.ndarray:
    h, w = img.shape[:2]
    cw, ch = W / z * 1.0, H / z * 1.0
    cw, ch = min(cw, w), min(ch, h)
    x0 = np.clip(cx * w - cw / 2, 0, w - cw)
    y0 = np.clip(cy * h - ch / 2, 0, h - ch)
    m = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
    return cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------- live layers ----------
class Leaves:
    def __init__(self, n, rng):
        self.p = [(rng.uniform(0, W), rng.uniform(-H, H), rng.uniform(26, 52), rng.uniform(60, 140),
                   rng.uniform(0, 6.28), [(214, 110, 40), (190, 70, 35), (230, 150, 60), (160, 60, 30)][int(rng.integers(4))])
                  for _ in range(n)]

    def draw(self, fr, t):
        over = np.zeros((H, W, 4), np.uint8)
        for x0, y0, s, v, ph, col in self.p:
            y = (y0 + v * t * 1.6) % (H + 200) - 100
            x = x0 + 60 * math.sin(t * 1.3 + ph)
            ang = math.degrees(math.sin(t * 2 + ph)) * 1.4
            cv2.ellipse(over, (int(x), int(y)), (int(s), int(s * .45)), ang, 0, 360, (int(col[0]), int(col[1]), int(col[2]), 235), -1, cv2.LINE_AA)
            cv2.line(over, (int(x - s * .9 * math.cos(math.radians(ang))), int(y - s * .9 * math.sin(math.radians(ang)))),
                     (int(x + s * .9 * math.cos(math.radians(ang))), int(y + s * .9 * math.sin(math.radians(ang)))),
                     (*[int(max(0, c - 60)) for c in col], 200), 2, cv2.LINE_AA)
        over = cv2.GaussianBlur(over, (0, 0), 1.2)
        a = over[..., 3:4].astype(np.float32) / 255
        return fr * (1 - a) + over[..., :3].astype(np.float32) * a


class Steam:
    def __init__(self, x, y, rng):
        self.x, self.y, self.ph = x * W, y * H, rng.uniform(0, 6.28)

    def draw(self, fr, t):
        over = np.zeros((H, W), np.float32)
        for k in range(7):
            u = ((t * .35 + k / 7) % 1)
            yy = self.y - u * 260
            xx = self.x + 26 * math.sin(u * 7 + t * 1.5 + self.ph + k)
            cv2.circle(over, (int(xx), int(yy)), int(18 + 30 * u), 1.0 * (1 - u) * .55, -1, cv2.LINE_AA)
        over = cv2.GaussianBlur(over, (0, 0), 14)[..., None]
        return fr * (1 - over * .5) + 250 * over * .5


class Dust:
    def __init__(self, box, rng):
        x0, y0, x1, y1 = box
        self.p = [(rng.uniform(x0, x1) * W, rng.uniform(y0, y1) * H, rng.uniform(1.5, 4), rng.uniform(0, 6.28)) for _ in range(60)]

    def draw(self, fr, t):
        over = np.zeros((H, W), np.float32)
        for x, y, r, ph in self.p:
            cv2.circle(over, (int(x + 30 * math.sin(t * .4 + ph)), int(y - 20 * t % 120 + 30 * math.cos(t * .3 + ph))), int(r),
                       .5 + .5 * math.sin(t * 2 + ph), -1, cv2.LINE_AA)
        over = cv2.GaussianBlur(over, (0, 0), 1.5)[..., None]
        return fr + over * np.array([255, 230, 180], np.float32) * .55


def subtitle(text: str) -> np.ndarray:
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    f = ImageFont.truetype(FONT, 60, layout_engine=ImageFont.Layout.RAQM)
    d = ImageDraw.Draw(im)
    # wrap at ~22 characters per line, right-to-left
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) > 22 and cur:
            lines.append(cur); cur = w_
        else:
            cur = (cur + " " + w_).strip()
    lines.append(cur)
    y = 420 - 30 - len(lines) * 92
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    for ln in lines:
        tw = d.textlength(ln, font=f, direction="rtl", language="fa")
        x = (W - tw) / 2
        ds.text((x, y + 3), ln, font=f, fill=(0, 0, 0, 220), direction="rtl", language="fa")
        d.text((x, y), ln, font=f, fill=(255, 250, 240, 255), direction="rtl", language="fa")
        y += 92
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    return np.asarray(Image.alpha_composite(shadow, im), dtype=np.float32)


def end_card(sc: dict) -> np.ndarray:
    im = Image.new("RGB", (W, H), NAVY)
    logo = Image.open(ROOT / "assets" / "logo.png").convert("RGBA").resize((300, 300), Image.LANCZOS)
    m = Image.new("L", (300, 300), 0); ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255)
    im.paste(logo, (390, 600), m)
    d = ImageDraw.Draw(im)
    for txt, fnt, size, y, col in [("رامان سلامت سهیل", FONT_B, 86, 970, (255, 255, 255)),
                                   (sc["end"]["tag"], FONT, 50, 1090, (201, 204, 255))]:
        f = ImageFont.truetype(fnt, size, layout_engine=ImageFont.Layout.RAQM)
        tw = d.textlength(txt, font=f, direction="rtl", language="fa")
        d.text(((W - tw) / 2, y), txt, font=f, fill=col, direction="rtl", language="fa")
    f = ImageFont.truetype(FONT_B, 80, layout_engine=ImageFont.Layout.RAQM)
    ph = sc["end"]["phone"]
    tw = d.textlength(ph, font=f)
    d.rounded_rectangle(((W - tw) / 2 - 70, 1260, (W + tw) / 2 + 70, 1400), radius=70, fill=(255, 255, 255))
    d.text(((W - tw) / 2, 1272), ph, font=f, fill=NAVY)
    return np.asarray(im, dtype=np.float32)


def grade(fr: np.ndarray, rng, vig: np.ndarray) -> np.ndarray:
    fr = fr * vig
    fr += rng.normal(0, 6, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    return np.clip(fr, 0, 255)


def shot_frames(sh: dict, fps: int, cache: dict, rng) -> list:
    keys = [(load(p, cache), float(t)) for p, t in sh["keys"]]
    flows = []
    for (a, _), (b, _) in zip(keys, keys[1:]):
        flows.append((flow(a, b), flow(b, a)))
    layers = []
    for L in sh.get("layers", []):
        if L["kind"] == "leaves": layers.append(Leaves(L.get("n", 12), rng))
        elif L["kind"] == "steam": layers.append(Steam(L["x"], L["y"], rng))
        elif L["kind"] == "dust": layers.append(Dust(L["box"], rng))
    morph = sh.get("morph", 0.8)
    n = int(round(sh["dur"] * fps))
    c0, c1 = sh.get("cam", {}).get("from", [1, .5, .5]), sh.get("cam", {}).get("to", [1.06, .5, .5])
    sub = subtitle(sh["sub"]["text"]) if sh.get("sub") else None
    for i in range(n):
        t = i / fps
        base = keys[0][0]
        for k in range(1, len(keys)):
            tk = keys[k][1]
            if t >= tk:
                base = keys[k][0]
            elif t > tk - morph:
                fab, fba = flows[k - 1]
                base = inbetween(keys[k - 1][0], keys[k][0], fab, fba, (t - (tk - morph)) / morph)
                break
            else:
                break
        u = i / max(1, n - 1)
        u = u * u * (3 - 2 * u)
        z, cx, cy = [a + (b - a) * u for a, b in zip(c0, c1)]
        fr = camera(base, z, cx, cy)
        for L in layers:
            fr = L.draw(fr, t)
        if sub is not None:
            s = sh["sub"]
            a = min(1, max(0, (t - s["at"]) / .35)) * min(1, max(0, (s["to"] - t) / .35))
            if a > 0:
                al = sub[..., 3:4] / 255 * a
                fr[H - 420 - 260:H - 260] = fr[H - 420 - 260:H - 260] * (1 - al) + sub[..., :3] * al
        yield fr


def knock() -> np.ndarray:
    sr = music.SR
    n = int(.18 * sr)
    tt = np.arange(n) / sr
    s = (np.sin(2 * np.pi * 120 * tt) * .9 + np.random.default_rng(1).normal(0, .25, n)) * np.exp(-tt * 38)
    return s * .9


def soundtrack(sc: dict, total: float, end_at: float) -> np.ndarray:
    bed = music.make(total, sc.get("seed", 5), end_at) * .5
    sr = music.SR
    rng = np.random.default_rng(9)
    wind = rng.normal(0, 1, len(bed))
    wind = music.lowpass(wind, 500) * .05 * (1 + .5 * np.sin(np.arange(len(bed)) / sr * .6))
    bed[:, 0] += wind; bed[:, 1] += wind
    t0 = 0.0
    for sh in sc["shots"]:
        for fx in sh.get("sfx", []):
            if fx["kind"] == "knock":
                for k in range(2):
                    i = int((t0 + fx["at"] + k * .28) * sr)
                    s = knock(); j = min(len(bed), i + len(s))
                    bed[i:j] += s[: j - i, None]
        t0 += sh["dur"] - XF
    return np.tanh(bed * 1.1) / max(1e-9, np.abs(np.tanh(bed * 1.1)).max()) * .9


def build(sc: dict, out: pathlib.Path, stills: list[float] | None = None) -> float:
    fps = sc.get("fps", 24)
    rng = np.random.default_rng(sc.get("seed", 5))
    yy, xx = np.mgrid[0:H, 0:W]
    vig = (1 - .38 * (((xx - W / 2) / (W / 1.2)) ** 2 + ((yy - H / 2) / (H / 1.15)) ** 2)).clip(.55, 1)[..., None].astype(np.float32)
    del yy, xx
    xf = int(XF * fps)
    ne = int(sc.get("end_card", 3.5) * fps)
    total = (sum(int(round(sh["dur"] * fps)) for sh in sc["shots"]) - xf * (len(sc["shots"]) - 1) + ne - xf) / fps
    end_at = total - sc.get("end_card", 3.5)
    want = {int(x * fps): i for i, x in enumerate(stills or [])}
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        music.save(str(t / "a.wav"), soundtrack(sc, total, end_at))
        part = out.with_name(out.stem + ".part.mp4")
        enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(fps), "-i", "-", "-i", str(t / "a.wav"), "-map", "0:v", "-map", "1:a",
                                "-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p",
                                "-b:v", "8M", "-maxrate", "10M", "-bufsize", "16M", "-c:a", "aac", "-b:a", "160k",
                                "-shortest", "-movflags", "+faststart", str(part)], stdin=subprocess.PIPE)
        idx = [0]

        def emit(fr, graded=True):
            b = (grade(fr, rng, vig) if graded else np.clip(fr, 0, 255)).astype(np.uint8)
            enc.stdin.write(b.tobytes())
            if idx[0] in want:
                Image.fromarray(b).save(out.with_name(f"frame-{want[idx[0]] + 1}.jpg"), quality=90)
            idx[0] += 1

        cache: dict = {}
        tail: list = []           # last xf frames of the previous shot, held for the cross-fade
        for si, sh in enumerate(sc["shots"]):
            prev, tail = tail, []
            for k, fr in enumerate(shot_frames(sh, fps, cache, rng)):
                if prev and k < xf:
                    a = (k + 1) / (xf + 1)
                    emit(prev[k] * (1 - a) + fr * a)
                    continue
                tail.append(fr)
                if len(tail) > xf:
                    emit(tail.pop(0))
            cache.clear()
        end = end_card(sc)
        for k in range(xf):
            a = (k + 1) / (xf + 1)
            emit(tail[k] * (1 - a) + end * a)
        for _ in range(ne - xf):
            emit(end, graded=False)
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")
        part.replace(out)
    return idx[0] / fps


if __name__ == "__main__":
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    sc = json.loads(src.read_text(encoding="utf-8"))
    t, marks = 0.0, []
    for sh in sc["shots"]:
        marks.append(t + sh["dur"] * .7)
        t += sh["dur"] - XF
    marks.append(t + 1.5)
    print("ok", build(sc, dst, marks), "s")
