"""Check setup sequencing and preserve the dashboard selection on failure."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from marketlens.build_study import build_study


class BuildStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.snapshot = self.root / 'saved-snapshot'
        self.manifest = self.root / 'config' / 'study-runs.json'
        self.manifest.parent.mkdir()
        self.manifest.write_text('{"previous": true}\n')
        self.original = self.manifest.read_text()
        fixtures = {
            'ROOT': self.root,
            'prepare_study_data': None,
            'audit_snapshot': None,
            'run_study': None,
            'store_study': None,
            'compare_periods': None,
        }
        self.mocks = {}
        for name, value in fixtures.items():
            patcher = patch(f'marketlens.build_study.{name}', value) if name == 'ROOT' else patch(f'marketlens.build_study.{name}')
            mocked = patcher.start()
            self.addCleanup(patcher.stop)
            self.mocks[name] = mocked
        self.mocks['prepare_study_data'].return_value = self.snapshot
        self.mocks['audit_snapshot'].return_value = {'passed': True, 'prices_sha256': 'test-checksum'}
        self.mocks['run_study'].side_effect = [self.root / name for name in ['full', 'first', 'second']]
        self.mocks['store_study'].side_effect = ['full-id', 'first-id', 'second-id']
        self.mocks['compare_periods'].return_value = pd.DataFrame({'case': range(72)})

    def test_success_updates_manifest_after_all_windows(self):
        runs = build_study(self.snapshot)
        self.mocks['prepare_study_data'].assert_not_called()
        self.assertEqual([call.kwargs['window'] for call in self.mocks['run_study'].call_args_list],
                         ['full', '2016-2020', '2021-2025'])
        self.assertTrue(all(call.args[0] == self.snapshot for call in self.mocks['run_study'].call_args_list))
        saved = json.loads(self.manifest.read_text())
        self.assertEqual(saved['second_run'], runs['second_run'])
        self.assertEqual(saved['prices_sha256'], 'test-checksum')
        self.assertEqual(list(self.manifest.parent.glob('*.tmp')), [])

    def test_failed_window_preserves_previous_manifest(self):
        self.mocks['run_study'].side_effect = [self.root / 'full', ValueError('Failed simulation')]
        with self.assertRaises(ValueError):
            build_study(self.snapshot)
        self.assertEqual(self.manifest.read_text(), self.original)
        self.mocks['compare_periods'].assert_not_called()

    def test_failed_calendar_check_prevents_simulations(self):
        self.mocks['audit_snapshot'].return_value = {'passed': False}
        with self.assertRaisesRegex(ValueError, 'audit failed'):
            build_study(self.snapshot)
        self.mocks['run_study'].assert_not_called()
        self.assertEqual(self.manifest.read_text(), self.original)

    def test_no_snapshot_downloads_once(self):
        build_study()
        self.mocks['prepare_study_data'].assert_called_once_with()
        self.mocks['audit_snapshot'].assert_called_once_with(self.snapshot)
