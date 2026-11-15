# Rope Bridge with Fixed Planks — Graph View and MIP Models

Models for the problem described in
[`problem-statement.md`](problem-statement.md): the graph view, the exact
cover model and the flow model.

## Indices and sets

| Symbol                    | Meaning                                                   |
|---------------------------|-----------------------------------------------------------|
| λ ∈ Λ = {l, r}            | lane: left, right                                         |
| j ∈ J = {0, 1, …, n}      | planks, ordered along the bridge                          |
| J° = {1, …, n−1}          | interior planks                                           |
| k ∈ U = {1, …, n}         | gaps; gap k lies between planks k−1 and k                 |
| i = (a, b) ∈ S            | candidate pallets: 0 ≤ a < b ≤ n and m ≤ p(b) − p(a) ≤ M  |
| j1(i) = a, j2(i) = b      | start and end plank of pallet i                           |

A pallet (a, b) covers the consecutive gaps a+1, …, b.

## Graph view

Take the planks as nodes and the candidate pallets as arcs a → b. The graph
is acyclic, because every arc points forward.

- A valid lane is a **path from plank 0 to plank n**: consecutive pallets
  share a plank, so there are no holes and no overlaps.
- The joints of a lane are the interior nodes of its path. The staggering
  rule says that the two paths share **no interior node**.
- The number of pallets is the number of arcs of both paths.

The problem is therefore: find **two paths from 0 to n without a common
interior node and with the fewest arcs in total**. This is a minimum-cost
flow of two units from 0 to n in which every arc costs 1 and every interior
node lets one unit pass. It is solved exactly by two shortest-path
computations (`graph.py`): one in the graph itself and one in the residual
graph of the first path.

The only pallet both lanes can share is (0, n), which exists when
m ≤ L ≤ M; then each lane is that single pallet.

### Lane after lane

A simpler graph algorithm plans the lanes one after the other
(`solve_sequential` in `graph.py`):

1. List the left lanes from the fewest pallets to the most (best-first
   search; the exact number of pallets still needed from every plank is
   computed beforehand).
2. Take the next left lane, remove its joints from the graph and find the
   shortest right lane in what is left.
3. If there is none, go back to step 2; stop after a fixed number of
   attempts (100).

The plan is valid, but the method has no guarantee: in a general graph the
shortest first path can block every second path or force a long detour, which
is exactly what the residual graph of the two-lane algorithm repairs. On this
problem it did not happen in any test: on all 18 580 solvable bridges with up
to 15 planks on a unit grid and on more than 800 random bridges of realistic
proportions the first left lane already worked and the plan had the optimal
number of pallets.

## Model A — exact cover (binary)

The set-cover view: the gaps are the universe, the candidate pallets are the
subsets, and each lane picks subsets that cover every gap exactly once.

| Variable             | Domain | Meaning                         |
|----------------------|--------|---------------------------------|
| z(λ,i), λ ∈ Λ, i ∈ S | {0, 1} | 1 if pallet i is laid in lane λ |

Derived expression — plank j is a joint of lane λ:

    J(λ,j) = Σ_{i ∈ S : j2(i) = j} z(λ,i)          j ∈ J°

Every gap is covered by exactly one pallet in each lane:

    (1)  Σ_{i ∈ S : j1(i) < k ≤ j2(i)} z(λ,i) = 1          ∀ λ ∈ Λ, k ∈ U

Staggering — an interior plank carries the joint of at most one lane:

    (2)  J(l,j) + J(r,j) ≤ 1                                ∀ j ∈ J°

Objective:

    min  Σ_{λ ∈ Λ} Σ_{i ∈ S} z(λ,i)

Optional symmetry breaking — the lanes are interchangeable:

    (3)  Σ_{i ∈ S} z(l,i) ≤ Σ_{i ∈ S} z(r,i)

Every column of (1) for one lane has its ones in consecutive rows (an
interval matrix), so each lane alone is totally unimodular. The coupling (2)
keeps the bound of the linear relaxation at the optimum, but the relaxation
has fractional optimal solutions that mix the two lanes.

## Model B — flow (binary, one variable per pallet)

The lanes are interchangeable, so it is enough to decide which pallets are
laid at all and to split them into lanes afterwards.

| Variable    | Domain    | Meaning                                              |
|-------------|-----------|------------------------------------------------------|
| f(i), i ∈ S | {0, 1}    | 1 if pallet i is laid in one of the lanes            |
| f(0,n)      | {0, 1, 2} | the full-length pallet may be laid in both lanes     |

Two pallets start on the first plank and two end on the last one:

    (4)  Σ_{i : j1(i) = 0} f(i) = 2,     Σ_{i : j2(i) = n} f(i) = 2

On an interior plank, a pallet that ends is followed by a pallet that starts:

    (5)  Σ_{i : j2(i) = j} f(i) = Σ_{i : j1(i) = j} f(i)    ∀ j ∈ J°

Staggering — at most one pallet ends on an interior plank:

    (6)  Σ_{i : j2(i) = j} f(i) ≤ 1                          ∀ j ∈ J°

Objective:

    min  Σ_{i ∈ S} f(i)

Constraints (4)–(6) are the node balance and node capacity constraints of a
network flow. Their matrix is totally unimodular, so the linear relaxation
has integral vertices: a simplex solver returns the optimal plan without any
branching. Following the selected pallets from plank 0 twice gives the two
lanes.

## Model C — flow with cutting from stock pieces

The extension of the problem statement: pallets are cut from stock pieces of
length M and the number of stock pieces is minimised. Model B stays as it is;
the cutting is added on top of it.

Let ℓ(i) = p(j2(i)) − p(j1(i)) be the length of pallet i and K = {1, …, K̄}
the stock pieces, where K̄ is the number of pieces of any known plan (the
plan with the fewest pallets, cut by first fit decreasing).

| Variable             | Domain | Meaning                                    |
|----------------------|--------|--------------------------------------------|
| f(i), i ∈ S          | as in model B | pallet i is laid                    |
| x(i,k), i ∈ S, k ∈ K | {0, 1} | pallet i is cut from stock piece k         |
| u(k), k ∈ K          | {0, 1} | stock piece k is used                      |

Constraints (4)–(6) of model B, and:

Every laid pallet is cut from one stock piece:

    (7)  Σ_{k ∈ K} x(i,k) = f(i)                             ∀ i ∈ S

The pallets cut from a piece fit into its length, and only used pieces are
cut:

    (8)  Σ_{i ∈ S} ℓ(i) · x(i,k) ≤ M · u(k)                  ∀ k ∈ K

Symmetry breaking — the pieces are used in order:

    (9)  u(k) ≥ u(k+1)                                        ∀ k < K̄

The first ⌈2·L/M⌉ pieces are always used, so their u(k) is fixed to 1.

Objective — stock pieces first, then pallets; a stock piece outweighs any
number of pallets (at most 2·n are laid):

    min  (2·n + 1) · Σ_{k ∈ K} u(k)  +  Σ_{i ∈ S} f(i)

The model is a plain MIP (`stock.py`). The new requirement costs three constraints and leaves the rest
of the model untouched. The assignment of pallets to
numbered pieces is the simplest way to write the cutting, not the strongest:
bridges of the reference size are solved to proven optimality in seconds
(CP-SAT) to tens of seconds (SCIP), see [`benchmark.md`](benchmark.md), much longer ones would need a pattern or
arc-flow formulation of the cutting.

## Solvers

Models A, B and C are written once and passed through the same OR-Tools
interface to two solvers:

- **SCIP**, a branch-and-cut MIP solver: it solves the linear relaxation and
  branches on fractional variables;
- **CP-SAT**, a constraint programming solver built on SAT with clause
  learning; it accepts the models because all their variables are integer.

The benchmark reports both (`scip-…` and `cpsat-…`). SCIP runs on one thread;
CP-SAT runs a portfolio of search strategies on all cores, so its times
depend on the machine. On model C that matters: with many cores CP-SAT is
several times faster than SCIP, with two cores it can be the slower one.

## Model size

| Item              | Model A        | Model B     |
|-------------------|----------------|-------------|
| variables         | 2·\|S\|        | \|S\|       |
| constraints       | 2·n + (n − 1)  | 2·(n − 1) + 2 |

With planks about 550 mm apart and pallets of 600–2 600 mm, every plank
starts about four candidate pallets, so |S| ≈ 4·n.

## Small example

Planks at 0, 1 000, 2 000, 3 000, 4 000, m = 1 000, M = 2 000. Each lane
needs at least two pallets, and two pallets per lane would put both joints on
plank 2 (at 2 000). One lane needs a third pallet:

    left:   0 — 2 000 — 4 000
    right:  0 — 1 000 — 3 000 — 4 000

5 pallets. The staggering rule costs one pallet.

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
