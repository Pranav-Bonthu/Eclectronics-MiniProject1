# Eclectronics Mini-Project 1 — Op-Amp LED Blinker

A 35 × 20 mm two-layer PCB that blinks an LED once per second, using no
microcontroller and no 555 — just two op-amps, an RC network, and a 3.3 V
regulator. Designed from scratch in LTspice, verified against component
tolerances with a 200-run Monte Carlo sweep, then laid out in KiCad.

<p align="center">
  <img src="images/pcb-3d-iso.png" alt="3D render of the assembled board" width="90%">
</p>

---

## Schematic

<p align="center">
  <img src="images/kicad-schematic.png" alt="KiCad schematic" width="94%">
</p>

Full-resolution PDF: [`docs/kicad-schematic.pdf`](docs/kicad-schematic.pdf)

---

## The board

Two layers, 35 × 20 mm, 15 components, entirely 0603 passives and SOT-23
actives.

| Top | Bottom |
|---|---|
| <img src="images/pcb-3d-top.png" alt="Top of the board"> | <img src="images/pcb-3d-bottom.png" alt="Bottom of the board"> |

Copper and silkscreen, as plotted for fabrication:

| Front (F.Cu + silkscreen) | Back (B.Cu) |
|---|---|
| <img src="images/pcb-front.png" alt="Front copper and silkscreen"> | <img src="images/pcb-back.png" alt="Back copper"> |

Gerbers are in [`fabrication/`](fabrication/), zipped and ready to upload.

---

## Repository layout

```
kicad/        KiCad 10 project — schematic, board, and the
              symbol/footprint libraries it depends on
ltspice/      Simulation deck, netlist, solver log, extracted results
fabrication/  Gerbers + zipped fab package
docs/         Project write-up and schematic PDF
images/       Every figure in this README — all generated, none hand-made
tools/        The scripts that generate them
```
