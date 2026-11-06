"""Check a study snapshot against the XNYS regular-session calendar."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import exchange_calendars as calendars
import pandas as pd

from marketlens.data import load_prices, validate_prices

ROOT = Path(__file__).resolve().parents[1]


def audit_sessions(prices, start, end):
    validate_prices(prices)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start >= end:
        raise ValueError('Start must be before the exclusive end date.')
    last_day = end - pd.Timedelta(days=1)
    calendar = calendars.get_calendar('XNYS', start=start, end=last_day)
    sessions = calendar.sessions.tz_localize(None)
    expected = sessions[(sessions >= start) & (sessions < end)]
    missing = expected.difference(prices.index)
    unexpected = prices.index.difference(expected)
    return {
        'calendar': 'XNYS', 'exchange_calendars_version': version('exchange-calendars'),
        'requested_start': start.date().isoformat(), 'requested_end_exclusive': end.date().isoformat(),
        'expected_sessions': len(expected), 'observed_sessions': len(prices),
        'missing_sessions': missing.strftime('%Y-%m-%d').tolist(),
        'unexpected_sessions': unexpected.strftime('%Y-%m-%d').tolist(),
        'passed': len(missing) == 0 and len(unexpected) == 0,
    }


def audit_snapshot(snapshot):
    snapshot = Path(snapshot)
    metadata = json.loads((snapshot / 'metadata.json').read_text())
    checksum = hashlib.sha256((snapshot / 'prices.csv').read_bytes()).hexdigest()
    if checksum != metadata['prices_sha256']:
        raise ValueError('Price checksum does not match the snapshot metadata.')
    report = audit_sessions(load_prices(snapshot / 'prices.csv'),
                            metadata['requested_start'], metadata['requested_end_exclusive'])
    report['prices_sha256'] = checksum
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    report = audit_snapshot(args.snapshot)
    output = ROOT / 'reports' / 'quality' / f'{args.snapshot.name}-calendar.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(f'Audit saved to {output}')
    raise SystemExit(0 if report['passed'] else 1)
