#!/usr/bin/env python3
"""Crop the empty backdrop out of a kicad-cli 3D render.

kicad-cli frames the board inside a fixed viewport, so the PNG carries a wide
lavender border. Zooming in far enough to remove it risks clipping the board
instead, so render loose and crop here: the backdrop is bluish (blue channel
dominant) while the board is green, which separates them cleanly.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def trim(path: Path, pad: int = 18) -> None:
    img = Image.open(path).convert("RGB")
    a = np.asarray(img).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # backdrop and its drop shadow are blue-dominant; board copper/mask is not
    board = g >= b + 4

    ys, xs = np.where(board)
    if len(ys) == 0:
        print(f"{path.name}: nothing to trim")
        return

    h, w = board.shape
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
    out = img.crop((x0, y0, x1, y1))
    out.save(path, optimize=True)
    print(f"{path.name}: {img.width}x{img.height} -> {out.width}x{out.height}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        trim(Path(p))
