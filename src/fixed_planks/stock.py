# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Extension: pallets are cut from stock pieces, minimise the stock pieces.

See docs/problem-statement.md, "Extension", and docs/mip-model.md, "Model C".
Constraint numbers refer to docs/mip-model.md.

solve() decides the pallets and their cutting together. pack() is the
reference: it takes a finished plan and only cuts it (first fit decreasing).
"""

from __future__ import annotations

import math
from dataclasses import replace

from ortools.linear_solver import pywraplp

from fixed_planks import graph
from fixed_planks.model import create_solver
from fixed_planks.instance import BridgeInstance, Pallet
from fixed_planks.solution import BridgePlan, Status, lanes_from_pallets


def first_fit_decreasing(instance: BridgeInstance, pallets: list[Pallet]) -> list[list[Pallet]]:
    """Cut the pallets from stock pieces: longest first, into the first piece with room."""
    planks = instance.planks
    pieces: list[list[Pallet]] = []
    room: list[int] = []
    for pallet in sorted(pallets, key=lambda p: planks[p[0]] - planks[p[1]]):
        length = planks[pallet[1]] - planks[pallet[0]]
        for k, free in enumerate(room):
            if length <= free:
                pieces[k].append(pallet)
                room[k] -= length
                break
        else:
            pieces.append([pallet])
            room.append(instance.max_pallet - length)
    return pieces


def pack(instance: BridgeInstance, plan: BridgePlan) -> BridgePlan:
    """The same plan with its pallets cut by first fit decreasing."""
    if not plan.has_plan:
        return plan
    return replace(plan, status=Status.FEASIBLE, stock=first_fit_decreasing(instance, plan.left + plan.right))


def solve(instance: BridgeInstance, backend: str = "scip", time_limit: float | None = None) -> BridgePlan:
    """Model C: fewest stock pieces, then fewest pallets.

    The same model goes to SCIP (backend "scip") or to CP-SAT (backend "cpsat").
    """
    reference = pack(instance, graph.solve(instance))
    if not reference.has_plan:
        return BridgePlan(Status.INFEASIBLE)
    solver = create_solver(backend, time_limit)

    planks = instance.planks
    last = instance.last
    stock = instance.max_pallet
    pallets = instance.candidates()
    length = {p: planks[p[1]] - planks[p[0]] for p in pallets}
    most = {p: 2 if p == (0, last) else 1 for p in pallets}
    # The reference plan needs len(reference.stock) pieces, so more are never used.
    pieces = range(len(reference.stock))
    lower_bound = math.ceil(2 * instance.length / stock)

    f = {p: solver.IntVar(0, most[p], f"f[{p[0]},{p[1]}]") for p in pallets}
    x = {(p, k): solver.IntVar(0, most[p], f"x[{p[0]},{p[1]},{k}]") for p in pallets for k in pieces}
    u = {k: solver.IntVar(1 if k < lower_bound else 0, 1, f"u[{k}]") for k in pieces}

    starting: dict[int, list[Pallet]] = {j: [] for j in range(last + 1)}
    ending: dict[int, list[Pallet]] = {j: [] for j in range(last + 1)}
    for a, b in pallets:
        starting[a].append((a, b))
        ending[b].append((a, b))

    # (4)–(6) of model B: the pallets form two lanes with staggered joints.
    solver.Add(sum(f[p] for p in starting[0]) == 2)
    solver.Add(sum(f[p] for p in ending[last]) == 2)
    for j in range(1, last):
        solver.Add(sum(f[p] for p in ending[j]) == sum(f[p] for p in starting[j]))
        if ending[j]:
            solver.Add(sum(f[p] for p in ending[j]) <= 1)

    # (7) every laid pallet is cut from one stock piece.
    for p in pallets:
        solver.Add(sum(x[p, k] for k in pieces) == f[p])
    for k in pieces:
        # (8) the pallets cut from a piece fit into its length, and only used pieces are cut.
        solver.Add(sum(length[p] * x[p, k] for p in pallets) <= stock * u[k])
        # (9) symmetry breaking: pieces are used in order.
        if k > 0:
            solver.Add(u[k - 1] >= u[k])

    # Stock pieces first; a piece outweighs any number of pallets.
    weight = 2 * last + 1
    solver.Minimize(weight * sum(u.values()) + sum(f.values()))
    result = solver.Solve()
    if result not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        # The reference plan is always available.
        return reference
    laid = [p for p in pallets for _ in range(round(f[p].solution_value()))]
    left, right = lanes_from_pallets(instance, laid)
    cut = [[p for p in pallets for _ in range(round(x[p, k].solution_value()))] for k in pieces]
    status = Status.OPTIMAL if result == pywraplp.Solver.OPTIMAL else Status.FEASIBLE
    return BridgePlan(status, left, right, [piece for piece in cut if piece])
