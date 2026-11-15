# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Graph algorithms: two paths without a common interior plank.

See docs/mip-model.md, "Graph view". Planks are nodes, candidate pallets are
arcs.

solve() treats both lanes at once: the plan is a minimum-cost flow of two
units from the first to the last plank in which every interior plank lets one
unit pass. It is found with two shortest-path computations (successive
shortest paths with potentials) and is optimal.

solve_sequential() treats the lanes one after the other: it lists the
shortest left lanes, removes the joints of one of them from the graph and
looks for the shortest right lane in what is left. The plan is valid;
optimality is not guaranteed.
"""

from __future__ import annotations

import heapq
from collections.abc import Iterator

from fixed_planks.instance import BridgeInstance, Pallet
from fixed_planks.solution import BridgePlan, Status, lanes_from_pallets

_INF = float("inf")


class _Network:
    """Residual network with arcs stored in pairs (arc, reverse arc)."""

    def __init__(self, nodes: int) -> None:
        self.head: list[list[int]] = [[] for _ in range(nodes)]
        self.to: list[int] = []
        self.cap: list[int] = []
        self.cost: list[int] = []

    def add(self, u: int, v: int, cap: int, cost: int) -> int:
        """Add arc u → v and its reverse; return the index of the arc."""
        index = len(self.to)
        self.head[u].append(index)
        self.to.append(v)
        self.cap.append(cap)
        self.cost.append(cost)
        self.head[v].append(index + 1)
        self.to.append(u)
        self.cap.append(0)
        self.cost.append(-cost)
        return index

    def augment(self, source: int, sink: int, potential: list[float]) -> bool:
        """Send one unit along a shortest residual path; False if there is none."""
        dist = [_INF] * len(self.head)
        via = [-1] * len(self.head)
        dist[source] = 0
        queue = [(0, source)]
        while queue:
            d, u = heapq.heappop(queue)
            if d > dist[u]:
                continue
            for arc in self.head[u]:
                if self.cap[arc] == 0:
                    continue
                v = self.to[arc]
                reduced = d + self.cost[arc] + potential[u] - potential[v]
                if reduced < dist[v]:
                    dist[v] = reduced
                    via[v] = arc
                    heapq.heappush(queue, (reduced, v))
        if dist[sink] == _INF:
            return False
        for node, d in enumerate(dist):
            if d < _INF:
                potential[node] += d
        node = sink
        while node != source:
            arc = via[node]
            self.cap[arc] -= 1
            self.cap[arc ^ 1] += 1
            node = self.to[arc ^ 1]
        return True


def solve(instance: BridgeInstance) -> BridgePlan:
    """Optimal plan, or status INFEASIBLE when no valid plan exists."""
    last = instance.last
    # Plank j is split into an entry node 2j and an exit node 2j + 1; the arc
    # between them carries the staggering rule: one unit on interior planks.
    network = _Network(2 * (last + 1))
    for j in range(last + 1):
        network.add(2 * j, 2 * j + 1, 2 if j in (0, last) else 1, 0)
    arcs: list[tuple[int, Pallet, int]] = []
    for a, b in instance.candidates():
        cap = 2 if (a, b) == (0, last) else 1
        arcs.append((network.add(2 * a + 1, 2 * b, cap, 1), (a, b), cap))

    potential = [0.0] * len(network.head)
    for _ in range(2):
        if not network.augment(0, 2 * last + 1, potential):
            return BridgePlan(Status.INFEASIBLE)

    pallets = [pallet for arc, pallet, cap in arcs for _ in range(cap - network.cap[arc])]
    left, right = lanes_from_pallets(instance, pallets)
    return BridgePlan(Status.OPTIMAL, left, right)


def _shortest_lanes(instance: BridgeInstance) -> Iterator[list[Pallet]]:
    """All ways to cover one lane, from the fewest pallets to the most.

    Best-first search over partial lanes. The exact number of pallets still
    needed from every plank is known in advance, so lanes come out in order.
    """
    last = instance.last
    starting: dict[int, list[Pallet]] = {j: [] for j in range(last + 1)}
    for pallet in instance.candidates():
        starting[pallet[0]].append(pallet)
    remaining = [_INF] * (last + 1)
    remaining[last] = 0
    for j in range(last - 1, -1, -1):
        remaining[j] = min((1 + remaining[b] for _, b in starting[j]), default=_INF)
    if remaining[0] == _INF:
        return

    queue: list[tuple[float, tuple[int, ...]]] = [(remaining[0], (0,))]
    while queue:
        _, joints = heapq.heappop(queue)
        if joints[-1] == last:
            yield list(zip(joints, joints[1:]))
            continue
        for _, b in starting[joints[-1]]:
            if remaining[b] < _INF:
                heapq.heappush(queue, (len(joints) + remaining[b], joints + (b,)))


def _shortest_lane_avoiding(instance: BridgeInstance, blocked: set[int]) -> list[Pallet] | None:
    """Lane with the fewest pallets and no joint on a blocked plank, or None."""
    last = instance.last
    count = [_INF] * (last + 1)
    via: list[int] = [-1] * (last + 1)
    count[0] = 0
    for a, b in instance.candidates():
        if a not in blocked and b not in blocked and count[a] + 1 < count[b]:
            count[b] = count[a] + 1
            via[b] = a
    if count[last] == _INF:
        return None
    lane = []
    at = last
    while at != 0:
        lane.append((via[at], at))
        at = via[at]
    return lane[::-1]


def solve_sequential(instance: BridgeInstance, attempts: int = 100) -> BridgePlan:
    """Lane after lane: the first of the shortest left lanes that leaves room for a right lane.

    Tries at most `attempts` left lanes. Status FEASIBLE with a plan, UNKNOWN
    when none of the tried left lanes works, INFEASIBLE when no lane exists.
    """
    tried = False
    for _, left in zip(range(attempts), _shortest_lanes(instance)):
        tried = True
        right = _shortest_lane_avoiding(instance, {b for _, b in left[:-1]})
        if right is not None:
            return BridgePlan(Status.FEASIBLE, left, right)
    return BridgePlan(Status.UNKNOWN if tried else Status.INFEASIBLE)
