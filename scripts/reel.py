"""Build a ~15 second vertical Instagram reel (1080x1920, H.264, 30 fps) for one post.

    python scripts/reel.py posts/<slug>/

Reads  posts/<slug>/post.md       header: scene_1, scene_2, scene_3 (short Persian lines;
                                  scene_1 is the hook), optional scene_sub_1..3, service
       posts/<slug>/background-1.jpg .. background-3.jpg   (AI photos, no text)
Writes posts/<slug>/reel.mp4      the reel (silent audio track so every player accepts it)
       posts/<slug>/cover.jpg     first scene, used to review and as the reel cover
       posts/<slug>/frame-<n>.jpg one still per scene, for review

Timeline: scene 1 (4.6 s) -> scene 2 (4.0 s) -> scene 3 (4.0 s) -> end card (3.9 s) = 15 s,
0.5 s cross-fades, slow push-in on every photo. Text stays inside Instagram's safe
zone (clear of the top bar and the caption/buttons at the bottom).
All Persian text is drawn with Vazirmatn + libraqm; the only phone drawn is the official one.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from compose import (BRAND_FA, HANDLE, INDIGO, IVORY, LOGO, MINT, NAVY, PHONE,  # noqa: E402
                     balanced, font, read_header, rtl, width)

W, H = 1080, 1920
MARGIN = 84
FPS = 30
DUR = [4.6, 4.0, 4.0, 3.9]   # seconds per segment (3 scenes + end card)
FADE = 0.5
SAFE_TOP, SAFE_BOTTOM = 250, 1420   # keep text clear of Instagram's overlays


def cover_to(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - w) // 2
    top = max(0, (img.height - h) // 4)
    return img.crop((left, top, left + w, top + h))


def gradient(h_from: float, alpha_max: int) -> Image.Image:
    """Navy gradient over the lower part of the frame."""
    g = Image.new("L", (1, H), 0)
    y0 = int(H * h_from)
    for y in range(y0, H):
        g.putpixel((0, y), int(alpha_max * ((y - y0) / (H - y0)) ** 1.1))
    alpha = g.resize((W, H))
    layer = Image.new("RGBA", (W, H), (*NAVY, 0))
    layer.putalpha(alpha)
    return layer


def logo_disc(size: int) -> Image.Image | None:
    if not LOGO.is_file():
        return None
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((size, size), Image.LANCZOS)
    mask = Image.new("L", logo.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, *logo.size), fill=255)
    out = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    out.paste(logo, (0, 0), mask)
    return out


def scene_text(text: str, sub: str, n: int, service: str) -> Image.Image:
    """Transparent overlay with the scene's Persian line (and a small brand tag)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(gradient(0.45, 225))
    d = ImageDraw.Draw(img)
    max_w = W - 2 * MARGIN
    size = 92 if n == 1 else 80
    f = font("Black", size)
    lines = balanced(d, text, f, max_w)
    while len(lines) > 3 and size > 60:
        size -= 8
        f = font("Black", size)
        lines = balanced(d, text, f, max_w)
    s_font = font("Medium", 44)
    s_lines = balanced(d, sub, s_font, max_w) if sub else []
    lh, sh = int(size * 1.34), int(44 * 1.5)
    block = len(lines) * lh + (28 + len(s_lines) * sh if s_lines else 0)
    y = SAFE_BOTTOM - 40 - block
    if n == 1 and service:
        c = font("Bold", 34)
        cw = int(width(d, service, c)) + 56
        d.rounded_rectangle((W - MARGIN - cw, y - 92, W - MARGIN, y - 32), radius=30, fill=MINT)
        rtl(d, (W - MARGIN - 28, y - 62), service, c, NAVY, anchor="rm")
    d.rectangle((W - MARGIN - 8, y + 10, W - MARGIN, y + len(lines) * lh - 18), fill=INDIGO)
    for line in lines:
        rtl(d, (W - MARGIN - 30, y), line, f, IVORY)
        y += lh
    if s_lines:
        y += 28
        for line in s_lines:
            rtl(d, (W - MARGIN - 30, y), line, s_font, (226, 232, 240))
            y += sh
    # small brand tag at the top, inside the safe zone
    tag = font("Bold", 34)
    tw = int(width(d, BRAND_FA, tag)) + 60
    d.rounded_rectangle((W - MARGIN - tw, SAFE_TOP - 10, W - MARGIN, SAFE_TOP + 58), radius=34, fill=(*NAVY, 170))
    rtl(d, (W - MARGIN - 30, SAFE_TOP + 24), BRAND_FA, tag, IVORY, anchor="rm")
    return img


def end_card() -> Image.Image:
    img = Image.new("RGBA", (W, H), (*NAVY, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((620, 22), (460, 30), (300, 38)):
        gd.ellipse((W / 2 - r, 760 - r, W / 2 + r, 760 + r), fill=(*INDIGO, a))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    y = 430
    disc = logo_disc(260)
    if disc:
        img.alpha_composite(disc, ((W - disc.width) // 2, y))
        y += disc.height + 70
    else:
        y += 120
    d.text((W / 2, y), BRAND_FA, font=font("Black", 84), fill=IVORY, anchor="ma", direction="rtl", language="fa")
    y += 130
    d.text((W / 2, y), "پرستار و پزشک در منزل", font=font("Medium", 50), fill=MINT, anchor="ma", direction="rtl", language="fa")
    y += 120
    d.rounded_rectangle((MARGIN + 60, y, W - MARGIN - 60, y + 150), radius=75, fill=IVORY)
    d.text((W / 2, y + 75), PHONE, font=font("Black", 76), fill=NAVY, anchor="mm", direction="ltr", language="fa")
    y += 210
    d.text((W / 2, y), "هر روز ۷ صبح تا ۱۱ شب", font=font("Medium", 44), fill=IVORY, anchor="ma", direction="rtl", language="fa")
    y += 80
    d.text((W / 2, y), HANDLE, font=font("Bold", 40), fill=MINT, anchor="ma", direction="ltr")
    return img


def build(post_dir: pathlib.Path) -> pathlib.Path:
    meta = read_header(post_dir / "post.md")
    scenes = [meta.get(f"scene_{n}", "").strip() for n in (1, 2, 3)]
    if not all(scenes):
        raise SystemExit("scene_1, scene_2 and scene_3 are required for a reel")
    service = meta.get("service", "").strip()
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        inputs = []
        for n in (1, 2, 3):
            bg = cover_to(Image.open(post_dir / f"background-{n}.jpg").convert("RGB"), W, H)
            # 8% larger source so the slow push-in never shows an edge
            bg.resize((int(W * 1.08), int(H * 1.08)), Image.LANCZOS).save(t / f"bg{n}.png")
            ov = scene_text(scenes[n - 1], meta.get(f"scene_sub_{n}", "").strip(), n, service)
            ov.save(t / f"ov{n}.png")
            still = bg.convert("RGBA")
            still.alpha_composite(ov)
            still.convert("RGB").save(post_dir / f"frame-{n}.jpg", quality=90)
            inputs.append((t / f"bg{n}.png", t / f"ov{n}.png"))
        end = end_card()
        end.convert("RGB").save(t / "end.png")
        end.convert("RGB").save(post_dir / "frame-4.jpg", quality=90)

        args, fc = ["ffmpeg", "-y", "-loglevel", "error"], []
        for i, (bg, ov) in enumerate(inputs):
            args += ["-loop", "1", "-t", f"{DUR[i]}", "-i", str(bg), "-loop", "1", "-t", f"{DUR[i]}", "-i", str(ov)]
        args += ["-loop", "1", "-t", f"{DUR[3]}", "-i", str(t / "end.png")]
        args += ["-f", "lavfi", "-t", f"{sum(DUR) - 3 * FADE}", "-i", "anullsrc=r=44100:cl=stereo"]
        for i in range(3):
            frames = int(DUR[i] * FPS)
            zoom = f"zoompan=z='1+0.07*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
            fc.append(f"[{2 * i}:v]scale={int(W * 1.08)}:{int(H * 1.08)},{zoom},format=yuva420p[z{i}]")
            fc.append(f"[{2 * i + 1}:v]format=rgba,fade=t=in:st=0.25:d=0.5:alpha=1[t{i}]")
            fc.append(f"[z{i}][t{i}]overlay=0:0:format=auto,format=yuv420p,setsar=1[s{i}]")
        fc.append(f"[6:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[s3]")
        off = DUR[0] - FADE
        fc.append(f"[s0][s1]xfade=transition=fade:duration={FADE}:offset={off:.2f}[x1]")
        off += DUR[1] - FADE
        fc.append(f"[x1][s2]xfade=transition=smoothleft:duration={FADE}:offset={off:.2f}[x2]")
        off += DUR[2] - FADE
        fc.append(f"[x2][s3]xfade=transition=fade:duration={FADE}:offset={off:.2f}[v]")
        out = post_dir / "reel.mp4"
        args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "7:a",
                 "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
                 "-b:v", "6M", "-maxrate", "8M", "-bufsize", "12M",
                 "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
        subprocess.run(args, check=True)
    Image.open(post_dir / "frame-1.jpg").save(post_dir / "cover.jpg", quality=90)
    return out


if __name__ == "__main__":
    print(build(pathlib.Path(sys.argv[1])))
