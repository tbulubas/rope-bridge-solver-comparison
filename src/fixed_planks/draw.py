# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Pictures of a bridge plan and of its cutting (matplotlib, extra "plot")."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from fixed_planks.instance import BridgeInstance
from fixed_planks.solution import BridgePlan

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#898781"
AXIS = "#c3c2b7"
GRID = "#e1e0d9"
# Categorical colours in a fixed order; a solver keeps its colour in every chart.
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
LANE_COLOURS = {"left": SERIES[0], "right": SERIES[1]}


def style(ax: Axes) -> None:
    """Quiet axes: no box, light grid behind the marks."""
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def draw_plan(instance: BridgeInstance, plan: BridgePlan, ax: Axes | None = None, title: str | None = None) -> Axes:
    """The deck from above: planks as lines, the pallets of both lanes as bars.

    Gaps between the bars are the joints; a joint never faces a joint of the
    other lane.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 1.9))
    ax.set_facecolor(SURFACE)
    planks = instance.planks
    seam = instance.length * 0.0025
    for position in planks:
        ax.plot([position, position], [-0.08, 2.08], color=AXIS, linewidth=0.8, zorder=1)
    for row, (name, lane) in enumerate((("right", plan.right), ("left", plan.left))):
        for a, b in lane:
            ax.add_patch(
                Rectangle(
                    (planks[a] + seam, row + 0.14),
                    planks[b] - planks[a] - 2 * seam,
                    0.72,
                    facecolor=LANE_COLOURS[name],
                    edgecolor="none",
                    alpha=0.9,
                    zorder=2,
                )
            )
        ax.text(-instance.length * 0.012, row + 0.5, name, ha="right", va="center", color=INK, fontsize=9)
    ax.set_xlim(-instance.length * 0.06, instance.length * 1.01)
    ax.set_ylim(-0.15, 2.15)
    ax.set_yticks([])
    ax.set_xlabel("position (mm)", color=MUTED)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_title(title or f"{plan.pallet_count} pallets", loc="left", color=INK, fontsize=10)
    return ax


def draw_cutting(instance: BridgeInstance, plan: BridgePlan, ax: Axes | None = None, title: str | None = None) -> Axes:
    """One bar per stock piece: the pallets cut from it and, hatched, what is left."""
    pieces = plan.stock
    if ax is None:
        _, ax = plt.subplots(figsize=(5.5, 0.28 * len(pieces) + 0.9))
    ax.set_facecolor(SURFACE)
    planks = instance.planks
    stock = instance.max_pallet
    lane_of = {p: "left" for p in plan.left} | {p: "right" for p in plan.right}
    seam = stock * 0.006
    waste = 0
    for row, piece in enumerate(pieces):
        at = 0
        for a, b in sorted(piece, key=lambda p: planks[p[0]] - planks[p[1]]):
            length = planks[b] - planks[a]
            ax.add_patch(
                Rectangle((at + seam, row + 0.15), length - 2 * seam, 0.7, facecolor=LANE_COLOURS[lane_of[(a, b)]],
                          edgecolor="none", alpha=0.9)
            )
            at += length
        if at < stock:
            ax.add_patch(
                Rectangle((at + seam, row + 0.15), stock - at - 2 * seam, 0.7, facecolor="none", edgecolor=MUTED,
                          hatch="////", linewidth=0.6)
            )
            waste += stock - at
    ax.set_xlim(0, stock)
    ax.set_ylim(len(pieces) + 0.1, -0.1)
    ax.set_yticks([])
    ax.set_xlabel("stock piece (mm)", color=MUTED)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, length=0)
    share = waste / (stock * len(pieces)) if pieces else 0
    ax.set_title(title or f"{len(pieces)} stock pieces, {share:.0%} waste", loc="left", color=INK, fontsize=10)
    return ax
