"""Cut brand-character renders out of their studio background for the dialogue reels.

Reads characters/jobs.json; every job with "cut": "<name>" turns characters/out/<id>-<first seed>.jpg
into characters/cut/<name>.png (transparent). The mask from rembg (isnet) is closed and
hole-filled with the render's own pixels, so thin gaps (e.g. a roof edge) are not cut away,
while true background colour stays transparent.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parent.parent


def cut(src: pathlib.Path, dest: pathlib.Path, session) -> None:
    im = Image.open(src).convert("RGB")
    S = np.array(im).astype(float)
    A = np.array(remove(im, session=session).split()[-1])
    a = A > 128
    closed = ndimage.binary_fill_holes(ndimage.binary_closing(a, structure=np.ones((41, 41))))
    bg = np.concatenate([S[:, :40], S[:, -40:]], axis=1).mean(axis=1)
    dist = np.sqrt(((S - bg[:, None, :]) ** 2).sum(-1))
    add = ndimage.binary_opening(closed & ~a & (dist > 22), structure=np.ones((5, 5)))
    alpha = np.maximum(A, (add * 255).astype(np.uint8))
    alpha = np.maximum(alpha, (ndimage.binary_fill_holes(alpha > 40) * 255).astype(np.uint8))
    im.putalpha(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1.0)))
    im = im.crop(im.getbbox())
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    print("cut", dest.name, im.size)


def main() -> None:
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
