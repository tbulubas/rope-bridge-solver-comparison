# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Bridge plan returned by the solvers and an independent feasibility check."""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field

from fixed_planks.instance import BridgeInstance, Pallet


class Status(enum.Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"


@dataclass
class BridgePlan:
    """Result of one solver run.

    Attributes:
        status: solver status.
        left: pallets of the left lane as (start plank, end plank), in order.
        right: pallets of the right lane, in order.
        stock: the pallets cut from each stock piece; empty when the plan has
            no cutting (see the extension in docs/problem-statement.md).
    """

    status: Status
    left: list[Pallet] = field(default_factory=list)
    right: list[Pallet] = field(default_factory=list)
    stock: list[list[Pallet]] = field(default_factory=list)

    @property
    def has_plan(self) -> bool:
        return self.status in (Status.OPTIMAL, Status.FEASIBLE)

    @property
    def pallet_count(self) -> int:
        return len(self.left) + len(self.right)

    @staticmethod
    def from_json(text: str) -> BridgePlan:
        """Plan written by the Timefold runner: {"status", "left", "right"}."""
        data = json.loads(text)
        return BridgePlan(
            Status(data["status"]),
            sorted((a, b) for a, b in data["left"]),
            sorted((a, b) for a, b in data["right"]),
        )


def lanes_from_pallets(instance: BridgeInstance, pallets: list[Pallet]) -> tuple[list[Pallet], list[Pallet]]:
    """Split the pallets of a plan into two lanes by following them from plank 0.

    `pallets` holds every laid pallet once; the full-length pallet (0, n)
    appears twice when both lanes use it.
    """
    starts: dict[int, list[Pallet]] = {}
    for pallet in sorted(pallets):
        starts.setdefault(pallet[0], []).append(pallet)
    lanes: list[list[Pallet]] = []
    for _ in range(2):
        lane = []
        at = 0
        while at != instance.last:
            pallet = starts[at].pop()
            lane.append(pallet)
            at = pallet[1]
        lanes.append(lane)
    if any(starts.values()):
        raise ValueError("pallets do not form two lanes")
    return lanes[0], lanes[1]


def verify(instance: BridgeInstance, plan: BridgePlan) -> list[str]:
    """Check a plan against the rules of the problem statement.

    Independent of every solver. Returns a list of violated rules; an empty
    list means the plan is valid.
    """
    errors: list[str] = []
    planks = instance.planks
    joints: dict[str, set[int]] = {}
    for name, lane in (("left", plan.left), ("right", plan.right)):
        if not lane:
            errors.append(f"{name} lane has no pallets")
            continue
        if lane[0][0] != 0 or lane[-1][1] != instance.last:
            errors.append(f"{name} lane must start on the first and end on the last plank")
        for (_, end), (start, _) in zip(lane, lane[1:]):
            if end != start:
                errors.append(f"{name} lane has a hole or an overlap between planks {end} and {start}")
        for a, b in lane:
            if not 0 <= a < b <= instance.last:
                errors.append(f"{name} pallet {a}-{b} does not lie on planks of the bridge")
                continue
            span = planks[b] - planks[a]
            if not instance.min_pallet <= span <= instance.max_pallet:
                errors.append(f"{name} pallet {a}-{b} has length {span} outside [m, M]")
        joints[name] = {end for _, end in lane[:-1]}

    for j in sorted(joints.get("left", set()) & joints.get("right", set())):
        errors.append(f"joints of both lanes lie on plank {j}")
    return errors


def verify_cutting(instance: BridgeInstance, plan: BridgePlan) -> list[str]:
    """Check the cutting of a plan: every pallet is cut once and every stock piece is long enough."""
    errors: list[str] = []
    planks = instance.planks
    if sorted(p for piece in plan.stock for p in piece) != sorted(plan.left + plan.right):
        errors.append("the pallets cut from the stock pieces are not the pallets of the plan")
    for number, piece in enumerate(plan.stock, start=1):
        used = sum(planks[b] - planks[a] for a, b in piece)
        if not piece:
            errors.append(f"stock piece {number} is not cut")
        if used > instance.max_pallet:
            errors.append(f"stock piece {number} is cut into {used}, more than its length")
    return errors
