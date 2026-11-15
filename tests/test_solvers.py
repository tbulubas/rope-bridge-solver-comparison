# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

from __future__ import annotations

import pytest
from exhaustive import optimum, stock_optimum

from fixed_planks import BridgeInstance, BridgePlan, Status, random_instance, stock, verify, verify_cutting
from fixed_planks.cli import EXACT_SOLVERS, main, run_solver
from fixed_planks.graph import solve_sequential

EXAMPLE = BridgeInstance((0, 1000, 2000, 3000, 4000), 1000, 2000)


def test_candidates():
    assert EXAMPLE.candidates() == [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4)]


def test_json_round_trip(tmp_path):
    path = tmp_path / "instance.json"
    EXAMPLE.save(path)
    assert BridgeInstance.load(path) == EXAMPLE


def test_verify_accepts_valid_plan():
    plan = BridgePlan(Status.OPTIMAL, [(0, 2), (2, 4)], [(0, 1), (1, 3), (3, 4)])
    assert verify(EXAMPLE, plan) == []


@pytest.mark.parametrize(
    "left, right, message",
    [
        ([(0, 2), (2, 4)], [(0, 2), (2, 4)], "joints of both lanes"),
        ([(0, 2), (3, 4)], [(0, 1), (1, 3), (3, 4)], "hole or an overlap"),
        ([(0, 3), (3, 4)], [(0, 1), (1, 2), (2, 4)], "outside [m, M]"),
        ([(0, 2)], [(0, 1), (1, 3), (3, 4)], "must start on the first and end on the last"),
        ([], [(0, 2), (2, 4)], "has no pallets"),
    ],
)
def test_verify_rejects_invalid_plan(left, right, message):
    errors = verify(EXAMPLE, BridgePlan(Status.OPTIMAL, left, right))
    assert any(message in error for error in errors)


@pytest.mark.parametrize("solver", EXACT_SOLVERS)
def test_example(solver):
    plan = run_solver(EXAMPLE, solver)
    assert plan.status is Status.OPTIMAL
    assert verify(EXAMPLE, plan) == []
    assert plan.pallet_count == 5


@pytest.mark.parametrize("solver", EXACT_SOLVERS)
def test_single_full_length_pallet(solver):
    instance = BridgeInstance((0, 500, 1500), 1000, 2000)
    plan = run_solver(instance, solver)
    assert plan.status is Status.OPTIMAL
    assert plan.left == plan.right == [(0, 2)]


@pytest.mark.parametrize("solver", EXACT_SOLVERS)
def test_infeasible(solver):
    # Each lane needs the joint on plank 1.
    instance = BridgeInstance((0, 1000, 2000), 1000, 1000)
    assert run_solver(instance, solver).status is Status.INFEASIBLE


@pytest.mark.parametrize("solver", EXACT_SOLVERS)
@pytest.mark.parametrize("seed", range(40))
def test_matches_exhaustive_search(solver, seed):
    instance = random_instance(
        length=3000 + 150 * seed, min_gap=300, max_gap=700, min_pallet=600, max_pallet=1500, seed=seed
    )
    expected = optimum(instance)
    plan = run_solver(instance, solver)
    if expected is None:
        assert plan.status is Status.INFEASIBLE
    else:
        assert plan.status is Status.OPTIMAL
        assert verify(instance, plan) == []
        assert plan.pallet_count == expected


@pytest.mark.parametrize("seed", range(5))
def test_solvers_agree_on_reference_size(seed):
    instance = random_instance(seed=seed)
    counts = set()
    for solver in EXACT_SOLVERS:
        plan = run_solver(instance, solver)
        assert plan.status is Status.OPTIMAL
        assert verify(instance, plan) == []
        counts.add(plan.pallet_count)
    assert len(counts) == 1


@pytest.mark.parametrize("seed", range(40))
def test_sequential_is_valid_and_never_better(seed):
    instance = random_instance(
        length=3000 + 150 * seed, min_gap=300, max_gap=700, min_pallet=600, max_pallet=1500, seed=seed
    )
    expected = optimum(instance)
    plan = solve_sequential(instance, attempts=10**6)
    if expected is None:
        assert not plan.has_plan
    else:
        assert plan.status is Status.FEASIBLE
        assert verify(instance, plan) == []
        assert plan.pallet_count >= expected


def test_sequential_example():
    plan = solve_sequential(EXAMPLE)
    assert verify(EXAMPLE, plan) == []
    assert plan.pallet_count == 5


def test_sequential_gives_up_after_its_attempts():
    # The shortest left lane 0-2-4 leaves 0-1-3-4 for the right lane.
    assert solve_sequential(EXAMPLE, attempts=1).has_plan
    assert solve_sequential(BridgeInstance((0, 1000, 2000), 1000, 1000)).status is Status.UNKNOWN
    assert solve_sequential(BridgeInstance((0, 500, 3000), 1000, 2000)).status is Status.INFEASIBLE


@pytest.mark.parametrize("backend", ["cpsat", "scip"])
@pytest.mark.parametrize("seed", range(25))
def test_stock_matches_exhaustive_search(backend, seed):
    instance = random_instance(
        length=3000 + 120 * seed, min_gap=300, max_gap=700, min_pallet=600, max_pallet=1500, seed=seed
    )
    expected = stock_optimum(instance)
    plan = stock.solve(instance, backend)
    if expected is None:
        assert plan.status is Status.INFEASIBLE
    else:
        assert plan.status is Status.OPTIMAL
        assert verify(instance, plan) == [] and verify_cutting(instance, plan) == []
        assert (len(plan.stock), plan.pallet_count) == expected


@pytest.mark.parametrize("seed", range(3))
def test_stock_never_needs_more_pieces_than_cutting_the_shortest_plan(seed):
    instance = random_instance(length=12000, seed=seed)
    reference = run_solver(instance, "graph-stock")
    plans = [run_solver(instance, solver) for solver in ("scip-stock", "cpsat-stock")]
    for candidate in (reference, *plans):
        assert verify(instance, candidate) == [] and verify_cutting(instance, candidate) == []
    assert len(plans[0].stock) == len(plans[1].stock) <= len(reference.stock)
    assert len(plans[0].stock) >= -(-2 * instance.length // instance.max_pallet)


def test_verify_cutting_rejects_wrong_cutting():
    plan = BridgePlan(Status.OPTIMAL, [(0, 2), (2, 4)], [(0, 1), (1, 3), (3, 4)])
    plan.stock = [[(0, 2)], [(2, 4)], [(0, 1), (1, 3)]]
    assert any("not the pallets of the plan" in e for e in verify_cutting(EXAMPLE, plan))
    plan.stock = [[(0, 2), (2, 4)], [(0, 1), (3, 4)], [(1, 3)]]
    assert any("more than its length" in e for e in verify_cutting(EXAMPLE, plan))
    plan.stock = [[(0, 2)], [(2, 4)], [(0, 1), (3, 4)], [(1, 3)]]
    assert verify_cutting(EXAMPLE, plan) == []


def test_cli(capsys):
    main(["--length", "8000", "--seed", "3", "--solver", "scip-flow"])
    assert "Plan verified." in capsys.readouterr().out
