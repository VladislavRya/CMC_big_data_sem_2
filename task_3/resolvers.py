from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, Optional


class Resolver(ABC):
    name: str = ''

    @abstractmethod
    def resolve(self, values: list[Any]) -> Any: ...

    @staticmethod
    def _non_null(values: list[Any]) -> list[Any]:
        return [v for v in values if v is not None and v != '']


class Coalesce(Resolver):
    name = 'coalesce'

    def resolve(self, values):
        nn = self._non_null(values)
        return nn[0] if nn else None


class Vote(Resolver):
    name = 'vote'

    def resolve(self, values):
        nn = self._non_null(values)
        if not nn:
            return None
        counts = Counter(nn)
        top = counts.most_common(1)[0][0]
        return top


class Max(Resolver):
    name = 'max'

    def resolve(self, values):
        nn = self._non_null(values)
        return max(nn) if nn else None


class Min(Resolver):
    name = 'min'

    def resolve(self, values):
        nn = self._non_null(values)
        return min(nn) if nn else None


class Avg(Resolver):
    name = 'avg'

    def resolve(self, values):
        nn = [v for v in self._non_null(values) if isinstance(v, (int, float))]
        return round(sum(nn) / len(nn), 2) if nn else None


class Longest(Resolver):
    name = 'longest'

    def resolve(self, values):
        nn = self._non_null(values)
        return max(nn, key=lambda v: len(str(v))) if nn else None


class Concat(Resolver):
    name = 'concat'

    def __init__(self, sep: str = ' | '):
        self.sep = sep

    def resolve(self, values):
        nn = [str(v) for v in self._non_null(values)]
        return self.sep.join(nn) if nn else None


class Escalate(Resolver):
    name = 'escalate'

    def resolve(self, values) -> Optional[list]:
        nn = self._non_null(values)
        if not nn:
            return None
        return sorted(set(nn), key=str)


RESOLVERS: dict[str, type[Resolver]] = {
    cls.name: cls for cls in (
        Coalesce, Vote, Max, Min, Avg, Longest, Concat, Escalate,
    )
}
