from abc import ABC, abstractmethod
from typing import Any

from resolvers import (
    Resolver,
    Coalesce, Vote, Avg, Min, Longest, Escalate,
)


TARGET_FIELDS: tuple[str, ...] = (
    'marketplace', 'source_id', 'url', 'title', 'description',
    'brand', 'model', 'price_rub', 'color',
    'keys_count', 'keys_size', 'keys_weight', 'polyphony', 'timbres',
    'weight_kg', 'width_mm', 'height_mm', 'depth_mm', 'country',
)


DEFAULT_RESOLVERS: dict[str, Resolver] = {
    'marketplace':  Escalate(),
    'source_id':    Escalate(),
    'url':          Longest(),
    'title':        Longest(),
    'description':  Longest(),
    'brand':        Vote(),
    'model':        Longest(),
    'price_rub':    Min(),
    'color':        Vote(),
    'keys_count':   Vote(),
    'keys_size':    Vote(),
    'keys_weight':  Vote(),
    'polyphony':    Vote(),
    'timbres':      Vote(),
    'weight_kg':    Avg(),
    'width_mm':     Vote(),
    'height_mm':    Vote(),
    'depth_mm':     Vote(),
    'country':      Vote(),
}


def _singleton(record: dict) -> dict:
    return {f: record.get(f) for f in TARGET_FIELDS}


class FusionStrategy(ABC):
    name: str = ''

    def fuse(self, records: list[dict]) -> dict:
        if len(records) == 1:
            return _singleton(records[0])
        return self._fuse_many(records)

    @abstractmethod
    def _fuse_many(self, records: list[dict]) -> dict: ...


class FuseByStrategy(FusionStrategy):
    """FUSE BY (cluster_id) RESOLVE(attr, fn)"""

    name = 'fuse_by'

    def __init__(self, resolvers: dict[str, Resolver] | None = None):
        self.resolvers = resolvers if resolvers is not None else DEFAULT_RESOLVERS

    def _fuse_many(self, records: list[dict]) -> dict:
        out: dict[str, Any] = {}
        for f in TARGET_FIELDS:
            values = [r.get(f) for r in records]
            out[f] = self.resolvers[f].resolve(values)
        return out


class MinimumUnionStrategy(FusionStrategy):
    name = 'minimum_union'

    @staticmethod
    def _subsumes(a: dict, b: dict) -> bool:
        extra = False
        for f in TARGET_FIELDS:
            va, vb = a.get(f), b.get(f)
            if vb is not None and vb != '':
                if va != vb:
                    return False
            else:
                if va is not None and va != '':
                    extra = True
        return extra

    def _fuse_many(self, records: list[dict]) -> dict:
        keep = [True] * len(records)
        for i, ri in enumerate(records):
            for j, rj in enumerate(records):
                if i == j or not keep[j]:
                    continue
                if self._subsumes(rj, ri):
                    keep[i] = False
                    break
        survivors = [r for r, k in zip(records, keep) if k]

        coalesce = Coalesce()
        escalate = Escalate()
        out: dict[str, Any] = {}
        for f in TARGET_FIELDS:
            if f in ('marketplace', 'source_id'):
                out[f] = escalate.resolve([r.get(f) for r in records])
            else:
                out[f] = coalesce.resolve([r.get(f) for r in survivors])
        return out


class ComplementUnionStrategy(FusionStrategy):
    name = 'complement_union'

    @staticmethod
    def _can_complement(a: dict, b: dict) -> bool:
        for f in TARGET_FIELDS:
            va, vb = a.get(f), b.get(f)
            if (va is not None and va != '') and (vb is not None and vb != '') and va != vb:
                return False
        return True

    @staticmethod
    def _merge(a: dict, b: dict) -> dict:
        out: dict[str, Any] = {}
        for f in TARGET_FIELDS:
            va, vb = a.get(f), b.get(f)
            out[f] = va if (va is not None and va != '') else vb
        return out

    def _fuse_many(self, records: list[dict]) -> dict:
        pool: list[dict] = [_singleton(r) for r in records]
        changed = True
        while changed and len(pool) > 1:
            changed = False
            for i in range(len(pool)):
                merged_with = -1
                for j in range(i + 1, len(pool)):
                    if self._can_complement(pool[i], pool[j]):
                        merged_with = j
                        break
                if merged_with >= 0:
                    merged = self._merge(pool[i], pool[merged_with])
                    pool = (
                        [pool[k] for k in range(len(pool)) if k not in (i, merged_with)]
                        + [merged]
                    )
                    changed = True
                    break

        escalate = Escalate()
        if len(pool) == 1:
            out = pool[0]
            out['marketplace'] = escalate.resolve([r.get('marketplace') for r in records])
            out['source_id'] = escalate.resolve([r.get('source_id') for r in records])
            return out

        vote = Vote()
        out = {}
        for f in TARGET_FIELDS:
            if f in ('marketplace', 'source_id'):
                out[f] = escalate.resolve([r.get(f) for r in records])
            else:
                out[f] = vote.resolve([r.get(f) for r in pool])
        return out


STRATEGIES: dict[str, type[FusionStrategy]] = {
    cls.name: cls for cls in (
        FuseByStrategy, MinimumUnionStrategy, ComplementUnionStrategy,
    )
}
