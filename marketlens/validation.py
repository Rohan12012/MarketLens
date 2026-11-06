"""Read saved validation evidence and check the selected study exports."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

from marketlens.audit_calendar import audit_snapshot
from marketlens.compare_periods import compare_periods

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'reports' / 'validation' / 'latest.json'
RUN_KEYS = ['full_run', 'first_run', 'second_run']


def source_fingerprint(root=ROOT):
    paths = [root / name for name in ['app.py', 'main.py', 'dashboard.css', 'requirements.txt',
                                     'requirements-lock.txt', '.streamlit/config.toml', '.github/workflows/tests.yml']]
    for directory, pattern in [('marketlens', '*.py'), ('tests', '*.py'), ('pages', '*.py'),
                               ('config', '*.json'), ('docs', '*.sql')]:
        paths.extend((root / directory).glob(pattern))
    digest = hashlib.sha256()
    for path in sorted(paths):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def load_validation():
    if not RECEIPT.is_file():
        return None
    report = json.loads(RECEIPT.read_text())
    report['is_current'] = report['source_fingerprint'] == source_fingerprint()
    for name, checksum in report.get('study', {}).get('checked_files', {}).items():
        path = Path(name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            report['is_current'] = False
            break
    return report


def check_accounting(comparison, report_root):
    checked = 0
    for row in comparison.itertuples(index=False):
        name = f'{row.allocation.lower().replace(" ", "-")}__{row.strategy.lower()}__{row.cost_bps}bps'
        folder = Path(report_root) / row.run_id / name
        holdings = pd.read_csv(folder / 'holdings.csv', index_col=0)
        values = pd.read_csv(folder / 'portfolio_value.csv', index_col=0).iloc[:, 0]
        trades = pd.read_csv(folder / 'rebalance_log.csv', index_col=0)
        if not np.allclose(holdings.sum(axis=1), values, rtol=1e-9, atol=1e-7):
            raise ValueError(f'Holdings do not reconcile: {name}')
        if not np.isclose(values.iloc[0], 10000):
            raise ValueError(f'Wrong starting capital: {name}')
        if not np.isclose(values.iloc[-1] / values.iloc[0] - 1, row.total_return):
            raise ValueError(f'Return does not match ending value: {name}')
        if not trades.empty:
            checks = [
                np.allclose(values.loc[trades.index] + trades.cost, trades.value_before),
                np.allclose(trades.sales - trades.purchases, trades.cost, atol=1e-7),
                np.allclose(trades.cost, trades.gross_traded * row.cost_bps / 10000),
            ]
            if not all(checks):
                raise ValueError(f'Trading fees do not reconcile: {name}')
        checked += 1
    return checked


def collect_study_checks():
    result = {'checks': []}
    database = ROOT / 'data' / 'study' / 'study.sqlite'
    if not database.is_file():
        return {'checks': [{'check': 'Study results', 'status': 'Not available', 'detail': 'No local database.'}]}
    runs = json.loads((ROOT / 'config' / 'study-runs.json').read_text())
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute('SELECT settings_json FROM study_runs WHERE run_id = ?', (runs['full_run'],)).fetchone()
    if row is None:
        raise ValueError('Selected full-period run is missing from the database.')
    settings = json.loads(row[0])
    result['audit'] = audit_snapshot(settings['snapshot'])
    audit = result['audit']
    result['checks'].append({'check': 'Input checksum & trading dates', 'status': 'Passed' if audit['passed'] else 'Failed',
                             'detail': f'{audit["observed_sessions"]} observed / {audit["expected_sessions"]} expected sessions; {len(audit["missing_sessions"])} missing, {len(audit["unexpected_sessions"])} unexpected.'})
    comparison = compare_periods(database, *(runs[key] for key in RUN_KEYS))
    result['cases'] = len(comparison)
    result['checks'].append({'check': 'SQL case coverage', 'status': 'Passed', 'detail': '72 cases across the three planned windows, using one source snapshot.'})
    try:
        result['accounting_cases'] = check_accounting(comparison, ROOT / 'reports' / 'study')
        result['checks'].append({'check': 'Holdings, returns & fees', 'status': 'Passed', 'detail': f'{result["accounting_cases"]} case exports reconciled.'})
    except (OSError, ValueError, KeyError) as exc:
        result['checks'].append({'check': 'Holdings, returns & fees', 'status': 'Failed', 'detail': str(exc)})
    try:
        reference = json.loads((ROOT / 'config' / 'reference-study-runs.json').read_text())
        original = compare_periods(database, *(reference[key] for key in RUN_KEYS))
        keys = ['first_date', 'last_date', 'allocation', 'strategy', 'cost_bps']
        left = comparison.drop(columns='run_id').sort_values(keys).reset_index(drop=True)
        right = original.drop(columns='run_id').sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(left, right)
        result['checks'].append({'check': 'Rebuild vs. original results', 'status': 'Passed', 'detail': 'All 72 summary rows match the original recorded runs.'})
    except (OSError, ValueError, KeyError) as exc:
        result['checks'].append({'check': 'Rebuild vs. original results', 'status': 'Not available', 'detail': str(exc)})
    except AssertionError:
        result['checks'].append({'check': 'Rebuild vs. original results', 'status': 'Different', 'detail': 'Results differ from the original runs. Review data and method changes before interpreting.'})
    verification_file = ROOT / 'reports' / 'quality' / 'price-verification.json'
    verification = json.loads(verification_file.read_text()) if verification_file.exists() else None
    if verification and verification.get('prices_sha256') == audit['prices_sha256']:
        result['price_verification'] = verification
        detail = f'{verification["verified_observations"]} of {verification["sample_count"]} sampled prices independently verified. {verification["detail"]}'
    else:
        detail = 'No independent price-verification evidence is available for the selected snapshot.'
    result['checks'].append({'check': 'Independent price sample', 'status': 'Not verified', 'detail': detail})
    files = [database, Path(settings['snapshot']) / 'prices.csv']
    if verification_file.exists():
        files.append(verification_file)
    for row in comparison.itertuples(index=False):
        name = f'{row.allocation.lower().replace(" ", "-")}__{row.strategy.lower()}__{row.cost_bps}bps'
        folder = ROOT / 'reports' / 'study' / row.run_id / name
        files.extend(folder / filename for filename in ['holdings.csv', 'portfolio_value.csv', 'rebalance_log.csv'])
    result['checked_files'] = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in files if path.is_file()}
    return result
