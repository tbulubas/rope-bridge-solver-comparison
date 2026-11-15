# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Input data of a rope bridge with fixed planks (all lengths in millimetres)."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

Pallet = tuple[int, int]


@dataclass(frozen=True)
class BridgeInstance:
    """Parameters of the problem statement.

    Attributes:
        planks: plank positions p(0) = 0 < p(1) < … < p(n) = L.
        min_pallet: m, minimal pallet length.
        max_pallet: M, maximal pallet length.
    """

    planks: tuple[int, ...]
    min_pallet: int
    max_pallet: int

    def __post_init__(self) -> None:
        if len(self.planks) < 2:
            raise ValueError("a bridge needs at least the two anchored planks")
        if self.planks[0] != 0:
            raise ValueError("the first plank must be at position 0")
        if any(a >= b for a, b in zip(self.planks, self.planks[1:])):
            raise ValueError("plank positions must be strictly increasing")
        if not 0 < self.min_pallet <= self.max_pallet:
            raise ValueError("pallet lengths must satisfy 0 < min_pallet <= max_pallet")

    @property
    def length(self) -> int:
        """L, the position of the last plank."""
        return self.planks[-1]

    @property
    def last(self) -> int:
        """n, the index of the last plank."""
        return len(self.planks) - 1

    def candidates(self) -> list[Pallet]:
        """Candidate pallets (a, b): planks a < b at a distance in [m, M]."""
        planks = self.planks
        pallets = []
        for a in range(self.last):
            for b in range(a + 1, self.last + 1):
                span = planks[b] - planks[a]
                if span > self.max_pallet:
                    break
                if span >= self.min_pallet:
                    pallets.append((a, b))
        return pallets

    def to_json(self) -> str:
        return json.dumps(
            {"planks": list(self.planks), "min_pallet": self.min_pallet, "max_pallet": self.max_pallet}
        )

    @staticmethod
    def from_json(text: str) -> BridgeInstance:
        data = json.loads(text)
        return BridgeInstance(tuple(data["planks"]), data["min_pallet"], data["max_pallet"])

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> BridgeInstance:
        return BridgeInstance.from_json(Path(path).read_text(encoding="utf-8"))


def random_instance(
    length: int = 16000,
    min_gap: int = 400,
    max_gap: int = 700,
    min_pallet: int = 600,
    max_pallet: int = 2600,
    seed: int = 0,
) -> BridgeInstance:
    """Bridge of the given length with planks at random irregular distances.

    The gaps are drawn uniformly from [min_gap, max_gap]; the last gap takes
    what is left, so it may be shorter than min_gap.
    """
    if not 0 < min_gap <= max_gap:
        raise ValueError("gaps must satisfy 0 < min_gap <= max_gap")
    rng = random.Random(seed)
    planks = [0]
    while planks[-1] + max_gap < length:
        planks.append(planks[-1] + rng.randint(min_gap, max_gap))
    planks.append(length)
    return BridgeInstance(tuple(planks), min_pallet, max_pallet)
