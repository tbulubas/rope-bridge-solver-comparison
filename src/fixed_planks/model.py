# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""MIP models of the rope bridge with fixed planks, solved with SCIP or CP-SAT (OR-Tools).

Both solvers get the same model through the same OR-Tools interface.

Constraint numbers refer to docs/mip-model.md.
"""

from __future__ import annotations

from ortools.linear_solver import pywraplp

from fixed_planks.instance import BridgeInstance
from fixed_planks.solution import BridgePlan, Status, lanes_from_pallets

LANES = ("l", "r")
FORMULATIONS = ("cover", "flow")
BACKENDS = {"scip": "SCIP", "cpsat": "SAT"}

_STATUS = {
    pywraplp.Solver.OPTIMAL: Status.OPTIMAL,
    pywraplp.Solver.FEASIBLE: Status.FEASIBLE,
    pywraplp.Solver.INFEASIBLE: Status.INFEASIBLE,
}


def create_solver(backend: str, time_limit: float | None) -> pywraplp.Solver:
    solver = pywraplp.Solver.CreateSolver(BACKENDS[backend])
    if solver is None:
        raise RuntimeError(f"solver {backend} is not available in this OR-Tools build")
    if time_limit is not None:
        solver.SetTimeLimit(int(time_limit * 1000))
    return solver


def solve_cover(
    instance: BridgeInstance, time_limit: float | None = None, lane_symmetry: bool = True, backend: str = "scip"
) -> BridgePlan:
    """Model A: exact cover of the gaps in each lane."""
    solver = create_solver(backend, time_limit)
    last = instance.last
    pallets = instance.candidates()
    z = {(lane, p): solver.BoolVar(f"z[{lane},{p[0]},{p[1]}]") for lane in LANES for p in pallets}

    # (1) every gap is covered by exactly one pallet in each lane.
    covering: dict[int, list[tuple[int, int]]] = {k: [] for k in range(1, last + 1)}
    for a, b in pallets:
        for k in range(a + 1, b + 1):
            covering[k].append((a, b))
    for lane in LANES:
        for k in range(1, last + 1):
            solver.Add(sum(z[lane, p] for p in covering[k]) == 1)

    # (2) an interior plank carries the joint of at most one lane.
    ending: dict[int, list[tuple[int, int]]] = {j: [] for j in range(1, last)}
    for a, b in pallets:
        if b < last:
            ending[b].append((a, b))
    for j in range(1, last):
        if ending[j]:
            solver.Add(sum(z[lane, p] for lane in LANES for p in ending[j]) <= 1)

    # (3) symmetry breaking: the left lane has no more pallets than the right one.
    if lane_symmetry:
        solver.Add(sum(z["l", p] for p in pallets) <= sum(z["r", p] for p in pallets))

    solver.Minimize(sum(z.values()))
    status = _STATUS.get(solver.Solve(), Status.UNKNOWN)
    if status not in (Status.OPTIMAL, Status.FEASIBLE):
        return BridgePlan(status)
    lanes = [[p for p in pallets if z[lane, p].solution_value() > 0.5] for lane in LANES]
    return BridgePlan(status, lanes[0], lanes[1])


def solve_flow(instance: BridgeInstance, time_limit: float | None = None, backend: str = "scip") -> BridgePlan:
    """Model B: one variable per pallet, a flow of two units along the bridge."""
    solver = create_solver(backend, time_limit)
    last = instance.last
    pallets = instance.candidates()
    f = {p: solver.IntVar(0, 2 if p == (0, last) else 1, f"f[{p[0]},{p[1]}]") for p in pallets}

    starting: dict[int, list[tuple[int, int]]] = {j: [] for j in range(last + 1)}
    ending: dict[int, list[tuple[int, int]]] = {j: [] for j in range(last + 1)}
    for a, b in pallets:
        starting[a].append((a, b))
        ending[b].append((a, b))

    # (4) two pallets start on the first plank and two end on the last one.
    solver.Add(sum(f[p] for p in starting[0]) == 2)
    solver.Add(sum(f[p] for p in ending[last]) == 2)
    for j in range(1, last):
        # (5) a pallet that ends on an interior plank is followed by one that starts there.
        solver.Add(sum(f[p] for p in ending[j]) == sum(f[p] for p in starting[j]))
        # (6) at most one pallet ends on an interior plank.
        if ending[j]:
            solver.Add(sum(f[p] for p in ending[j]) <= 1)

    solver.Minimize(sum(f.values()))
    status = _STATUS.get(solver.Solve(), Status.UNKNOWN)
    if status not in (Status.OPTIMAL, Status.FEASIBLE):
        return BridgePlan(status)
    laid = [p for p in pallets for _ in range(round(f[p].solution_value()))]
    left, right = lanes_from_pallets(instance, laid)
    return BridgePlan(status, left, right)


def solve(
    instance: BridgeInstance, formulation: str = "flow", time_limit: float | None = None, backend: str = "scip"
) -> BridgePlan:
    """Solve with the given formulation, "cover" (model A) or "flow" (model B)."""
    if formulation == "cover":
        return solve_cover(instance, time_limit, backend=backend)
    if formulation == "flow":
        return solve_flow(instance, time_limit, backend)
    raise ValueError(f"unknown formulation {formulation!r}")
