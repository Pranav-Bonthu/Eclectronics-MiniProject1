#!/usr/bin/env python3
"""Rasterize a PDF page to a trimmed PNG.

kicad-cli emits vector PDFs on a full A4 sheet, which leaves the artwork
floating in a sea of white. This renders at high DPI, trims the uniform border
back to the drawing, then re-pads it slightly so it doesn't sit flush against
the image edge.
"""
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageChops


def render(pdf: Path, png: Path, dpi: int = 300, pad: int = 24) -> None:
    doc = fitz.open(pdf)
    pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()

    # Trim whatever solid colour surrounds the drawing (white sheet or black bg).
    bg = Image.new("RGB", img.size, img.getpixel((0, 0)))
    box = ImageChops.difference(img, bg).convert("L").point(lambda p: 255 if p > 12 else 0).getbbox()
    if box:
        img = img.crop(box)

    canvas = Image.new("RGB", (img.width + 2 * pad, img.height + 2 * pad), bg.getpixel((0, 0)))
    canvas.paste(img, (pad, pad))
    canvas.save(png, optimize=True)
    print(f"{png.name}: {canvas.width}x{canvas.height}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: pdf_to_png.py IN.pdf OUT.png [dpi]")
    render(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 300)
