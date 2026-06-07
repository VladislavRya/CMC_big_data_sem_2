import csv
import json
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).parent
TASK0_OUT = ROOT.parent / 'task_0' / 'output_data'
INTERMEDIATE = ROOT / 'intermediate'
OUT = ROOT / 'output_data'
JOB = ROOT / 'job.py'

SOURCES: dict[str, str] = {
    'ozon': 'ozon.json',
    'wb':   'wb.yaml',
    'ym':   'ym.csv',
}


def _load_records(source: str) -> Iterable[dict[str, Any]]:
    path = TASK0_OUT / SOURCES[source]
    if source == 'ozon':
        with open(path, 'r') as f:
            return json.load(f)
    if source == 'wb':
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    if source == 'ym':
        with open(path, 'r', newline='') as f:
            return list(csv.DictReader(f))
    raise ValueError(f'unknown source: {source}')


def _to_jsonl(records: Iterable[dict[str, Any]], dst: Path):
    with open(dst, 'w') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False))
            f.write('\n')


def _run_mrjob(source: str, input_path: Path, output_path: Path) -> None:
    cmd = [sys.executable, str(JOB), '--source', source, str(input_path)]
    with open(output_path, 'w') as fout:
        subprocess.run(cmd, stdout=fout, check=True)


def main() -> None:
    INTERMEDIATE.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    for source in SOURCES:
        records = _load_records(source)
        intermediate_path = INTERMEDIATE / f'{source}.jsonl'
        _to_jsonl(records, intermediate_path)
        output_path = OUT / f'{source}.jsonl'
        _run_mrjob(source, intermediate_path, output_path)


if __name__ == '__main__':
    main()
