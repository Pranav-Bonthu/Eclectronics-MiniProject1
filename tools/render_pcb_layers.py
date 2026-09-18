#!/usr/bin/env python3
"""Render readable 2D layer views of the PCB.

kicad-cli's own colour output puts pale yellow silkscreen on a white sheet,
which is close to unreadable at README scale. Instead this plots each layer
separately in black-and-white, turns each into a mask, and composites the masks
with our own colours over a dark background -- so copper, silkscreen and the
board outline all stay legible and the result is reproducible from this repo
alone, with no KiCad colour-theme config to install.

All layers are plotted onto the same A4 page at the same DPI, so the rasters
line up pixel-for-pixel and can share one crop box.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
DPI = 600
BACKGROUND = (22, 26, 32)

# (layer, colour, opacity) -- painted in order, first is furthest back
FRONT = [
    ("Edge.Cuts",     (120, 132, 148), 1.0),
    ("F.Cu",          (214, 118, 72),  1.0),
    ("F.Silkscreen",  (238, 240, 244), 1.0),
]
BACK = [
    ("Edge.Cuts",     (120, 132, 148), 1.0),
    ("B.Cu",          (94, 148, 190),  1.0),
    ("B.Silkscreen",  (238, 240, 244), 1.0),
]


def layer_mask(board: Path, layer: str, tmp: Path, mirror: bool) -> np.ndarray:
    """Plot one layer black-on-white and return it as a 0..1 coverage mask."""
    out = tmp / f"{layer.replace('.', '_')}.pdf"
    cmd = [CLI, "pcb", "export", "pdf", "--mode-single", "-l", layer,
           "--black-and-white", "-o", str(out), str(board)]
    if mirror:
        cmd.insert(-1, "--mirror")
    subprocess.run(cmd, check=True, capture_output=True)

    doc = fitz.open(out)
    pix = doc[0].get_pixmap(dpi=DPI, alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    doc.close()
    # black ink on a white page -> coverage is the inverse of luminance
    return 1.0 - arr.mean(axis=2) / 255.0


def compose(board: Path, spec, png: Path, mirror: bool = False) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        masks = [(layer_mask(board, name, tmp, mirror), colour, alpha)
                 for name, colour, alpha in spec]

    h, w = masks[0][0].shape
    canvas = np.zeros((h, w, 3), dtype=float)
    canvas[:] = BACKGROUND

    for mask, colour, alpha in masks:
        a = (mask * alpha)[..., None]
        canvas = canvas * (1 - a) + np.array(colour, dtype=float) * a

    # crop to the union of everything drawn, then pad
    union = np.maximum.reduce([m for m, _, _ in masks])
    ys, xs = np.where(union > 0.04)
    if len(ys):
        pad = 40
        y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad + 1)
        x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad + 1)
        canvas = canvas[y0:y1, x0:x1]

    img = Image.fromarray(canvas.round().astype(np.uint8))
    if img.width > 2000:
        img = img.resize((2000, round(img.height * 2000 / img.width)), Image.LANCZOS)
    img.save(png, optimize=True)
    print(f"{png.name}: {img.width}x{img.height}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    board = root / "kicad" / "eclectronicsmp1.kicad_pcb"
    images = root / "images"
    compose(board, FRONT, images / "pcb-front.png")
    compose(board, BACK, images / "pcb-back.png", mirror=True)
