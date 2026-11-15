# SetCoverageTimefoldVsMIP — project guide for Claude

Decking a rope bridge with fixed planks in two lanes with staggered joints
and the fewest pallets — a set-cover-like problem solved with Timefold (two
models), a graph algorithm and two MIP models, and compared. The goal is a
LinkedIn post: structure matters more than the tool.

- Problem statement: `docs/problem-statement.md` (comes from the user — ask,
  do not invent the problem or the modelling approach)
- `docs/mip-model.md` (graph view, MIP models A and B),
  `docs/timefold-models.md`, `docs/benchmark.md` (written by `make benchmark`)
- Vocabulary: bridge, plank, pallet, lane, joint, gap — nothing else.

Package `fixed_planks`: `instance.py`, `solution.py` (`verify()`),
`graph.py` (`solve`: min-cost flow, optimal; `solve_sequential`: lane after
lane, the user's original approach), `model.py` (models A and B; every MIP model runs with SCIP and with CP-SAT,
solver names `scip-…` / `cpsat-…`, keep both in the results), `stock.py` (extension: cutting from stock pieces of
length M, model C; `pack` cuts a finished plan; the
extension is hypothetical, only to show that the MIP takes new requirements), `cli.py`;
`tests/exhaustive.py` is the independent optimality check.
`draw.py` (matplotlib pictures). `notebooks/solver_comparison.ipynb`
(`make notebook`, `make notebook-check`) is stored with its outputs; it is
Python only and shows Timefold through `docs/benchmark/*.csv` plus one
optional live cell.
`timefold/` is a Kotlin Maven module (JDK 25, bytecode target 25,
Timefold Solver 2.8, models
`pallets` and `joints`); `make timefold` builds its runner jar, which
`scripts/benchmark.py` calls.

## Layout

Follows the standard of the user's `PlanningRopeBridge`,
`PlanningLinesSweeping`, `PlanningTrainWagons` and `PlanningSlotCapacity`
projects in `C:\AI\Claude` (use them as the reference and copy their patterns
before adding files):

- `src/<package>/`, `pyproject.toml` (setuptools, no `requirements.txt`),
  `tests/` with pytest
- `Makefile` with `venv`, `test`, `run`, `clean`, `distclean`, `recreate`;
  Python 3.12 via the py launcher, `scripts/check_venv.py` guards the version
- `docs/` — `problem-statement.md`, `mip-model.md` (numbered constraints
  referenced from `model.py`), `intellij.md`
- `.run/` — shared IntelliJ run configurations
- An independent `verify()` of every solution; notebooks are stored with
  their outputs — keep them free of local paths
- Copyright header in every source file:
  ```
  # Copyright (c) 2026 Taras Bulubas. All rights reserved.
  # Use requires prior written permission; see LICENSE.
  ```
- `LICENSE` — all rights reserved; README has the Author / Use of AI /
  License sections like the sibling projects
- `linkedin-post.txt` stays untracked

## Language

All files — code, identifiers, comments, docs, README, notebook text, commit
messages — are in English.

## Running and testing

```bash
make venv
make test
make run
```

The user is on Windows 11 and uses the local `.venv`; do not use or suggest
conda. After changing dependencies in `pyproject.toml`, run `make venv`.
