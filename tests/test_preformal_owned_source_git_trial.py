"""A retained trial binds the exact seven pinned source calls."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import preformal_owned_source_git_trial as trial


REVISION = 'a' * 40
PIN = trial.observed._pin(b'fixture')


def fixture():
    selected = {name: PIN for name in trial.owner.chain.SOURCES}
    source = {'revision': REVISION, 'orchestrator_selected': selected,
              'owner': PIN,
              'scope': 'clean-head-selected-working-raw-not-source-closure'}
    calls = []
    for call_id, operation, path, expected in (
            [('head', 'head', None, None),
             ('status', 'status', None, None)] +
            [(f'selected-source-{index}', 'source_blob', name, PIN)
             for index, name in enumerate(trial.owner.chain.SOURCES)] +
            [('owner-source', 'source_blob', trial.owner.SOURCE, PIN)]):
        calls.append({'call_id': call_id, 'operation': operation,
                      'source_path': path, 'expected_output_pin': expected,
                      'call_status': 'verified', 'receipt_pin': PIN,
                      'error_type': None})
    return source, calls


class OwnedSourceGitTrialTests(unittest.TestCase):
    def test_exact_inventory_and_order_required(self):
        source, calls = fixture()
        trial._calls({'calls': calls}, source)
        for changed in (calls[:-1], list(reversed(calls))):
            with self.assertRaises(ValueError):
                trial._calls({'calls': changed}, source)
        mismatched = [dict(row) for row in calls]
        mismatched[3]['expected_output_pin'] = trial.observed._pin(b'wrong')
        with self.assertRaises(ValueError):
            trial._calls({'calls': mismatched}, source)

    def test_retained_trial_checks_verified_pinned_calls_without_second_read(self):
        source, calls = fixture()
        with tempfile.TemporaryDirectory(prefix='banto-source-git-trial-') as tmp:
            root = Path(tmp).resolve()
            target = root / 'artifacts' / 'anomaly-v03-preformal-owned-source-git-test'
            target.mkdir(parents=True)
            result = {'format': trial.FORMAT, 'status': 'verified',
                      'scope': 'seven-direct-selected-source-Git-calls-only',
                      'root': str(target), 'revision': REVISION,
                      'policy_path': str(root / 'artifacts' / 'policy.json'),
                      'policy_pin': PIN, 'session_manifest_pin': PIN,
                      'source': source, 'call_count': 7,
                      'integration_pending': True,
                      'registered_data_read': False,
                      'formal_permission': False,
                      'source_closure_complete': False,
                      'runtime_closure_complete': False,
                      'execution_authenticated': False}
            raw = trial.io.json_bytes(result)
            (target / 'result.json').write_bytes(raw)
            retained = {'status': 'verified_retained',
                        'call_status': 'verified', 'call_count': 7,
                        'calls': calls, 'formal_permission': False,
                        'integration_pending': True}
            with patch.object(trial, 'ROOT', root), \
                 patch.object(trial.source_git, 'verify_retained',
                              return_value=retained):
                self.assertEqual(trial.verify_saved(
                    target, trial.observed._pin(raw))['call_count'], 7)
                retained['calls'] = calls[:-1]
                with self.assertRaises(ValueError):
                    trial.verify_saved(target, trial.observed._pin(raw))


if __name__ == '__main__':
    unittest.main()
