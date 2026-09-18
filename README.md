# Eclectronics Mini-Project 1
Final right up can be found here: docs/Electronics-Mini-Project-1.pdf
<p align="center">
  <img src="images/pcb-3d-iso.png" alt="3D render of the assembled board" width="90%">
</p>

---

## Simulation

<p align="center">
  <img src="images/ltspice-schematic.png" alt="LTspice schematic" width="90%">
</p>

200-run Monte Carlo over 1 % resistor and 5 % capacitor tolerances:

<p align="center">
  <img src="images/ltspice-simulation.png" alt="V(vout) across 200 Monte Carlo runs" width="68%">
</p>

---

## Schematic

<p align="center">
  <img src="images/kicad-schematic.png" alt="KiCad schematic" width="94%">
</p>

PDF: [`docs/kicad-schematic.pdf`](docs/kicad-schematic.pdf)

---

## The board


| Top | Bottom |
|---|---|
| <img src="images/pcb-3d-top.png" alt="Top of the board"> | <img src="images/pcb-3d-bottom.png" alt="Bottom of the board"> |


| Front (F.Cu ) | Back (B.Cu) |
|---|---|
| <img src="images/pcb-front.png" alt="Front copper and silkscreen"> | <img src="images/pcb-back.png" alt="Back copper"> |


---

## Repository layout

```
kicad/        KiCad 10 project: schematic, board, and the
              symbol/footprint libraries it depends on
ltspice/      Simulation and results
fabrication/  Gerbers 
docs/         Project write-up and schematic PDF
images/       Images for the README    
```
