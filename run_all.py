import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
ALL_TASKS = ('task_0', 'task_1', 'task_2', 'task_3')
ALL_STRATEGIES = ('fuse_by', 'minimum_union', 'complement_union')


def _run(cmd: list[str]) -> None:
    print(f'$ {" ".join(cmd)}', flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run all',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--threshold', type=float, default=None,
        help='Similarity threshold for task_2 (default: task_2 default = 0.60)',
    )
    parser.add_argument(
        '--strategy', choices=(*ALL_STRATEGIES, 'all'), default='all',
        help="Fusion strategy for task_3. 'all' runs all three (default).",
    )
    parser.add_argument(
        '--skip', action='append', default=[], choices=ALL_TASKS,
        help='Skip a task (repeatable).',
    )
    args = parser.parse_args()

    py = sys.executable

    if 'task_0' not in args.skip:
        _run([py, 'task_0/run.py'])

    if 'task_1' not in args.skip:
        _run([py, 'task_1/run.py'])

    if 'task_2' not in args.skip:
        cmd = [py, 'task_2/run.py']
        if args.threshold is not None:
            cmd += ['--threshold', str(args.threshold)]
        suffix = f' (threshold={args.threshold})' if args.threshold is not None else ''
        _run(cmd)

    if 'task_3' not in args.skip:
        strategies = ALL_STRATEGIES if args.strategy == 'all' else (args.strategy,)
        for s in strategies:
            _run([py, 'task_3/run.py', '--strategy', s])


if __name__ == '__main__':
    main()
