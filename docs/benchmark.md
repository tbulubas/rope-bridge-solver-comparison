# Benchmark

Written by `scripts/benchmark.py` (`make benchmark`). Random bridges with planks
400–700 mm apart and pallets of 600–2 600 mm; the columns are averages over the
seeds of one bridge length. `graph` treats both lanes at once and gives the
optimum; `graph-sequential` plans one lane after the other. The Timefold
runs stop when they reach it or after 30 s; their time is the solver's own,
without the start of the JVM. Every plan is checked with `verify()`.

## Time in seconds

| L (mm) | planks | candidates | graph | graph-sequential | scip-flow | cpsat-flow | scip-cover | cpsat-cover | timefold-joints | timefold-pallets |
|---|---|---|---|---|---|---|---|---|---|---|
| 16000 | 30 | 98 | 0.000 | 0.000 | 0.017 | 0.024 | 0.035 | 0.035 | 0.714 | 30.059 |
| 32000 | 59 | 199 | 0.001 | 0.001 | 0.037 | 0.112 | 0.094 | 0.103 | 30.071 | 30.071 |
| 64000 | 115 | 400 | 0.002 | 0.001 | 0.066 | 0.154 | 0.118 | 0.235 | 30.072 | 30.073 |
| 128000 | 234 | 832 | 0.006 | 0.001 | 0.088 | 0.188 | 0.309 | 0.521 | 30.078 | 30.077 |

## Pallets above the optimum

Average of (pallets − optimum) / optimum; `no plan` when a run ended without a valid plan.

| L (mm) | optimum | graph | graph-sequential | scip-flow | cpsat-flow | scip-cover | cpsat-cover | timefold-joints | timefold-pallets |
|---|---|---|---|---|---|---|---|---|---|
| 16000 | 15.0 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 89% |
| 32000 | 28.0 | 0% | 0% | 0% | 0% | 0% | 0% | 7% | 102% |
| 64000 | 56.3 | 0% | 0% | 0% | 0% | 0% | 0% | 13% | 101% |
| 128000 | 112.3 | 0% | 0% | 0% | 0% | 0% | 0% | 27% | 107% |

## Extension: cutting from stock pieces

Pallets are cut from stock pieces of length M and the stock pieces are minimised.
`graph-stock` takes the plan with the fewest pallets and cuts it afterwards (first fit
decreasing). Model C decides pallets and cutting together; the same model is solved
with SCIP and with CP-SAT. The lower bound is ⌈2·L/M⌉. Averages over the seeds;
`proved` counts the runs in which the solver proved its plan optimal within the time
limit.

| L (mm) | candidates | lower bound | graph-stock pieces | scip-stock pieces | cpsat-stock pieces | graph-stock pallets | model C pallets | scip proved | scip time (s) | cpsat proved | cpsat time (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 8000 | 45 | 7.0 | 8.0 | 7.0 | 7.0 | 8.0 | 8.0 | 5/5 | 0.3 | 5/5 | 0.2 |
| 12000 | 70 | 10.0 | 11.6 | 10.0 | 10.0 | 11.8 | 12.4 | 5/5 | 9.7 | 5/5 | 0.4 |
| 16000 | 98 | 13.0 | 14.0 | 13.0 | 13.0 | 15.0 | 16.8 | 4/5 | 19.8 | 5/5 | 2.6 |

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
