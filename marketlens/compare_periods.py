"""Compare three recorded study runs using SQL."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3

import pandas as pd

from marketlens.study import WINDOWS

ROOT = Path(__file__).resolve().parents[1]


def compare_periods(database, full_run, first_run, second_run):
    parameters = {'full_run': full_run, 'first_run': first_run, 'second_run': second_run}
    with closing(sqlite3.connect(database)) as connection:
        checksums = set()
        for run_id, window in zip(parameters.values(), ['full', '2016-2020', '2021-2025']):
            row = connection.execute('SELECT prices_sha256, settings_json FROM study_runs WHERE run_id = ?',
                                     (run_id,)).fetchone()
            if row is None:
                raise ValueError(f'Run not found in the database: {run_id}')
            checksum, text = row
            settings = json.loads(text)
            if (settings['start_inclusive'], settings['end_exclusive']) != WINDOWS[window]:
                raise ValueError(f'Run {run_id} does not cover the expected {window} window.')
            checksums.add(checksum)
        if len(checksums) != 1:
            raise ValueError('The three runs must use the same source price snapshot.')
        query = (ROOT / 'docs' / 'study-comparison.sql').read_text()
        comparison = pd.read_sql_query(query, connection, params=parameters)
    if len(comparison) != 72:
        raise ValueError('Expected 24 cases per window, 72 in total.')
    return comparison


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('full_run')
    parser.add_argument('first_run')
    parser.add_argument('second_run')
    parser.add_argument('--database', type=Path, default=ROOT / 'data' / 'study' / 'study.sqlite')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'study' / 'period-comparison.csv')
    args = parser.parse_args()
    comparison = compare_periods(args.database, args.full_run, args.first_run, args.second_run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(args.output, index=False)
    print(f'Saved {len(comparison)} comparisons to {args.output}')
    display = comparison.loc[comparison.cost_bps == 10,
                             ['first_date', 'last_date', 'allocation', 'strategy', 'total_return', 'return_rank', 'max_drawdown']].copy()
    for column in ['total_return', 'max_drawdown']:
        display[column] = display[column].map(lambda value: f'{value:.2%}')
    print('10-basis-point scenarios (the CSV includes all four rates):')
    print(display.to_string(index=False))
