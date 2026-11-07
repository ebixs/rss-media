"""Cut brand-character renders out of their studio background for the dialogue reels.

Reads characters/jobs.json; every job with "cut": "<name>" turns characters/out/<id>-<first seed>.jpg
into characters/cut/<name>.png (transparent). The mask from rembg (isnet) is combined with a
colour test against a fitted model of the studio background: parts rembg misses (ivory wall,
chimney) come back, gaps of background colour (between arm and body) and floor shadow stay out.
Re-cut one render by hand: python scripts/cutouts.py <render.jpg> <dest.png>
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parent.parent


def bg_model(S: np.ndarray, A: np.ndarray) -> np.ndarray:
    """Smooth model of the studio background (cubic surface per channel), fitted robustly on
    pixels rembg calls background, so the vignette and floor gradient are followed."""
    h, w, _ = S.shape
    yy, xx = np.mgrid[0:h, 0:w]
    yy, xx = yy / h, xx / w
    F = np.stack([np.ones_like(xx), xx, yy, xx * xx, yy * yy, xx * yy, xx ** 3, yy ** 3, xx * xx * yy, xx * yy * yy], -1)
    m = ndimage.binary_erosion(A < 10, np.ones((15, 15)))
    M = S
    for _ in range(4):
        coef = np.linalg.lstsq(F[m], S[m], rcond=None)[0]
        M = F @ coef
        m &= np.sqrt(((S - M) ** 2).sum(-1)) < 12
    return M


def chroma(X: np.ndarray) -> np.ndarray:
    return X / (X.sum(-1, keepdims=True) + 1e-6) * 765


def cut(src: pathlib.Path, dest: pathlib.Path, session, T: float = 12) -> None:
    """rembg mask + colour against the background model:
    - adds back parts rembg missed that differ in colour from the studio background
      (an ivory wall or chimney on the ivory backdrop), but not floor shadow (darker, same hue);
    - leaves gaps between arm and body transparent when they are background colour
      (no more filled-in backdrop patches)."""
    im = Image.open(src).convert("RGB")
    S = np.array(im).astype(float)
    A = np.array(remove(im, session=session).split()[-1])
    M = bg_model(S, A)
    Rc = np.sqrt(((chroma(S) - chroma(M)) ** 2).sum(-1))
    a = A > 128
    col = ndimage.binary_opening(Rc > T, structure=np.ones((5, 5)))
    col &= ndimage.binary_opening((Rc > 25) | ((S - M).max(-1) > 6), structure=np.ones((3, 3)))
    lab, n = ndimage.label(a | col)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(n + 1))
    body = np.isin(lab, [i for i in set(np.unique(lab[a])) - {0} if sizes[i] > 2000])
    env = ndimage.binary_fill_holes(ndimage.binary_closing(body, structure=np.ones((25, 25))))
    gl, gn = ndimage.label(env & ~body)
    keep = body.copy()
    for i in range(1, gn + 1):
        g = gl == i
        if g.sum() < 40 or col[g].mean() > 0.5:
            keep |= g
    alpha = np.where(keep, np.where(col | ~a, 255, A), 0).astype(np.uint8)
    im.putalpha(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1.0)))
    im = im.crop(im.getbbox())
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    print("cut", dest.name, im.size)


def main() -> None:
    import sys
    if len(sys.argv) == 3:
        cut(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), new_session("isnet-general-use"))
        return
    jobs = json.loads((ROOT / "characters" / "jobs.json").read_text(encoding="utf-8"))
    todo = [(ROOT / "characters" / "out" / f"{j['id']}-{j['seeds'][0]}.jpg", ROOT / "characters" / "cut" / f"{j['cut']}.png")
            for j in jobs if j.get("cut")]
    todo = [(s, d) for s, d in todo if s.exists() and not d.exists()]
    if not todo:
        print("nothing to cut")
        return
    session = new_session("isnet-general-use")
    for s, d in todo:
        cut(s, d, session)


if __name__ == "__main__":
    main()
