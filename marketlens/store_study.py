"""Load a saved study into SQLite and compare its cost scenarios."""
import argparse
from contextlib import closing
import csv
import hashlib
from itertools import product
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]


def store_study(report_folder, database):
    report = Path(report_folder).resolve()
    run_id = report.name
    settings = json.loads((report / 'settings.json').read_text())
    summary_file = report / 'summary.csv'
    checksum = hashlib.sha256(summary_file.read_bytes()).hexdigest()
    with summary_file.open(newline='') as file:
        records = list(csv.DictReader(file))
    expected = set(product(settings['allocations'], ['Buy-and-hold', 'Monthly', 'Daily'], settings['cost_rates_bps']))
    cases = {(r['allocation'], r['strategy'], int(r['cost_bps'])) for r in records}
    if cases != expected or len(records) != len(expected) or len(records) != settings['cases']:
        raise ValueError('Results contain missing or duplicate study cases.')
    rows = [(run_id, r['allocation'], r['strategy'], int(r['cost_bps']),
             float(r['initial_value']), float(r['ending_value']), float(r['Total return']),
             float(r['Annualized volatility']), float(r['Max drawdown']),
             float(r['total_cost']), float(r['one_way_turnover'])) for r in records]
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    metadata = json.dumps(settings, sort_keys=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executescript((ROOT / 'docs' / 'study-schema.sql').read_text())
        existing = connection.execute(
            'SELECT summary_sha256, settings_json FROM study_runs WHERE run_id = ?', (run_id,)
        ).fetchone()
        if existing:
            if existing != (checksum, metadata):
                raise ValueError('This run is already stored with different results or settings.')
        else:
            connection.execute('INSERT INTO study_runs VALUES (?, ?, ?, ?, ?, ?)',
                               (run_id, settings['prices_sha256'], checksum, metadata,
                                settings['actual_first_date'], settings['actual_last_date']))
            connection.executemany('INSERT INTO study_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', rows)
    return run_id


def compare_costs(database, run_id, cost_bps=10):
    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        query = (ROOT / 'docs' / 'analysis.sql').read_text()
        rows = connection.execute(query, {'run_id': run_id, 'cost_bps': cost_bps}).fetchall()
        return [dict(row) for row in rows]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report_folder', type=Path)
    parser.add_argument('--database', type=Path, default=ROOT / 'data' / 'study' / 'study.sqlite')
    args = parser.parse_args()
    run_id = store_study(args.report_folder, args.database)
    print(f'Stored run {run_id} in {args.database}')
    comparison = compare_costs(args.database, run_id)
    if comparison:
        writer = csv.DictWriter(sys.stdout, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)
