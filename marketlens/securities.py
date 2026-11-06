"""Load and search current US listings from Nasdaq Trader."""
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
import json
import ssl
from urllib.request import Request, urlopen
import certifi
import pandas as pd

SOURCES = {
    'nasdaq': 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt',
    'other': 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt',
}
CACHE = Path(__file__).resolve().parents[1] / 'data' / 'directory' / 'listings.json'
EXCHANGES = {'N': 'NYSE', 'P': 'NYSE Arca', 'A': 'NYSE American', 'Z': 'Cboe BZX',
             'V': 'IEX', 'L': 'LTSE', 'Q': 'Nasdaq', 'B': 'Nasdaq Texas',
             'M': 'NYSE Texas', 'F': 'Texas Stock Exchange'}


def parse_directory(text, source):
    lines = [line for line in text.splitlines() if not line.startswith('File Creation Time:')]
    frame = pd.read_csv(StringIO('\n'.join(lines)), sep='|', dtype=str, keep_default_na=False)
    symbol_column = 'Symbol' if source == 'nasdaq' else 'ACT Symbol'
    required = {symbol_column, 'Security Name', 'Test Issue', 'ETF'}
    if source != 'nasdaq':
        required.add('Exchange')
    if not required.issubset(frame.columns):
        raise ValueError('Listing directory has an unexpected format.')
    frame = frame.loc[(frame['Test Issue'] == 'N') & frame[symbol_column].ne('')].copy()
    result = pd.DataFrame({'Symbol': frame[symbol_column], 'Name': frame['Security Name'],
                           'Type': frame['ETF'].map({'Y': 'ETF', 'N': 'Stock / other'})})
    result['Exchange'] = 'Nasdaq' if source == 'nasdaq' else frame['Exchange'].map(EXCHANGES).fillna(frame['Exchange'])
    # Yahoo uses BRK-B where the directory uses BRK.B. Other suffixes may
    # still need a manually entered Yahoo symbol.
    result['Price symbol'] = result['Symbol'].str.replace('.', '-', regex=False)
    return result.reset_index(drop=True)


def load_directory(refresh=False, cache_path=CACHE):
    cache_path = Path(cache_path)
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        age = datetime.now(timezone.utc) - datetime.fromisoformat(cached['retrieved_at_utc'])
        if age < timedelta(days=1):
            frame = pd.DataFrame(cached['listings'])
            frame['Exchange'] = frame['Exchange'].replace(EXCHANGES)
            return frame, cached['retrieved_at_utc']
    frames = []
    for source, url in SOURCES.items():
        request = Request(url, headers={'User-Agent': 'MarketLens/1.0'})
        context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=25, context=context) as response:
            frames.append(parse_directory(response.read().decode('utf-8-sig'), source))
    directory = pd.concat(frames, ignore_index=True).drop_duplicates('Symbol').sort_values('Symbol').reset_index(drop=True)
    if directory.empty:
        raise ValueError('Listing directory returned no securities.')
    retrieved = datetime.now(timezone.utc).isoformat()
    payload = {'retrieved_at_utc': retrieved, 'sources': SOURCES, 'listings': directory.to_dict('records')}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload))
    temporary.replace(cache_path)
    return directory, retrieved


def search_directory(directory, query='', exchange='All exchanges', security_type='All types'):
    result = directory
    if exchange != 'All exchanges':
        result = result.loc[result['Exchange'] == exchange]
    if security_type != 'All types':
        result = result.loc[result['Type'] == security_type]
    if query.strip():
        term = query.strip()
        result = result.loc[result['Symbol'].str.contains(term, case=False, regex=False) |
                            result['Name'].str.contains(term, case=False, regex=False)]
    return result
