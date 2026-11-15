# Decking a Rope Bridge with Fixed Planks — Problem Statement

## Context

A rope bridge crosses a gorge. Its planks are already woven into the ropes,
so their positions are given. The deck is made of rigid pallets laid on the
planks in two lanes. The task is to choose the pallets of both lanes so that
the deck obeys the construction rules below and needs as few pallets as
possible.

This is the fixed-plank variant of the
[rope bridge planning problem](https://github.com/tbulubas/rope-bridge-planning),
where the plank positions are decisions too. With fixed planks the problem
becomes purely combinatorial: a set-cover-like selection of pallets from a
finite list of candidates.

The purpose of this project is to compare three ways of solving it — a
constraint solver based on local search (Timefold), a graph algorithm and a
mixed-integer programming (MIP) model.

## Geometry

- The bridge has length **L**.
- Three ropes run along the bridge and split the deck into two **lanes**, the
  **left** and the **right** one.
- **n + 1 planks** lie across both lanes at the given positions
  `0 = p(0) < p(1) < … < p(n) = L`. The spacing is irregular.
- The **first plank** p(0) and the **last plank** p(n) are anchored to the
  edges of the gorge; the planks between them are *interior* planks.

```
         p(0)     p(1)   p(2)    p(3)    p(4)    p(5)    p(6)  p(7)  p(8)
  R_l   =+=========+======+=======+=======+=======+=======+=====+====+=
         |    left lane   |               |               |          |
  R_m   =+=========+======+=======+=======+=======+=======+=====+====+=
         |         |  right lane  |               |             |    |
  R_r   =+=========+======+=======+=======+=======+=======+=====+====+=

  + = plank (fixed position)     | = pallet joint in that lane
```

## Pallets

- A pallet fills one lane between two planks: it starts on plank a and ends
  on plank b, a < b, and passes over the planks between them.
- Its length p(b) − p(a) must lie in **[m, M]**: **m** is the minimal and
  **M** the maximal pallet length.
- Pallets are cut to length, so every pair of planks with a distance in
  [m, M] is a **candidate pallet**. The candidates are known in advance; a
  plan selects some of them for the left lane and some for the right lane.

## Construction rules

1. **Cover.** In each lane the selected pallets are laid one after another
   and cover the lane from the first plank to the last plank — without holes
   and without overlaps. Consecutive pallets of a lane meet on a shared plank,
   a *joint*.
2. **Staggering.** An interior plank carries the joint of at most one lane;
   the pallet of the other lane passes over it. Joints of the two lanes never
   lie on the same interior plank.
3. **Anchored planks.** Both lanes start on the first plank and end on the
   last plank (this follows from rule 1 and is the only place where the two
   lanes meet).

## Inputs

All lengths are whole millimetres.

| Symbol     | Meaning                                  | Unit |
|------------|------------------------------------------|------|
| p(0..n)    | plank positions, p(0) = 0, p(n) = L      | mm   |
| m          | minimal pallet length                    | mm   |
| M          | maximal pallet length                    | mm   |

## Decisions

For each lane, which candidate pallets are laid.

## Objective

**Minimise the total number of pallets** in both lanes. Fewer pallets mean
fewer cuts, which saves time and reduces waste.

An instance may have no valid plan, e.g. when L is slightly longer than M and
the few planks do not allow staggered joints.

## Extension — cutting from stock pieces

This extension is hypothetical. Its purpose is to show what happens to each
solution approach when a new requirement arrives.

Pallets are cut from **stock pieces of length M** (that is why no pallet is
longer than M). Several pallets can be cut from one stock piece when their
lengths add up to at most M; what is left of a piece is waste unless another
pallet is cut from it. The saw cut itself takes no length.

In the extension the objective changes:

**Minimise the number of stock pieces**; among the plans with the fewest
stock pieces, minimise the number of pallets.

The two lanes have a total length of 2·L, so at least ⌈2·L/M⌉ stock pieces
are needed. The plan with the fewest pallets is usually not the one with the
fewest stock pieces: its pallets are long, and the short remainders of their
stock pieces fit no other pallet. Cutting the deck into a few more pallets
whose lengths pair up well saves stock.

Selecting the pallets and cutting them are now one decision. The graph view
of the basic problem does not carry over: the cost of a pallet depends on
which other pallets share its stock piece, so a plan is no longer a cheapest
pair of paths.

## Reference size

A realistic instance has L up to 16 000 mm, planks 400–700 mm apart, m = 600
and M = 2 600, which gives 25–35 planks and well over 100 candidate pallets.
The benchmark also uses much longer bridges to show how the approaches scale.

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
