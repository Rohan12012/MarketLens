"""Prepare a fixed price-check sample and record a secondary-source access probe."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import ssl
from urllib.request import Request, urlopen

import certifi
import pandas as pd

from marketlens.data import load_prices

ROOT = Path(__file__).resolve().parents[1]


def prepare_sample(snapshot, output_root=None):
    snapshot = Path(snapshot)
    metadata = json.loads((snapshot / 'metadata.json').read_text())
    checksum = hashlib.sha256((snapshot / 'prices.csv').read_bytes()).hexdigest()
    if checksum != metadata['prices_sha256']:
        raise ValueError('Snapshot checksum does not match.')
    plan = json.loads((ROOT / 'config' / 'price-check-sample.json').read_text())
    prices = load_prices(snapshot / 'prices.csv')
    records = []
    for symbol in plan['symbols']:
        for day in plan['dates']:
            records.append({'symbol': symbol, 'date': day,
                            'primary_adjusted_close': float(prices.at[pd.Timestamp(day), symbol]),
                            'reference_close': None, 'difference': None,
                            'status': 'Not verified'})
    output = Path(output_root or ROOT / 'reports' / 'quality')
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output / 'price-check-sample.csv', index=False)
    return output, checksum, len(records)


def record_probe(output, checksum, sample_count):
    url = 'https://stooq.com/q/d/l/?s=aapl.us&i=d&d1=20160104&d2=20251231'
    evidence = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                'status': 'Not verified', 'sample_count': sample_count,
                'verified_observations': 0, 'prices_sha256': checksum, 'source_url': url,
                'adjustment_basis': 'Unconfirmed; not treated as equivalent to Yahoo adjusted close'}
    try:
        request = Request(url, headers={'User-Agent': 'MarketLens/1.0'})
        with urlopen(request, timeout=25, context=ssl.create_default_context(cafile=certifi.where())) as response:
            body = response.read()
            evidence['http_status'] = response.status
            evidence['content_type'] = response.headers.get('Content-Type', '')
        text = body.decode('utf-8', errors='replace')
        evidence['response_sha256'] = hashlib.sha256(body).hexdigest()
        if text.lstrip().startswith('Date,Open,High,Low,Close,Volume'):
            evidence['detail'] = 'CSV was available for the AAPL probe, but its adjustment basis has not been confirmed. No prices are marked verified.'
        else:
            evidence['detail'] = 'The AAPL CSV endpoint returned a non-CSV response. Independent values were not obtained for the 12-point sample.'
        raw = ROOT / 'data' / 'verification'
        raw.mkdir(parents=True, exist_ok=True)
        (raw / 'stooq-probe-response.txt').write_bytes(body)
    except Exception as exc:
        evidence['detail'] = f'Secondary source request failed: {exc}. No prices are marked verified.'
    (output / 'price-verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    output, checksum, count = prepare_sample(args.snapshot)
    result = record_probe(output, checksum, count)
    print(json.dumps(result, indent=2))
    print(f'Sample and evidence: {output}')
