# Rope Bridge with Fixed Planks — Timefold Models

Two models of the problem in [`problem-statement.md`](problem-statement.md)
for the [Timefold Solver](https://timefold.ai) (Kotlin, constraint streams,
default construction heuristic and local search). They differ only in what a
planning entity is; the code is in `timefold/src/main/kotlin/fixedplanks/`.

## Model "pallets" — one entity per candidate pallet

`PalletModel.kt`. Every candidate pallet is a planning entity with one
planning variable, the lane it is laid in: 1, 2 or unassigned.

| Level  | Constraint                                                                 |
|--------|----------------------------------------------------------------------------|
| hard   | pallets of one lane do not overlap                                         |
| medium | every gap of every lane is covered (penalty: the uncovered millimetres)    |
| medium | joints of the two lanes do not lie on the same interior plank              |
| soft   | number of pallets                                                          |

This is the direct translation of the set-cover view: the solver selects
subsets. Its weakness is the neighbourhood. A plan is a chain of pallets that
touch exactly, so replacing two pallets by one longer pallet needs three
variables to change together; every single change opens a hole or creates an
overlap and makes the score worse. Almost all entities stay unassigned, and
almost all moves are rejected.

## Model "joints" — one entity per lane and plank

`JointModel.kt`. Every plank of every lane is a planning entity with a
boolean planning variable: the lane has a joint there or not. The anchored
planks are pinned to "joint". The pallets of a lane run from joint to joint,
so a lane is covered without holes and overlaps **by construction**.

| Level | Constraint                                                                  |
|-------|-----------------------------------------------------------------------------|
| hard  | consecutive joints of a lane are m to M apart (penalty: the missing or excess millimetres) |
| hard  | joints of the two lanes do not lie on the same interior plank               |
| soft  | number of joints                                                            |

Here a single change is a meaningful step: removing a joint merges two
pallets, adding one splits a pallet. The penalty in millimetres gives the
local search a slope to follow; with a flat penalty per violated pallet the
same model does not leave the empty plan.

## What the comparison shows

See [`benchmark.md`](benchmark.md). Neither model proves optimality; the
benchmark gives them the optimum as the target and measures whether and when
they reach it.

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
