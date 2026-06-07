import argparse
import json
import subprocess
import sys
from pathlib import Path

from strategies import STRATEGIES


ROOT = Path(__file__).parent
TASK2_INT = ROOT.parent / 'task_2' / 'intermediate'
TASK2_OUT = ROOT.parent / 'task_2' / 'output_data'
INTERMEDIATE = ROOT / 'intermediate'
OUT = ROOT / 'output_data'
JOB = ROOT / 'fuse_job.py'

SINGLETON_ID_OFFSET = 1000


def _load_records() -> list[dict]:
    path = TASK2_INT / 'all.jsonl'
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_clusters() -> list[dict]:
    path = TASK2_OUT / 'duplicates.json'
    with open(path) as f:
        return json.load(f)['clusters']


def _tag_with_cluster(records: list[dict], clusters: list[dict]) -> tuple[list[dict], int, int]:
    rec_id_to_cid: dict[str, int] = {}
    for c in clusters:
        for m in c['members']:
            rec_id_to_cid[m['rec_id']] = c['cluster_id']

    tagged: list[dict] = []
    next_singleton = SINGLETON_ID_OFFSET
    singleton_count = 0
    for r in records:
        rid = r['rec_id']
        if rid in rec_id_to_cid:
            cid = rec_id_to_cid[rid]
        else:
            cid = next_singleton
            next_singleton += 1
            singleton_count += 1
        out = dict(r)
        out['_cluster_id'] = cid
        tagged.append(out)
    return tagged, len(clusters), singleton_count


def _write_jsonl(records: list[dict], path: Path) -> None:
    with open(path, 'w') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write('\n')


def _run_fuse_job(strategy: str, input_path: Path) -> Path:
    out_path = INTERMEDIATE / f'fused_{strategy}.jsonl'
    cmd = [sys.executable, str(JOB), '--strategy', strategy, str(input_path)]
    with open(out_path, 'w') as fout:
        subprocess.run(cmd, stdout=fout, check=True)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Fusion with different strategies')
    parser.add_argument(
        '--strategy',
        choices=sorted(STRATEGIES),
        default='fuse_by',
        help='Fusion strategy (default: fuse_by)',
    )
    args = parser.parse_args()

    INTERMEDIATE.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)

    records = _load_records()
    clusters = _load_clusters()
    tagged, multi_count, single_count = _tag_with_cluster(records, clusters)

    input_path = INTERMEDIATE / 'records_tagged.jsonl'
    _write_jsonl(tagged, input_path)

    fused_path = _run_fuse_job(args.strategy, input_path)
    with open(fused_path) as f:
        fused = [json.loads(line) for line in f if line.strip()]

    fused.sort(key=lambda r: (
        0 if r['_cluster_id'] < SINGLETON_ID_OFFSET else 1,
        r['_cluster_id'],
    ))

    out_path = OUT / f'fused_{args.strategy}.json'
    payload = {
        'strategy':           args.strategy,
        'input_clusters':     multi_count,
        'input_singletons':   single_count,
        'fused_record_count': len(fused),
        'records':            fused,
    }
    with open(out_path, 'w') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'Strategy:               {args.strategy}')
    print(f'Multi-source clusters:  {multi_count}')
    print(f'Singletons:             {single_count}')
    print(f'Fused records:          {len(fused)}')
    print(f'Output:                 {out_path.relative_to(ROOT.parent)}')


if __name__ == '__main__':
    main()
