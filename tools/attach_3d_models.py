#!/usr/bin/env python3
"""Attach KiCad stock 3D models to the board's footprints.

The footprints in this design came from SnapEDA/DigiKey and ship with no 3D
model attached, so `kicad-cli pcb render` would otherwise produce a bare board
with no components standing on it. Every package here is a JEDEC-standard
outline, so KiCad's own shipped models fit without modification.

Models are referenced through ${KICAD10_3DMODEL_DIR} so the board stays portable.
Idempotent: re-running will not add duplicate model entries.
"""
import re
import sys
from pathlib import Path

# footprint "LIB:NAME"  ->  path under ${KICAD10_3DMODEL_DIR}
MODELS = {
    "RC0603FR_0760K4L:RC0603N_YAG":      "Resistor_SMD.3dshapes/R_0603_1608Metric.step",
    "C0603C105K3RACTU:CAPC17595_95N_KEM": "Capacitor_SMD.3dshapes/C_0603_1608Metric.step",
    "LTST_C171KRKT:LED_LTST-C171_LTO":   "LED_SMD.3dshapes/LED_0603_1608Metric.step",
    "MCP6021T_E_OT:SOT-23-5_MC_MCH":     "Package_TO_SOT_SMD.3dshapes/SOT-23-5.step",
    "MCP1702T_3302E_CB:SOT-23A_MC_MCH":  "Package_TO_SOT_SMD.3dshapes/SOT-23.step",
    # 480370001:CONN_480370001_MOL is deliberately left bare -- its 4 signal pads
    # use an irregular pitch (2.5/2.0/2.5 mm) that no stock Molex model matches,
    # and a misaligned connector renders worse than none at all.
}

MODEL_BLOCK = """\t\t(model "${{KICAD10_3DMODEL_DIR}}/{path}"
\t\t\t(offset
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t\t(scale
\t\t\t\t(xyz 1 1 1)
\t\t\t)
\t\t\t(rotate
\t\t\t\t(xyz 0 0 0)
\t\t\t)
\t\t)
"""

FOOTPRINT_RE = re.compile(r'^\t\(footprint "([^"]+)"')


def main(board: Path) -> int:
    lines = board.read_text(encoding="utf-8").splitlines(keepends=True)
    out, current, added, skipped = [], None, 0, 0

    for line in lines:
        m = FOOTPRINT_RE.match(line)
        if m:
            current = m.group(1)
        elif line.startswith("\t\t(model "):
            # already has a model -- leave this footprint alone
            if current:
                skipped += 1
                current = None
        elif line == "\t\t(embedded_fonts no)\n" and current in MODELS:
            out.append(MODEL_BLOCK.format(path=MODELS[current]))
            added += 1
            current = None
        out.append(line)

    board.write_text("".join(out), encoding="utf-8", newline="")
    print(f"attached {added} model(s), skipped {skipped} footprint(s) that already had one")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).resolve().parent.parent / "kicad" / "eclectronicsmp1.kicad_pcb"
    sys.exit(main(target))
