"""Fail-closed checks for the retained pure-fixture budget probe."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_preformal_join_budget as probe


class ProbeBoundaryTests(unittest.TestCase):
    def test_revision_scope_requires_every_selected_raw_blob(self):
        pins = {name: probe._pin(name.encode()) for name in probe.SOURCES}
        with patch.object(probe.subprocess, 'check_output',
                          side_effect=lambda argv, **kwargs: argv[-1].split(':', 1)[1].encode()):
            self.assertEqual(probe._revision_scope('a' * 40, pins),
                             'selected-working-raw-matches-head-blobs')
        changed = dict(pins)
        changed[probe.SOURCES[0]] = probe._pin(b'changed')
        with patch.object(probe.subprocess, 'check_output',
                          side_effect=lambda argv, **kwargs: argv[-1].split(':', 1)[1].encode()):
            self.assertEqual(probe._revision_scope('a' * 40, changed),
                             'baseline-head-with-selected-working-raw-pins')

    def test_new_root_is_local_distinct_and_nonreusable(self):
        with tempfile.TemporaryDirectory() as parent, patch.object(probe, 'PARENT', Path(parent)):
            for name in ('formal', '../outside', probe.PREFIX + 'X', probe.PREFIX + 'a/b'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    probe._new_root(name)
            name = probe.PREFIX + 'one'
            target = probe._new_root(name)
            self.assertEqual(target, Path(parent) / name)
            target.mkdir()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                probe._new_root(name)

    def test_preflight_failure_retains_closed_receipt_and_starts_no_fixture(self):
        class StoppedBudget:
            def __init__(self, root, limits):
                self.root, self.limits = root, limits
            def start(self):
                raise ValueError('simulated_preflight_stop')
            def close(self):
                return {'passed': False, 'stop_reason': 'simulated_preflight_stop',
                        'monitor_exit_confirmed': True}

        with tempfile.TemporaryDirectory() as parent, \
             patch.object(probe, 'PARENT', Path(parent)), \
             patch.object(probe.budgets, 'FixtureBudget', StoppedBudget), \
             patch.object(probe, '_source_pins', return_value={}), \
             patch.object(probe, '_head', return_value='a' * 40), \
             patch.object(probe.invented_primary, 'example', side_effect=AssertionError('fixture started')):
            result = probe.run_measurement(probe.PREFIX + 'preflight')
            saved = json.loads((Path(result['root']) / 'receipt.json').read_bytes())
            self.assertEqual(saved['status'], 'failed')
            self.assertIn('simulated_preflight_stop', saved['reason'])
            self.assertFalse(saved['formal_permission'])
            self.assertFalse(saved['registered_data_read'])
            self.assertFalse(saved['real_producer_executed'])
            self.assertEqual(saved['source_revision_scope'],
                             'baseline-head-with-selected-working-raw-pins')
            self.assertFalse((Path(result['root']) / 'invented-inputs.zip').exists())

    def test_saved_file_pin_detects_modification(self):
        with tempfile.TemporaryDirectory() as parent:
            path = Path(parent) / 'input.json'
            path.write_bytes(b'one')
            pin = probe._pin(b'one')
            self.assertEqual(probe._read_pin(path, pin, 10), b'one')
            path.write_bytes(b'two')
            with self.assertRaisesRegex(ValueError, 'pin changed'):
                probe._read_pin(path, pin, 10)


if __name__ == '__main__':
    unittest.main()
