from collections import defaultdict
from typing import Hashable


class UnionFind:
    def __init__(self):
        self._parent: dict[Hashable, Hashable] = {}
        self._rank: dict[Hashable, int] = {}

    def add(self, x: Hashable) -> None:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0

    def find(self, x: Hashable) -> Hashable:
        self.add(x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: Hashable, b: Hashable) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1

    def groups(self) -> dict[Hashable, list[Hashable]]:
        out: dict[Hashable, list[Hashable]] = defaultdict(list)
        for x in self._parent:
            out[self.find(x)].append(x)
        return dict(out)
