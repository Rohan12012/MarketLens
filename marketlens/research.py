"""Load the recorded SQL study for the research page."""
import json
from pathlib import Path

from marketlens.compare_periods import compare_periods

ROOT = Path(__file__).resolve().parents[1]


def load_research(database=None, manifest=None):
    database = Path(database) if database is not None else ROOT / 'data' / 'study' / 'study.sqlite'
    manifest = Path(manifest) if manifest is not None else ROOT / 'config' / 'study-runs.json'
    if not database.is_file():
        raise FileNotFoundError('The saved study database is not available on this machine.')
    runs = json.loads(manifest.read_text())
    return compare_periods(database, runs['full_run'], runs['first_run'], runs['second_run'])
