#!/usr/bin/env python3
"""Plot the 200-run Monte Carlo results for the blink oscillator.

Two figures:
  images/montecarlo-waveforms.png         V(vout) for every tolerance draw
  images/montecarlo-period-histogram.png  distribution of the measured period

The measured periods come from ltspice/montecarlo.log (committed, small). The
waveforms come from LTspice's exported .txt, which is ~11 MB and deliberately
NOT committed -- pass its path, or re-export it from LTspice, to redraw the
ensemble. If it is missing, the histogram is still produced.
"""
import argparse
import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parent.parent

# dataviz reference palette, dark surface -- categorical slots 1 (blue) and 2 (orange)
SURFACE = "#1a1a19"
INK = "#ffffff"
INK_DIM = "#c3c2b7"
GRID = "#383835"
SERIES_1 = "#3987e5"
SERIES_2 = "#d95926"

THRESHOLD = 1.65  # V, the .meas TRIG/TARG crossing level

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK,
    "axes.labelcolor": INK_DIM, "xtick.color": INK_DIM, "ytick.color": INK_DIM,
    "axes.edgecolor": GRID, "grid.color": GRID,
    "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "semibold",
})


def read_periods(log: Path) -> np.ndarray:
    """Pull the .meas tperiod column out of the LTspice log."""
    rows, capture = [], False
    for line in log.read_text(errors="replace").splitlines():
        if line.startswith("Measurement: tperiod"):
            capture = True
            continue
        if capture:
            m = re.match(r"\s*(\d+)\s+([\d.eE+-]+)\s", line)
            if m:
                rows.append(float(m.group(2)))
            elif rows:
                break
    return np.array(rows)


def read_waveforms(txt: Path):
    """Parse LTspice's stepped .txt export into (time, vout) arrays per run."""
    runs, t, v = [], [], []
    with txt.open() as fh:
        next(fh)  # column header
        for line in fh:
            if line.startswith("Step Information"):
                if t:
                    runs.append((np.array(t), np.array(v)))
                    t, v = [], []
                continue
            a, _, b = line.partition("\t")
            try:
                t.append(float(a)); v.append(float(b))
            except ValueError:
                continue
    if t:
        runs.append((np.array(t), np.array(v)))
    return runs


def style(ax):
    ax.grid(True, linewidth=0.8, alpha=0.5)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_linewidth(1.0)


def plot_waveforms(runs, periods, out: Path):
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)

    for t, v in runs:
        ax.plot(t, v, color=SERIES_1, linewidth=0.6, alpha=0.06)

    # highlight the run whose period is closest to the median
    mid = int(np.argmin(np.abs(periods - np.median(periods)))) if len(periods) else 0
    if mid < len(runs):
        t, v = runs[mid]
        ax.plot(t, v, color=SERIES_2, linewidth=2.0,
                label=f"median run (#{mid + 1}, {periods[mid]:.3f} s)")

    ax.axhline(THRESHOLD, color=INK_DIM, linewidth=1.2, linestyle=(0, (5, 4)),
               alpha=0.7, label=f"comparator threshold, {THRESHOLD} V")
    ax.plot([], [], color=SERIES_1, linewidth=2, alpha=0.5,
            label=f"{len(runs)} tolerance draws")

    ax.set_xlabel("time (s)")
    ax.set_ylabel("V(vout)  (V)")
    ax.set_title("LED drive across 200 Monte Carlo tolerance draws", color=INK, pad=14)
    ax.set_xlim(0, max(t.max() for t, _ in runs))
    ax.set_ylim(-0.15, 3.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3,
              frameon=False, labelcolor=INK_DIM, fontsize=10)
    style(ax)
    fig.text(0.011, 0.02,
             "Edges fan out with each draw — the oscillation itself never fails to start.",
             color=INK_DIM, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.095, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    print(f"{out.name}")


def plot_histogram(periods: np.ndarray, out: Path):
    mean, sd = periods.mean(), periods.std(ddof=1)
    fig, ax = plt.subplots(figsize=(11, 5.0), dpi=150)

    n, bins, patches = ax.hist(periods, bins=26, color=SERIES_1,
                               edgecolor=SURFACE, linewidth=2.0)

    ax.axvline(mean, color=SERIES_2, linewidth=2.0)
    ax.annotate(f"mean {mean:.3f} s", xy=(mean, n.max()),
                xytext=(6, -4), textcoords="offset points",
                color=SERIES_2, fontsize=11, fontweight="semibold", va="top")

    ax.set_xlabel("blink period (s)")
    ax.set_ylabel("runs")
    ax.set_title("Blink period spread from 1 % resistors and a 5 % capacitor",
                 color=INK, pad=14)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    style(ax)

    spread = (periods.max() - periods.min()) / mean * 100
    fig.text(0.011, 0.02,
             f"n = {len(periods)}    σ = {sd * 1000:.1f} ms ({sd / mean * 100:.1f} %)    "
             f"range {periods.min():.3f}–{periods.max():.3f} s ({spread:.1f} % of mean)",
             color=INK_DIM, fontsize=9.5)
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(out)
    plt.close(fig)
    print(f"{out.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=ROOT / "ltspice" / "montecarlo.log")
    ap.add_argument("--waveforms", type=Path, default=Path(
        r"C:\Users\pbonthu\OneDrive - Olin College of Engineering"
        r"\Documents\LTspice\eclectronicsmp12.txt"))
    args = ap.parse_args()

    periods = read_periods(args.log)
    if periods.size == 0:
        raise SystemExit(f"no tperiod measurements found in {args.log}")

    csv_path = ROOT / "ltspice" / "tperiod-montecarlo.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "period_s"])
        w.writerows((i, f"{p:.9f}") for i, p in enumerate(periods, 1))
    print(f"{csv_path.name}: {len(periods)} rows")

    images = ROOT / "images"
    plot_histogram(periods, images / "montecarlo-period-histogram.png")

    if args.waveforms.exists():
        runs = read_waveforms(args.waveforms)
        plot_waveforms(runs, periods, images / "montecarlo-waveforms.png")
    else:
        print(f"skipped waveforms: {args.waveforms} not found")


if __name__ == "__main__":
    main()
