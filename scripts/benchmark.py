# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Benchmark: both graph algorithms, both MIP models and both Timefold models.

Usage: python scripts/benchmark.py [--part all|solvers|stock] [--lengths 16000,32000] [--seeds 3] [--seconds 30]

Every instance is solved by the two-lane graph algorithm first; its pallet count is the
optimum and the target of the Timefold runs, which stop as soon as they reach
it or when the time limit is over. Every plan is checked with verify().
Results go to docs/benchmark/results.csv and the tables to docs/benchmark.md.

The stock part compares, for the extension with stock pieces, cutting the
plan with the fewest pallets afterwards (graph-stock) with deciding pallets
and cutting together (model C with SCIP and with CP-SAT); results in docs/benchmark/stock.csv.
Build the Timefold runner first: make timefold.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fixed_planks import BridgeInstance, random_instance, verify, verify_cutting
from fixed_planks.cli import run_solver
from fixed_planks.solution import BridgePlan

ROOT = Path(__file__).resolve().parent.parent
JAR = ROOT / "timefold" / "target" / "fixed-planks-timefold.jar"
CSV_PATH = ROOT / "docs" / "benchmark" / "results.csv"
STOCK_CSV_PATH = ROOT / "docs" / "benchmark" / "stock.csv"
REPORT_PATH = ROOT / "docs" / "benchmark.md"

PYTHON_SOLVERS = ("graph", "graph-sequential", "scip-flow", "cpsat-flow", "scip-cover", "cpsat-cover")
TIMEFOLD_MODELS = ("joints", "pallets")
SOLVERS = (*PYTHON_SOLVERS, *(f"timefold-{model}" for model in TIMEFOLD_MODELS))
STOCK_FIELDS = (
    "length", "seed", "candidates", "lower_bound", "graph_pieces", "graph_pallets",
    "scip_pieces", "scip_pallets", "scip_status", "scip_seconds",
    "cpsat_pieces", "cpsat_pallets", "cpsat_status", "cpsat_seconds",
)
FIELDS = ("length", "seed", "planks", "candidates", "optimum", "solver", "status", "pallets", "seconds", "valid")


def solve_python(instance: BridgeInstance, solver: str) -> tuple[BridgePlan, float]:
    started = time.perf_counter()
    plan = run_solver(instance, solver)
    return plan, time.perf_counter() - started


def solve_timefold(path: Path, model: str, seconds: float, target: int) -> tuple[BridgePlan, float]:
    """Run the Timefold model; the time is the solver's own, without JVM start-up."""
    command = ["java", "-jar", str(JAR), "--instance", str(path), "--model", model]
    command += ["--seconds", str(seconds), "--target", str(target)]
    output = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    text = output.strip().splitlines()[-1]
    return BridgePlan.from_json(text), json.loads(text)["solve_ms"] / 1000


def run(lengths: list[int], seeds: int, seconds: float) -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for length in lengths:
            for seed in range(seeds):
                instance = random_instance(length=length, seed=seed)
                path = Path(folder) / "instance.json"
                instance.save(path)
                optimum = run_solver(instance, "graph").pallet_count
                for solver in SOLVERS:
                    if solver in PYTHON_SOLVERS:
                        plan, elapsed = solve_python(instance, solver)
                    else:
                        plan, elapsed = solve_timefold(path, solver.removeprefix("timefold-"), seconds, optimum)
                    valid = plan.has_plan and not verify(instance, plan)
                    rows.append(
                        {
                            "length": length,
                            "seed": seed,
                            "planks": len(instance.planks),
                            "candidates": len(instance.candidates()),
                            "optimum": optimum,
                            "solver": solver,
                            "status": plan.status.value,
                            "pallets": plan.pallet_count if valid else "",
                            "seconds": f"{elapsed:.4f}",
                            "valid": int(valid),
                        }
                    )
                    print(
                        f"L={length} seed={seed} {solver:17s} {plan.status.value:10s} "
                        f"pallets={plan.pallet_count if valid else '-'} (optimum {optimum}) {elapsed:.3f} s",
                        flush=True,
                    )
    return rows


def run_stock(lengths: list[int], seeds: int, seconds: float) -> list[dict]:
    rows = []
    for length in lengths:
        for seed in range(seeds):
            instance = random_instance(length=length, seed=seed)
            reference = run_solver(instance, "graph-stock")
            row = {
                "length": length,
                "seed": seed,
                "candidates": len(instance.candidates()),
                "lower_bound": -(-2 * instance.length // instance.max_pallet),
                "graph_pieces": len(reference.stock),
                "graph_pallets": reference.pallet_count,
            }
            for backend in ("scip", "cpsat"):
                started = time.perf_counter()
                plan = run_solver(instance, f"{backend}-stock", seconds)
                elapsed = time.perf_counter() - started
                for candidate in (reference, plan):
                    errors = verify(instance, candidate) + verify_cutting(instance, candidate)
                    if errors:
                        sys.exit(f"invalid plan for L={length} seed={seed}: {errors}")
                row[f"{backend}_pieces"] = len(plan.stock)
                row[f"{backend}_pallets"] = plan.pallet_count
                row[f"{backend}_status"] = plan.status.value
                row[f"{backend}_seconds"] = f"{elapsed:.3f}"
            rows.append(row)
            print(f"stock L={length} seed={seed} {row}", flush=True)
    return rows


def stock_report(rows: list[dict]) -> list[str]:
    lines = [
        "## Extension: cutting from stock pieces",
        "",
        "Pallets are cut from stock pieces of length M and the stock pieces are minimised.",
        "`graph-stock` takes the plan with the fewest pallets and cuts it afterwards (first fit",
        "decreasing). Model C decides pallets and cutting together; the same model is solved",
        "with SCIP and with CP-SAT. The lower bound is ⌈2·L/M⌉. Averages over the seeds;",
        "`proved` counts the runs in which the solver proved its plan optimal within the time",
        "limit.",
        "",
        "| L (mm) | candidates | lower bound | graph-stock pieces | scip-stock pieces | cpsat-stock pieces "
        "| graph-stock pallets | model C pallets | scip proved | scip time (s) | cpsat proved | cpsat time (s) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for length in sorted({int(r["length"]) for r in rows}):
        group = [r for r in rows if int(r["length"]) == length]

        def mean(key: str) -> float:
            return statistics.mean(float(r[key]) for r in group)

        def proved(backend: str) -> str:
            return f"{sum(r[f'{backend}_status'] == 'optimal' for r in group)}/{len(group)}"

        lines.append(
            f"| {length} | {mean('candidates'):.0f} | {mean('lower_bound'):.1f} | {mean('graph_pieces'):.1f} "
            f"| {mean('scip_pieces'):.1f} | {mean('cpsat_pieces'):.1f} | {mean('graph_pallets'):.1f} "
            f"| {mean('scip_pallets'):.1f} | {proved('scip')} | {mean('scip_seconds'):.1f} "
            f"| {proved('cpsat')} | {mean('cpsat_seconds'):.1f} |"
        )
    return lines + [""]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fields)
        writer.writeheader()
        writer.writerows(rows)


def report(rows: list[dict], seconds: float, stock_rows: list[dict]) -> str:
    lengths = sorted({int(r["length"]) for r in rows})
    lines = [
        "# Benchmark",
        "",
        "Written by `scripts/benchmark.py` (`make benchmark`). Random bridges with planks",
        "400–700 mm apart and pallets of 600–2 600 mm; the columns are averages over the",
        "seeds of one bridge length. `graph` treats both lanes at once and gives the",
        "optimum; `graph-sequential` plans one lane after the other. The Timefold",
        f"runs stop when they reach it or after {seconds:g} s; their time is the solver's own,",
        "without the start of the JVM. Every plan is checked with `verify()`.",
        "",
        "## Time in seconds",
        "",
        "| L (mm) | planks | candidates | " + " | ".join(SOLVERS) + " |",
        "|---|---|---|" + "---|" * len(SOLVERS),
    ]
    quality = [
        "## Pallets above the optimum",
        "",
        "Average of (pallets − optimum) / optimum; `no plan` when a run ended without a valid plan.",
        "",
        "| L (mm) | optimum | " + " | ".join(SOLVERS) + " |",
        "|---|---|" + "---|" * len(SOLVERS),
    ]
    for length in lengths:
        group = [r for r in rows if int(r["length"]) == length]
        first = [r for r in group if r["solver"] == SOLVERS[0]]
        times, gaps = [], []
        for solver in SOLVERS:
            mine = [r for r in group if r["solver"] == solver]
            times.append(f"{statistics.mean(float(r['seconds']) for r in mine):.3f}")
            if all(int(r["valid"]) for r in mine):
                gap = statistics.mean((int(r["pallets"]) - int(r["optimum"])) / int(r["optimum"]) for r in mine)
                gaps.append(f"{gap:.0%}")
            else:
                gaps.append(f"no plan ({sum(1 - int(r['valid']) for r in mine)}/{len(mine)})")
        planks = statistics.mean(int(r["planks"]) for r in first)
        candidates = statistics.mean(int(r["candidates"]) for r in first)
        optimum = statistics.mean(int(r["optimum"]) for r in first)
        lines.append(f"| {length} | {planks:.0f} | {candidates:.0f} | " + " | ".join(times) + " |")
        quality.append(f"| {length} | {optimum:.1f} | " + " | ".join(gaps) + " |")
    footer = ["", "---", "", "© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE)."]
    stock = stock_report(stock_rows) if stock_rows else []
    return "\n".join(lines + [""] + quality + [""] + stock + footer[1:]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", choices=("all", "solvers", "stock"), default="all")
    parser.add_argument("--lengths", default="16000,32000,64000,128000", help="bridge lengths in mm")
    parser.add_argument("--seeds", type=int, default=3, help="instances per length")
    parser.add_argument("--seconds", type=float, default=30, help="time limit of a Timefold run")
    parser.add_argument("--stock-lengths", default="8000,12000,16000", help="bridge lengths of the stock part")
    parser.add_argument("--stock-seeds", type=int, default=5, help="instances per length in the stock part")
    parser.add_argument("--stock-seconds", type=float, default=60, help="time limit of a model C run")
    args = parser.parse_args()

    if args.part in ("all", "solvers"):
        if not JAR.exists():
            sys.exit(f"{JAR} is missing: run 'make timefold' first")
        rows = run([int(x) for x in args.lengths.split(",")], args.seeds, args.seconds)
        write_csv(CSV_PATH, FIELDS, rows)
    if args.part in ("all", "stock"):
        stock_rows = run_stock([int(x) for x in args.stock_lengths.split(",")], args.stock_seeds, args.stock_seconds)
        write_csv(STOCK_CSV_PATH, STOCK_FIELDS, stock_rows)
    REPORT_PATH.write_text(report(read_csv(CSV_PATH), args.seconds, read_csv(STOCK_CSV_PATH)), encoding="utf-8")
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
