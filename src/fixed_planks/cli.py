# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Command line interface: generate or load an instance, solve it, print the plan."""

from __future__ import annotations

import argparse
import time

from fixed_planks import graph, model, stock
from fixed_planks.instance import BridgeInstance, random_instance
from fixed_planks.solution import BridgePlan, verify, verify_cutting

EXACT_SOLVERS = ("graph", "scip-flow", "cpsat-flow", "scip-cover", "cpsat-cover")
STOCK_SOLVERS = ("graph-stock", "scip-stock", "cpsat-stock")
SOLVERS = (*EXACT_SOLVERS, "graph-sequential", *STOCK_SOLVERS)


def run_solver(instance: BridgeInstance, solver: str, time_limit: float | None = None) -> BridgePlan:
    if solver == "graph":
        return graph.solve(instance)
    if solver == "graph-sequential":
        return graph.solve_sequential(instance)
    if solver == "graph-stock":
        return stock.pack(instance, graph.solve(instance))
    backend, _, formulation = solver.partition("-")
    if backend in model.BACKENDS and formulation == "stock":
        return stock.solve(instance, backend, time_limit)
    if backend in model.BACKENDS and formulation in model.FORMULATIONS:
        return model.solve(instance, formulation, time_limit, backend)
    raise ValueError(f"unknown solver {solver!r}")


def _lane_text(instance: BridgeInstance, lane: list[tuple[int, int]]) -> str:
    if not lane:
        return "-"
    positions = [instance.planks[lane[0][0]]] + [instance.planks[b] for _, b in lane]
    return " — ".join(f"{p:,}".replace(",", " ") for p in positions)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="fixed_planks", description="Deck a rope bridge with fixed planks using the fewest pallets."
    )
    parser.add_argument("--load", metavar="FILE", help="read the instance from a JSON file")
    parser.add_argument("--save", metavar="FILE", help="write the instance to a JSON file")
    parser.add_argument("-L", "--length", type=int, default=16000, help="bridge length in mm")
    parser.add_argument("--min-gap", type=int, default=400, help="minimal plank distance in mm")
    parser.add_argument("--max-gap", type=int, default=700, help="maximal plank distance in mm")
    parser.add_argument("-m", "--min-pallet", type=int, default=600, help="minimal pallet length in mm")
    parser.add_argument("-M", "--max-pallet", type=int, default=2600, help="maximal pallet length in mm")
    parser.add_argument("--seed", type=int, default=0, help="seed of the random plank positions")
    parser.add_argument("--solver", choices=SOLVERS, default="graph")
    parser.add_argument("--time-limit", type=float, default=None, help="seconds, MIP solvers only")
    args = parser.parse_args(argv)

    if args.load:
        instance = BridgeInstance.load(args.load)
    else:
        instance = random_instance(
            args.length, args.min_gap, args.max_gap, args.min_pallet, args.max_pallet, args.seed
        )
    if args.save:
        instance.save(args.save)

    print(
        f"Bridge L = {instance.length} mm, {len(instance.planks)} planks, "
        f"{len(instance.candidates())} candidate pallets of {instance.min_pallet}–{instance.max_pallet} mm"
    )
    started = time.perf_counter()
    plan = run_solver(instance, args.solver, args.time_limit)
    elapsed = time.perf_counter() - started
    print(f"Solver {args.solver}: {plan.status.value} in {elapsed * 1000:.1f} ms")
    if not plan.has_plan:
        return
    print(f"Pallets: {plan.pallet_count} ({len(plan.left)} left, {len(plan.right)} right)")
    print(f"  left:  {_lane_text(instance, plan.left)}")
    print(f"  right: {_lane_text(instance, plan.right)}")
    errors = verify(instance, plan)
    if plan.stock:
        print(f"Stock pieces of {instance.max_pallet} mm: {len(plan.stock)}")
        for piece in plan.stock:
            lengths = [instance.planks[b] - instance.planks[a] for a, b in piece]
            print(f"  {' + '.join(map(str, lengths))} = {sum(lengths)}")
        errors += verify_cutting(instance, plan)
    print("Plan verified." if not errors else "INVALID PLAN:\n  " + "\n  ".join(errors))
