#!/usr/bin/env python3
"""Render an LTspice .asc schematic to SVG.

LTspice has no headless image export, so a schematic drawn in it cannot be shown
on GitHub without a manual screenshot. Both LTspice file formats are plain-text
line primitives, so this reads the .asc plus the .asy symbol definitions it
references and re-draws the whole thing as SVG.

Coordinates are y-down in both LTspice and SVG, so placement maps across
directly. The rotation mapping (R90 -> (x, y) -> (-y, x)) was checked against
this schematic's own wire endpoints: R1's transformed pins land exactly on the
wires the netlist says they connect to.
"""
import argparse
import math
from pathlib import Path
from xml.sax.saxutils import escape

SYM_DIRS = [
    Path.home() / "AppData/Local/LTspice/lib/sym",
    Path("C:/Program Files/ADI/LTspice/lib/sym"),
]

# dark surface, matching the other figures in this repo
BG = "#1a1a19"
INK = "#e8eaee"
NAME = "#ffffff"
VALUE = "#c3c2b7"
NET = "#3987e5"
DIRECTIVE = "#d95926"

SANS = "Segoe UI, Helvetica, Arial, sans-serif"
MONO = "Cascadia Mono, Consolas, monospace"

ROT = {
    "R0":   lambda x, y: (x, y),
    "R90":  lambda x, y: (-y, x),
    "R180": lambda x, y: (-x, -y),
    "R270": lambda x, y: (y, -x),
    "M0":   lambda x, y: (-x, y),
    "M90":  lambda x, y: (-y, -x),
    "M180": lambda x, y: (x, -y),
    "M270": lambda x, y: (y, x),
}

ANCHOR = {"Left": "start", "Right": "end", "Center": "middle",
          "VTop": "middle", "VBottom": "middle", "Top": "middle",
          "Bottom": "middle"}


def find_symbol(name):
    rel = name.replace("\\", "/")
    while "//" in rel:
        rel = rel.replace("//", "/")
    for d in SYM_DIRS:
        p = d / (rel + ".asy")
        if p.exists():
            return p
    return None


def parse_asy(path):
    """Return {'shapes': [...], 'windows': {id: (x, y, align, size)}}."""
    shapes, windows = [], {}
    for raw in path.read_text(errors="replace").splitlines():
        t = raw.split()
        if not t:
            continue
        kind = t[0].upper()
        try:
            if kind == "LINE" and len(t) >= 6:
                shapes.append(("line", [int(v) for v in t[2:6]]))
            elif kind == "RECTANGLE" and len(t) >= 6:
                shapes.append(("rect", [int(v) for v in t[2:6]]))
            elif kind == "CIRCLE" and len(t) >= 6:
                shapes.append(("circle", [int(v) for v in t[2:6]]))
            elif kind == "ARC" and len(t) >= 10:
                shapes.append(("arc", [int(v) for v in t[2:10]]))
            elif kind == "WINDOW" and len(t) >= 5:
                windows[int(t[1])] = (int(t[2]), int(t[3]), t[4],
                                      int(t[5]) if len(t) > 5 else 2)
        except ValueError:
            continue
    return {"shapes": shapes, "windows": windows}


def parse_asc(path):
    wires, flags, symbols, texts = [], [], [], []
    cur = None
    for raw in path.read_text(errors="replace").splitlines():
        t = raw.split()
        if not t:
            continue
        kind = t[0].upper()
        if kind == "WIRE" and len(t) >= 5:
            wires.append([int(v) for v in t[1:5]])
        elif kind == "FLAG" and len(t) >= 4:
            flags.append((int(t[1]), int(t[2]), t[3]))
        elif kind == "SYMBOL" and len(t) >= 5:
            cur = {"name": t[1], "x": int(t[2]), "y": int(t[3]), "rot": t[4],
                   "attrs": {}, "windows": {}}
            symbols.append(cur)
        elif kind == "WINDOW" and cur is not None and len(t) >= 5:
            cur["windows"][int(t[1])] = (int(t[2]), int(t[3]), t[4],
                                         int(t[5]) if len(t) > 5 else 2)
        elif kind == "SYMATTR" and cur is not None and len(t) >= 3:
            cur["attrs"][t[1]] = " ".join(t[2:])
        elif kind == "TEXT" and len(t) >= 5:
            parts = raw.split(None, 5)
            texts.append((int(t[1]), int(t[2]), t[3], parts[5] if len(parts) > 5 else ""))
    return wires, flags, symbols, texts


def arc_points(bx1, by1, bx2, by2, sx, sy, ex, ey, steps=24):
    """Sample an LTspice ARC. Sampling sidesteps SVG arc-flag ambiguity."""
    cx, cy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
    rx, ry = abs(bx2 - bx1) / 2.0, abs(by2 - by1) / 2.0
    if rx == 0 or ry == 0:
        return []
    a0 = math.atan2((sy - cy) / ry, (sx - cx) / rx)
    a1 = math.atan2((ey - cy) / ry, (ex - cx) / rx)
    while a1 <= a0:
        a1 += 2 * math.pi
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / steps),
             cy + ry * math.sin(a0 + (a1 - a0) * i / steps))
            for i in range(steps + 1)]


def render(asc_path, out, pad=60):
    wires, flags, symbols, texts = parse_asc(asc_path)
    body, labels, pts = [], [], []

    def note(x, y):
        pts.append((x, y))

    def line(x1, y1, x2, y2, width=2.5):
        body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                    'stroke-width="%s" stroke-linecap="round"/>'
                    % (x1, y1, x2, y2, INK, width))
        note(x1, y1)
        note(x2, y2)

    def text(x, y, s, colour, size=15, weight="400", anchor="start",
             family=SANS, vertical=False):
        rot = (' transform="rotate(-90 %.1f %.1f)"' % (x, y)) if vertical else ""
        # Knock the background out from behind the glyphs so a label stays
        # readable where the original layout runs it across a wire.
        halo = (' paint-order="stroke" stroke="%s" stroke-width="2.6" '
                'stroke-linejoin="round"' % BG)
        labels.append('<text x="%.1f" y="%.1f" fill="%s" font-size="%s" '
                      'font-weight="%s" text-anchor="%s" font-family="%s"%s%s>%s</text>'
                      % (x, y, colour, size, weight, anchor, family, halo, rot,
                         escape(s)))

    # ---- wires
    for x1, y1, x2, y2 in wires:
        line(x1, y1, x2, y2)

    # ---- junction dots where three or more wire ends meet
    ends = {}
    for x1, y1, x2, y2 in wires:
        for p in ((x1, y1), (x2, y2)):
            ends[p] = ends.get(p, 0) + 1
    for (x, y), n in ends.items():
        if n >= 3:
            body.append('<circle cx="%d" cy="%d" r="4.5" fill="%s"/>' % (x, y, INK))

    # ---- symbols
    for s in symbols:
        asy = find_symbol(s["name"])
        if asy is None:
            print("  ! symbol not found: %s" % s["name"])
            continue
        sym = parse_asy(asy)
        tf = ROT.get(s["rot"], ROT["R0"])
        ox, oy = s["x"], s["y"]

        def T(x, y, tf=tf, ox=ox, oy=oy):
            dx, dy = tf(x, y)
            return ox + dx, oy + dy

        for kind, v in sym["shapes"]:
            if kind == "line":
                (x1, y1), (x2, y2) = T(v[0], v[1]), T(v[2], v[3])
                line(x1, y1, x2, y2)
            elif kind == "rect":
                a, b = T(v[0], v[1]), T(v[2], v[3])
                x1, y1 = min(a[0], b[0]), min(a[1], b[1])
                x2, y2 = max(a[0], b[0]), max(a[1], b[1])
                body.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                            'fill="none" stroke="%s" stroke-width="2.5"/>'
                            % (x1, y1, x2 - x1, y2 - y1, INK))
                note(x1, y1)
                note(x2, y2)
            elif kind == "circle":
                a, b = T(v[0], v[1]), T(v[2], v[3])
                cx, cy = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
                rx, ry = abs(b[0] - a[0]) / 2.0, abs(b[1] - a[1]) / 2.0
                body.append('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" '
                            'fill="none" stroke="%s" stroke-width="2.5"/>'
                            % (cx, cy, rx, ry, INK))
                note(cx - rx, cy - ry)
                note(cx + rx, cy + ry)
            elif kind == "arc":
                p = arc_points(*v)
                if p:
                    d = " ".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", *T(x, y))
                                 for i, (x, y) in enumerate(p))
                    body.append('<path d="%s" fill="none" stroke="%s" '
                                'stroke-width="2.2" stroke-linecap="round"/>' % (d, INK))

        # Window 0 is the instance name, window 3 the value. LTspice keeps these
        # offsets in the final screen frame -- they are relative to the symbol
        # origin but are NOT rotated with it, which is why a user can drag a
        # label somewhere sensible on an already-rotated part.
        sym_pts = [T(px, py) for kind, v in sym["shapes"]
                   for px, py in ((v[0], v[1]), (v[2], v[3]))]
        for wid, key, colour, weight in ((0, "InstName", NAME, "600"),
                                         (3, "Value", VALUE, "400")):
            label = s["attrs"].get(key)
            if not label:
                continue
            w = s["windows"].get(wid) or sym["windows"].get(wid)
            vertical = False
            if w is not None:
                wx, wy = ox + w[0], oy + w[1]
                anchor = ANCHOR.get(w[2], "start")
                vertical = w[2].startswith("V")
            elif wid == 0 and sym_pts:
                # no window defined (the op-amp symbol has none) -- sit the
                # reference just above the symbol's top-left corner
                wx = min(q[0] for q in sym_pts)
                wy = min(q[1] for q in sym_pts) - 10
                anchor = "start"
            else:
                continue
            text(wx, wy, label, colour, weight=weight, anchor=anchor,
                 vertical=vertical)
            if vertical:
                note(wx - 10, wy - 9 * len(label))
                note(wx + 14, wy + 10)
            else:
                note(wx - 10, wy - 14)
                note(wx + 9 * len(label), wy + 6)

    # ---- flags: ground glyph for net 0, otherwise a net label
    for x, y, name in flags:
        if name == "0":
            body.append('<path d="M%d,%d L%d,%d M%d,%d L%d,%d M%d,%d L%d,%d" '
                        'stroke="%s" stroke-width="2.5" stroke-linecap="round" '
                        'fill="none"/>'
                        % (x - 13, y + 4, x + 13, y + 4,
                           x - 8, y + 10, x + 8, y + 10,
                           x - 3, y + 16, x + 3, y + 16, INK))
            note(x - 15, y + 18)
            note(x + 15, y + 18)
        else:
            text(x, y - 9, name, NET, weight="600", anchor="middle")
            note(x - 30, y - 24)
            note(x + 30, y)

    # ---- free text and SPICE directives
    for x, y, _align, raw in texts:
        directive = raw.startswith("!")
        content = raw[1:] if directive else raw
        colour = DIRECTIVE if directive else VALUE
        family = MONO if directive else SANS
        for i, ln in enumerate(content.split("\\n")):
            yy = y + i * 21
            text(x, yy, ln, colour, size=14, family=family)
            note(x, yy - 14)
            note(x + 8.2 * len(ln), yy + 6)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = min(xs) - pad, min(ys) - pad
    w = max(xs) - min(xs) + 2 * pad
    h = max(ys) - min(ys) + 2 * pad

    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.1f %.1f %.1f %.1f" '
           'width="%.0f" height="%.0f" role="img" '
           'aria-label="LTspice schematic of the relaxation oscillator">'
           '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>%s</svg>'
           % (x0, y0, w, h, w, h, x0, y0, w, h, BG, "".join(body + labels)))
    Path(out).write_text(svg, encoding="utf-8")
    print("%s: %.0fx%.0f, %d symbols, %d wires"
          % (Path(out).name, w, h, len(symbols), len(wires)))


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--asc", type=Path, default=root / "ltspice" / "LTSpiceSchematicMP1.asc")
    ap.add_argument("--out", type=Path, default=root / "images" / "ltspice-schematic.svg")
    a = ap.parse_args()
    render(a.asc, a.out)

    # Also emit a PNG. GitHub does render SVG in a README, but a raster copy is
    # a guaranteed fallback and is what the README actually embeds.
    try:
        import fitz
        doc = fitz.open(a.out)
        page = fitz.open("pdf", doc.convert_to_pdf())[0]
        png = a.out.with_suffix(".png")
        page.get_pixmap(dpi=150, alpha=False).save(png)
        print("%s: raster fallback" % png.name)
    except Exception as exc:
        print("PNG fallback skipped: %s" % exc)
