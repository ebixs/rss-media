"""Compose the final branded Instagram image (1080x1350, 4:5) for one post.

    python scripts/compose.py posts/<slug>/

Reads  posts/<slug>/post.md   (header fields: headline, subline, service)
       posts/<slug>/background.jpg  (AI photo, no text)
Writes posts/<slug>/final.jpg

All Persian text is drawn here with a real font (Vazirmatn, OFL) and proper
shaping (Pillow + libraqm), because image models garble Persian letters.
The only phone number ever drawn is the official one below.
"""
from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "assets" / "logo.png"  # optional; the real RSS logo, added by the owner

W, H = 1080, 1350
NAVY = (15, 45, 74)
INDIGO = (84, 88, 218)
IVORY = (250, 247, 240)
MINT = (205, 232, 214)  # soft natural medical green
PHONE = "۰۹۱۹۰۴۲۳۴۰۰"
BRAND_FA = "رامان سلامت سهیل"
HANDLE = "@r.s.s.ir"
MARGIN = 72


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Vazirmatn-{weight}.ttf"), size)


def read_header(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith("---"):
        raise SystemExit(f"{path}: missing header")
    _, header, _ = text.split("---", 2)
    meta = {}
    for line in header.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def rtl(draw: ImageDraw.ImageDraw, xy, text, fnt, fill, anchor="ra"):
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor,
              direction="rtl", language="fa", features=["kern", "liga"])


def width(draw: ImageDraw.ImageDraw, text: str, fnt) -> float:
    return draw.textlength(text, font=fnt, direction="rtl", language="fa")


def wrap(draw, text: str, fnt, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if width(draw, trial, fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def balanced(draw, text: str, fnt, max_w: int) -> list[str]:
    """Same number of lines as greedy wrapping, but with even line lengths."""
    lines = wrap(draw, text, fnt, max_w)
    if len(lines) < 2:
        return lines
    best, w = lines, max_w
    while w > max_w * 0.5:
        w -= 12
        trial = wrap(draw, text, fnt, w)
        if len(trial) > len(lines):
            break
        best = trial
    return best


def cover(img: Image.Image) -> Image.Image:
    """Scale and centre-crop the background to exactly W x H."""
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - W) // 2
    top = max(0, (img.height - H) // 3)  # keep faces in the upper third
    return img.crop((left, top, left + W, top + H))


def bottom_scrim(img: Image.Image, start: float = 0.42) -> Image.Image:
    """Navy gradient from mid-image to the bottom so text stays readable."""
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = scrim.load()
    y0 = int(H * start)
    for y in range(y0, H):
        t = (y - y0) / (H - y0)
        alpha = int(235 * (t ** 1.15))
        for x in range(W):
            px[x, y] = (*NAVY, alpha)
    return Image.alpha_composite(img.convert("RGBA"), scrim)


def top_scrim(img: Image.Image) -> Image.Image:
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = scrim.load()
    for y in range(0, 220):
        alpha = int(150 * (1 - y / 220) ** 1.6)
        for x in range(W):
            px[x, y] = (*NAVY, alpha)
    return Image.alpha_composite(img, scrim)


def brand_mark(img: Image.Image, draw: ImageDraw.ImageDraw) -> None:
    x_right = W - MARGIN
    y = 64
    # Soft navy glass panel behind the header so it reads on bright windows too.
    name_f, tag_f = font("Bold", 34), font("Medium", 24)
    text_w = max(width(draw, BRAND_FA, name_f), width(draw, "خدمات پرستاری و پزشکی در منزل", tag_f))
    logo_w = 140 if LOGO.is_file() else 0
    panel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle(
        (x_right - logo_w - text_w - 36, y - 30, W - MARGIN + 18, y + 110),
        radius=34, fill=(*NAVY, 150),
    )
    img.alpha_composite(panel)
    if LOGO.is_file():
        logo = Image.open(LOGO).convert("RGBA")
        size = 120
        logo.thumbnail((size, size), Image.LANCZOS)
        mask = Image.new("L", logo.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, *logo.size), fill=255)
        img.paste(logo, (x_right - logo.width, y - 22), mask)
        x_right -= logo.width + 20
    rtl(draw, (x_right, y + 2), BRAND_FA, font("Bold", 34), IVORY)
    rtl(draw, (x_right, y + 52), "خدمات پرستاری و پزشکی در منزل", font("Medium", 24), MINT)


def compose(post_dir: pathlib.Path, bg_name: str = "background.jpg", out_name: str = "final.jpg") -> pathlib.Path:
    meta = read_header(post_dir / "post.md")
    headline = meta.get("headline", "").strip()
    subline = meta.get("subline", "").strip()
    service = meta.get("service", "").strip()
    if not headline:
        raise SystemExit("headline is required")

    bg = Image.open(post_dir / bg_name).convert("RGB")
    img = cover(bg)
    img = bottom_scrim(img)
    img = top_scrim(img)
    draw = ImageDraw.Draw(img)

    brand_mark(img, draw)

    max_w = W - 2 * MARGIN
    h_font = font("Black", 76)
    h_lines = balanced(draw, headline, h_font, max_w)
    if len(h_lines) > 3:
        h_font = font("Black", 62)
        h_lines = balanced(draw, headline, h_font, max_w)
    s_font = font("Medium", 36)
    s_lines = balanced(draw, subline, s_font, max_w) if subline else []

    line_h, sub_h = int(h_font.size * 1.32), int(s_font.size * 1.55)
    footer_top = H - 150
    block_h = len(h_lines) * line_h + (24 + len(s_lines) * sub_h if s_lines else 0)
    chip_h = 64 if service else 0
    y = footer_top - 40 - block_h - chip_h

    if service:
        c_font = font("Bold", 28)
        cw = int(width(draw, service, c_font)) + 48
        draw.rounded_rectangle((W - MARGIN - cw, y, W - MARGIN, y + 50), radius=25, fill=MINT)
        rtl(draw, (W - MARGIN - 24, y + 25), service, c_font, NAVY, anchor="rm")
        y += chip_h

    for line in h_lines:
        rtl(draw, (W - MARGIN, y), line, h_font, IVORY)
        y += line_h
    if s_lines:
        y += 24
        for line in s_lines:
            rtl(draw, (W - MARGIN, y), line, s_font, (226, 232, 240))
            y += sub_h

    # Footer: indigo accent line, phone (official number only), handle.
    draw.rectangle((MARGIN, footer_top, W - MARGIN, footer_top + 3), fill=INDIGO)
    p_font = font("Black", 46)
    rtl(draw, (W - MARGIN, footer_top + 38), "تماس و هماهنگی", font("Medium", 28), MINT)
    # Digits are drawn left-to-right so the number never reverses.
    draw.text((W - MARGIN - 230, footer_top + 28), PHONE, font=p_font, fill=IVORY,
              anchor="ra", direction="ltr", language="fa")
    draw.text((MARGIN, footer_top + 44), HANDLE, font=font("Bold", 30), fill=IVORY,
              anchor="la", direction="ltr")

    out = post_dir / out_name
    img.convert("RGB").save(out, "JPEG", quality=92, optimize=True, progressive=True)
    return out


def main() -> int:
    if not features.check("raqm"):
        print("::error::Pillow was built without libraqm; Persian text would break.")
        return 1
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out = compose(pathlib.Path(sys.argv[1]).resolve())
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
