"""Prepare the study database and dashboard run IDs with one command."""
import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from marketlens.audit_calendar import audit_snapshot
from marketlens.compare_periods import compare_periods
from marketlens.prepare_study_data import prepare_study_data
from marketlens.run_study import run_study
from marketlens.store_study import store_study

ROOT = Path(__file__).resolve().parents[1]


def build_study(snapshot=None):
    snapshot = Path(snapshot) if snapshot is not None else prepare_study_data()
    audit = audit_snapshot(snapshot)
    if not audit['passed']:
        raise ValueError('Trading-date audit failed. Review the snapshot before running the study.')
    database = ROOT / 'data' / 'study' / 'study.sqlite'
    runs = {}
    for key, window in [('full_run', 'full'), ('first_run', '2016-2020'), ('second_run', '2021-2025')]:
        report = run_study(snapshot, ROOT / 'reports' / 'study', window=window)
        runs[key] = store_study(report, database)
    comparison = compare_periods(database, runs['full_run'], runs['first_run'], runs['second_run'])
    manifest = ROOT / 'config' / 'study-runs.json'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    # Keep the dashboard on its previous runs unless the entire build succeeds.
    with NamedTemporaryFile('w', dir=manifest.parent, suffix='.tmp', delete=False) as file:
        json.dump({**runs, 'prices_sha256': audit['prices_sha256']}, file, indent=2)
        file.write('\n')
        temporary = Path(file.name)
    temporary.replace(manifest)
    print(f'Research study ready: {len(comparison)} cases in {database}')
    print(f'Dashboard run IDs updated: {manifest}')
    return runs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Reuse a saved study snapshot without downloading')
    args = parser.parse_args()
    try:
        build_study(args.snapshot)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Study setup failed: {exc}\n')
