"""Run the tests and save evidence for the dashboard's Validation tab."""
from datetime import datetime, timezone
import json
import unittest

from marketlens.validation import ROOT, RECEIPT, source_fingerprint, collect_study_checks


def main():
    before = source_fingerprint()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    tests = {'total': result.testsRun, 'failures': len(result.failures),
             'errors': len(result.errors), 'skipped': len(result.skipped),
             'expected_failures': len(result.expectedFailures),
             'unexpected_successes': len(result.unexpectedSuccesses),
             'successful': result.wasSuccessful()}
    tests['passed'] = tests['total'] - sum(tests[key] for key in
                                          ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'])
    try:
        study = collect_study_checks()
    except Exception as exc:
        study = {'checks': [{'check': 'Study validation', 'status': 'Failed', 'detail': str(exc)}]}
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'source_fingerprint': before, 'tests': tests, 'study': study}
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Validation evidence saved to {RECEIPT}')
    if source_fingerprint() != before:
        print('Source changed during validation. The dashboard will mark this record out of date.')
    return 0 if tests['successful'] and all(check['status'] not in ['Failed', 'Different'] for check in study['checks']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
