import argparse
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import similarity
from union_find import UnionFind


ROOT = Path(__file__).parent
TASK1_OUT = ROOT.parent / 'task_1' / 'output_data'
INTERMEDIATE = ROOT / 'intermediate'
OUT = ROOT / 'output_data'
JOB = ROOT / 'snm_job.py'
GOLD_PATH = ROOT / 'gold.json'

SOURCES = ('ozon', 'wb', 'ym')
PASSES = ('brand_model', 'model', 'title')


def _merge_inputs() -> Path:
    INTERMEDIATE.mkdir(exist_ok=True)
    all_path = INTERMEDIATE / 'all.jsonl'
    with open(all_path, 'w') as fout:
        for source in SOURCES:
            with open(TASK1_OUT / f'{source}.jsonl') as fin:
                for i, line in enumerate(fin):
                    rec = json.loads(line)
                    rec['rec_id'] = f'{source}#{i}'
                    fout.write(json.dumps(rec, ensure_ascii=False))
                    fout.write('\n')
    return all_path


def _run_pass(pass_name: str, input_path: Path, threshold: float) -> Path:
    out_path = INTERMEDIATE / f'pairs_{pass_name}.jsonl'
    cmd = [
        sys.executable, str(JOB),
        '--pass-name', pass_name,
        '--threshold', str(threshold),
        str(input_path),
    ]
    with open(out_path, 'w') as fout:
        subprocess.run(cmd, stdout=fout, check=True)
    return out_path


def _load_pairs(pass_files: list[Path]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for p in pass_files:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                pair = json.loads(line)
                ka, kb = pair['a']['rec_id'], pair['b']['rec_id']
                if ka > kb:
                    ka, kb = kb, ka
                key = (ka, kb)
                prev = seen.get(key)
                if prev is None or pair['score'] > prev['score']:
                    seen[key] = pair
    return list(seen.values())


def _build_clusters(records: list[dict], pairs: list[dict]) -> list[list[dict]]:
    uf = UnionFind()
    for r in records:
        uf.add(r['rec_id'])
    for p in pairs:
        uf.union(p['a']['rec_id'], p['b']['rec_id'])
    by_id = {r['rec_id']: r for r in records}
    groups = uf.groups()
    clusters = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members_sorted = sorted(members)
        clusters.append([by_id[m] for m in members_sorted])
    clusters.sort(key=lambda c: (-len(c), c[0]['rec_id']))
    return clusters


def _write_duplicates(clusters: list[list[dict]]) -> None:
    payload = {
        'cluster_count': len(clusters),
        'duplicate_record_count': sum(len(c) for c in clusters),
        'clusters': [
            {
                'cluster_id': i,
                'size': len(c),
                'members': [
                    {
                        'rec_id': r['rec_id'],
                        'marketplace': r['marketplace'],
                        'source_id': r['source_id'],
                        'title': r['title'],
                        'brand': r['brand'],
                        'model': r['model'],
                    }
                    for r in c
                ],
            }
            for i, c in enumerate(clusters)
        ],
    }
    OUT.mkdir(exist_ok=True)
    with open(OUT / 'duplicates.json', 'w') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_pairs(pairs: list[dict]) -> None:
    pairs_sorted = sorted(pairs, key=lambda p: -p['score'])
    with open(OUT / 'pairs.jsonl', 'w') as f:
        for p in pairs_sorted:
            slim = {
                'a': p['a']['rec_id'],
                'b': p['b']['rec_id'],
                'score': p['score'],
                'pass': p['pass'],
                'reason': p['reason'],
                'breakdown': p.get('breakdown', {}),
                'a_title': p['a']['title'],
                'b_title': p['b']['title'],
            }
            f.write(json.dumps(slim, ensure_ascii=False))
            f.write('\n')


def _gold_pairs() -> set[tuple[str, str]]:
    with open(GOLD_PATH) as f:
        gold = json.load(f)
    out = set()
    for cluster in gold['clusters']:
        for a, b in combinations(sorted(cluster['members']), 2):
            out.add((a, b))
    return out


def _pred_pairs_from_clusters(clusters: list[list[dict]]) -> set[tuple[str, str]]:
    out = set()
    for c in clusters:
        ids = sorted(r['rec_id'] for r in c)
        for a, b in combinations(ids, 2):
            out.add((a, b))
    return out


def _calculate_metrics(pred: set, gold: set) -> dict[str, Any]:
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        'true_positive':  tp,
        'false_positive': fp,
        'false_negative': fn,
        'precision': round(precision, 4),
        'recall':    round(recall, 4),
        'f1':        round(f1, 4),
        'gold_pair_count': len(gold),
        'pred_pair_count': len(pred),
        'missed_pairs':    sorted(gold - pred),
        'spurious_pairs':  sorted(pred - gold),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Multi-pass Sorted Neighborhood duplicate detection')
    parser.add_argument(
        '--threshold',
        type=float,
        default=similarity.THRESHOLD,
        help=f'Composite similarity threshold (default: {similarity.THRESHOLD})',
    )
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    all_path = _merge_inputs()
    with open(all_path) as f:
        records = [json.loads(l) for l in f]

    print(f'Threshold:         {args.threshold}')
    pass_files = []
    for p in PASSES:
        print(f'  pass: {p} ...', flush=True)
        pass_files.append(_run_pass(p, all_path, args.threshold))

    pairs = _load_pairs(pass_files)
    clusters = _build_clusters(records, pairs)
    _write_duplicates(clusters)
    _write_pairs(pairs)

    pred = _pred_pairs_from_clusters(clusters)
    gold = _gold_pairs()
    metrics = _calculate_metrics(pred, gold)
    metrics['threshold'] = args.threshold
    with open(OUT / 'metrics.json', 'w') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f'Records:           {len(records)}')
    print(f'Pairs predicted:   {len(pred)}')
    print(f'Gold pairs:        {len(gold)}')
    print(f'Clusters:          {len(clusters)}')
    print(f'{metrics=}')


if __name__ == '__main__':
    main()
