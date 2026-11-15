# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Exhaustive search over all pairs of lanes, for tiny instances only."""

from __future__ import annotations

from fixed_planks.instance import BridgeInstance, Pallet


def all_lanes(instance: BridgeInstance) -> list[list[Pallet]]:
    """Every way to cover one lane from the first to the last plank."""
    starting: dict[int, list[Pallet]] = {}
    for pallet in instance.candidates():
        starting.setdefault(pallet[0], []).append(pallet)
    lanes: list[list[Pallet]] = []

    def extend(at: int, lane: list[Pallet]) -> None:
        if at == instance.last:
            lanes.append(list(lane))
            return
        for pallet in starting.get(at, []):
            lane.append(pallet)
            extend(pallet[1], lane)
            lane.pop()

    extend(0, [])
    return lanes


def fewest_pieces(lengths: list[int], stock: int) -> int:
    """Fewest stock pieces the lengths can be cut from, by trying every assignment."""
    best = len(lengths)
    room: list[int] = []

    def place(index: int) -> None:
        nonlocal best
        if len(room) >= best:
            return
        if index == len(lengths):
            best = len(room)
            return
        for k in range(len(room)):
            if lengths[index] <= room[k]:
                room[k] -= lengths[index]
                place(index + 1)
                room[k] += lengths[index]
        room.append(stock - lengths[index])
        place(index + 1)
        room.pop()

    place(0)
    return best


def stock_optimum(instance: BridgeInstance) -> tuple[int, int] | None:
    """Fewest stock pieces and, with that many, fewest pallets; None without a valid plan."""
    planks = instance.planks
    lanes = [(lane, {b for _, b in lane[:-1]}) for lane in all_lanes(instance)]
    best = None
    for left, left_joints in lanes:
        for right, right_joints in lanes:
            if left_joints & right_joints:
                continue
            lengths = sorted((planks[b] - planks[a] for a, b in left + right), reverse=True)
            value = (fewest_pieces(lengths, instance.max_pallet), len(left) + len(right))
            if best is None or value < best:
                best = value
    return best


def optimum(instance: BridgeInstance) -> int | None:
    """Fewest pallets of a valid plan, or None when no valid plan exists."""
    lanes = [(lane, {b for _, b in lane[:-1]}) for lane in all_lanes(instance)]
    best = None
    for left, left_joints in lanes:
        for right, right_joints in lanes:
            if left_joints & right_joints:
                continue
            count = len(left) + len(right)
            if best is None or count < best:
                best = count
    return best
