# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Render images/rope-bridge-solver-comparison-linkedin.png (2400 × 1350 px).

Top: the same 16 m bridge decked by the graph algorithm and by the Timefold
model with one entity per candidate pallet after 30 seconds. Bottom: the four
approaches on the longest benchmark bridges, from docs/benchmark/results.csv.
Needs the Timefold runner (make timefold) and the benchmark results.
"""

from __future__ import annotations

import csv
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt

from fixed_planks import random_instance, verify
from fixed_planks.cli import run_solver
from fixed_planks.draw import AXIS, GRID, INK, MUTED, SERIES, SURFACE, draw_plan
from fixed_planks.solution import BridgePlan

ROOT = Path(__file__).resolve().parent.parent
JAR = ROOT / "timefold" / "target" / "fixed-planks-timefold.jar"
RESULTS = ROOT / "docs" / "benchmark" / "results.csv"
OUTPUT = ROOT / "images" / "rope-bridge-solver-comparison-linkedin.png"
SECONDS = 30

# (label, solver in the results, colour — the same as in the notebook)
APPROACHES = (
    ("Timefold — one entity per candidate pallet", "timefold-pallets", SERIES[7]),
    ("Timefold — one entity per joint", "timefold-joints", SERIES[6]),
    ("MIP — flow model, SCIP", "scip-flow", SERIES[2]),
    ("Graph — two shortest paths", "graph", SERIES[0]),
)


def timefold_plan(instance, target: int) -> BridgePlan:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "bridge.json"
        instance.save(path)
        command = ["java", "-jar", str(JAR), "--instance", str(path), "--model", "pallets"]
        command += ["--seconds", str(SECONDS), "--target", str(target)]
        output = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    return BridgePlan.from_json(output.strip().splitlines()[-1])


def longest_bridges() -> tuple[int, dict[str, tuple[float, float]]]:
    """Length of the longest benchmark bridges and, per solver, (share above the optimum, seconds)."""
    with RESULTS.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    length = max(int(r["length"]) for r in rows)
    summary = {}
    for _, solver, _ in APPROACHES:
        mine = [r for r in rows if int(r["length"]) == length and r["solver"] == solver]
        above = statistics.mean((int(r["pallets"]) - int(r["optimum"])) / int(r["optimum"]) for r in mine)
        summary[solver] = (above, statistics.mean(float(r["seconds"]) for r in mine))
    return length, summary


def seconds_text(seconds: float) -> str:
    if seconds >= 10:
        return f"{seconds:.0f} s"
    if seconds >= 0.1:
        return f"{seconds:.1f} s"
    return f"{seconds * 1000:.0f} ms"


def main() -> None:
    if not JAR.exists():
        sys.exit(f"{JAR} is missing: run 'make timefold' first")
    bridge = random_instance(length=16000, seed=1)
    optimal = run_solver(bridge, "graph")
    stuck = timefold_plan(bridge, optimal.pallet_count)
    for plan in (optimal, stuck):
        assert verify(bridge, plan) == []
    length, summary = longest_bridges()

    plt.rcParams.update({"font.size": 17, "font.family": "DejaVu Sans"})
    fig = plt.figure(figsize=(16, 9), dpi=150, facecolor=SURFACE)
    fig.text(0.045, 0.925, "One planning problem, three ways to solve it", fontsize=34, color=INK, weight="bold")
    fig.text(
        0.045,
        0.872,
        "Deck a rope bridge in two lanes with the fewest pallets; joints of the two lanes never on the same plank.",
        fontsize=17,
        color=MUTED,
    )

    top = fig.add_axes((0.045, 0.645, 0.925, 0.15))
    draw_plan(bridge, optimal, top, title=f"Graph algorithm and MIP: {optimal.pallet_count} pallets — optimal, in milliseconds")
    middle = fig.add_axes((0.045, 0.41, 0.925, 0.15))
    draw_plan(
        bridge,
        stuck,
        middle,
        title=f"Timefold, one entity per candidate pallet, after {SECONDS} seconds: {stuck.pallet_count} pallets",
    )
    for ax in (top, middle):
        ax.set_xlabel("")
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
        ax.set_title(ax.get_title(loc="left"), loc="left", color=INK, fontsize=19, pad=10)
        for text in ax.texts:
            text.set_fontsize(15)

    bars = fig.add_axes((0.36, 0.05, 0.61, 0.25))
    bars.set_facecolor(SURFACE)
    labels = [label for label, _, _ in APPROACHES]
    values = [summary[solver][0] * 100 for _, solver, _ in APPROACHES]
    positions = range(len(APPROACHES))
    bars.barh(positions, values, height=0.6, color=[colour for _, _, colour in APPROACHES])
    for position, (_, solver, _), value in zip(positions, APPROACHES, values):
        above, seconds = summary[solver]
        result = "optimal" if above == 0 else f"{value:.0f} % above the optimum"
        limit = ", time limit" if seconds >= SECONDS else ""
        bars.text(value + 2, position, f"{result}  ·  {seconds_text(seconds)}{limit}", va="center", color=INK, fontsize=16)
    bars.set_yticks(positions, labels, color=INK, fontsize=16)
    bars.invert_yaxis()
    bars.set_xlim(0, max(values) * 2.1)
    bars.set_xticks([])
    for side in ("top", "right", "bottom"):
        bars.spines[side].set_visible(False)
    bars.spines["left"].set_color(AXIS)
    bars.tick_params(length=0)
    bars.grid(False)
    fig.text(
        0.045,
        0.335,
        f"The same on {length // 1000} m bridges: pallets above the optimum, and time",
        fontsize=19,
        color=INK,
    )
    fig.lines.append(plt.Line2D([0.045, 0.97], [0.385, 0.385], color=GRID, linewidth=1.2, transform=fig.transFigure))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=150, facecolor=SURFACE)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
