"""Two-slot invented owner gates; no native process or observation read."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_controller as c
from banto_ai import anomaly_v03_preformal_campaign_metadata as m
from tests.test_anomaly_v03_preformal_campaign_metadata import Journal


def _manifest(journal, index):
    plan = journal.plan
    source = copy.deepcopy(plan['source'])
    source['selected_files'].reverse()  # Existing prepare retains collection order.
    output = {name: m.pin(name.encode('ascii'))
              for name in m._output_names(index)}
    output['saved/registry.json'] = plan['registry_pin']
    return v.canonical_json({
        'format': 'anomaly-v03-preformal-owned-generated-external-pins-v1',
        'scope': 'invented-registered-format-owned-generator-only',
        'root': m.attempt_root(plan, index, 1),
        'revision': plan['source']['revision'], 'chunk_index': index,
        'recipe_id': m.RECIPE, 'source': source,
        'source_snapshots': {}, 'source_snapshot_pins': {},
        'output_pins': output, 'output_file_count': 22,
        'output_bytes': sum(item['bytes'] for item in output.values()),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    })


class ControllerGateTests(unittest.TestCase):
    def setUp(self):
        self.j = Journal()

    def _start(self, index=0):
        manifest = _manifest(self.j, index)
        raw = c.next_started_record(
            self.j.plan_raw, self.j.plan_pin, self.j.raws,
            expected_record_count=len(self.j.raws),
            expected_head_sha256=self.j.head,
            manifest_pin=m.pin(manifest))
        self.j.raws.append(raw)
        return manifest

    def test_slot_zero_fixed_command_and_closed_flags(self):
        manifest = self._start()
        request = c.fixed_request(
            self.j.plan_raw, self.j.plan_pin, self.j.raws,
            expected_record_count=1, expected_head_sha256=self.j.head,
            manifest_raw=manifest, manifest_pin=m.pin(manifest),
            phase='run-budget', python_executable=sys.executable)
        self.assertEqual(request['chunk_index'], 0)
        self.assertEqual(request['attempt'], 1)
        self.assertEqual(request['manifest_pin'], m.pin(manifest))
        self.assertEqual(request['argv'][3], 'run-budget')
        self.assertTrue(request['attempt_root'].endswith('-h001'))
        self.assertIsNone(request['generation_receipt_pin'])
        self.assertFalse(request['formal_permission'])
        self.assertEqual(request['campaign_evaluations_credited'], 0)
        self.assertEqual(c.encode_request(request)[-1:], b'\n')

    def test_second_slot_requires_prior_owned_receipts(self):
        self.j.complete(0)
        manifest = _manifest(self.j, 1)
        with self.assertRaises(ValueError):
            c.next_started_record(
                self.j.plan_raw, self.j.plan_pin, self.j.raws,
                expected_record_count=2, expected_head_sha256=self.j.head,
                manifest_pin=m.pin(manifest))
        with patch.object(c, 'completion_record',
                          return_value=self.j.raws[-1]) as complete:
            raw = c.next_started_record(
                self.j.plan_raw, self.j.plan_pin, self.j.raws,
                expected_record_count=2, expected_head_sha256=self.j.head,
                manifest_pin=m.pin(manifest),
                prior_generation_receipt_pin=m.pin(b'run receipt'),
                prior_reread_receipt_pin=m.pin(b'reread receipt'))
        self.assertEqual(complete.call_count, 1)
        self.assertEqual(v.strict_json(raw)['chunk_index'], 1)
        self.assertTrue(v.strict_json(raw)['attempt_root'].endswith('-h011'))
        with patch.object(c, 'completion_record',
                          return_value=b'changed completed declaration\n'):
            with self.assertRaises(ValueError):
                c.next_started_record(
                    self.j.plan_raw, self.j.plan_pin, self.j.raws,
                    expected_record_count=2,
                    expected_head_sha256=self.j.head,
                    manifest_pin=m.pin(manifest),
                    prior_generation_receipt_pin=m.pin(b'run receipt'),
                    prior_reread_receipt_pin=m.pin(b'reread receipt'))

    def test_failed_or_in_flight_slot_never_auto_resumes(self):
        manifest = self._start()
        for raws in (list(self.j.raws),
                     [*self.j.raws,
                      m.encode_record(m.make_record(
                          self.j.plan_pin, self.j.head, 2, 0, 1, 'failed',
                          m.attempt_root(self.j.plan, 0, 1),
                          m.pin(manifest),
                          source_revision=self.j.plan['source']['revision'],
                          runtime_tuple_sha256=self.j.plan[
                              'runtime_candidate']['tuple_sha256'],
                          reason='worker_exit'))]):
            with self.assertRaises(ValueError):
                c.next_started_record(
                    self.j.plan_raw, self.j.plan_pin, raws,
                    expected_record_count=len(raws),
                    expected_head_sha256=m.pin(raws[-1])['sha256'],
                    manifest_pin=m.pin(manifest))

    def test_manifest_slot_source_and_registry_binding(self):
        manifest = self._start()
        for key, changed in (
            ('chunk_index', 1), ('root', 'D:\\unrelated'),
            ('revision', 'f' * 40), ('formal_permission', True),
        ):
            value = v.strict_json(manifest)
            value[key] = changed
            bad = v.canonical_json(value)
            with self.assertRaises(ValueError):
                c.fixed_request(
                    self.j.plan_raw, self.j.plan_pin, self.j.raws,
                    expected_record_count=1,
                    expected_head_sha256=self.j.head,
                    manifest_raw=bad, manifest_pin=m.pin(bad),
                    phase='run-budget', python_executable=sys.executable)
        value = v.strict_json(manifest)
        value['output_pins']['saved/registry.json'] = m.pin(b'wrong')
        bad = v.canonical_json(value)
        with self.assertRaises(ValueError):
            c._manifest(self.j.plan, v.strict_json(self.j.raws[-1]), bad,
                        m.pin(bad))

    def test_reread_requires_preceding_owned_result_and_current_python(self):
        manifest = self._start()
        with self.assertRaises(ValueError):
            c.fixed_request(
                self.j.plan_raw, self.j.plan_pin, self.j.raws,
                expected_record_count=1, expected_head_sha256=self.j.head,
                manifest_raw=manifest, manifest_pin=m.pin(manifest),
                phase='saved-reread', python_executable=sys.executable,
                outer_result_pin=m.pin(b'outer'))
        with patch.object(c, '_load_receipt', return_value={
                'inner': {'outer_result_pin': m.pin(b'outer')}}):
            request = c.fixed_request(
                self.j.plan_raw, self.j.plan_pin, self.j.raws,
                expected_record_count=1, expected_head_sha256=self.j.head,
                manifest_raw=manifest, manifest_pin=m.pin(manifest),
                phase='saved-reread', python_executable=sys.executable,
                outer_result_pin=m.pin(b'outer'),
                generation_receipt_pin=m.pin(b'owned receipt'))
            self.assertEqual(request['argv'][3], '--source-root')
            self.assertEqual(request['generation_receipt_pin'],
                             m.pin(b'owned receipt'))
            with self.assertRaises(ValueError):
                c.fixed_request(
                    self.j.plan_raw, self.j.plan_pin, self.j.raws,
                    expected_record_count=1,
                    expected_head_sha256=self.j.head,
                    manifest_raw=manifest, manifest_pin=m.pin(manifest),
                    phase='saved-reread', python_executable=sys.executable,
                    outer_result_pin=m.pin(b'old copied result'),
                    generation_receipt_pin=m.pin(b'owned receipt'))
        with self.assertRaises(ValueError):
            c.fixed_request(
                self.j.plan_raw, self.j.plan_pin, self.j.raws,
                expected_record_count=1, expected_head_sha256=self.j.head,
                manifest_raw=manifest, manifest_pin=m.pin(manifest),
                phase='run-budget', python_executable='different-python.exe')

    def test_failed_receipt_is_pinned_and_never_allows_next_slot(self):
        manifest = self._start()
        request_pin = m.pin(b'fixed request')
        request = {
            'phase': 'run-budget', 'journal_count': 1,
            'journal_head_sha256': self.j.head,
            'chunk_index': 0, 'attempt_root': m.attempt_root(
                self.j.plan, 0, 1), 'manifest_pin': m.pin(manifest),
        }
        with tempfile.TemporaryDirectory() as folder:
            control = Path(folder) / 'control'
            value, receipt_pin = c._failed_receipt(
                control, request, request_pin, self.j.plan_pin, None, {},
                'integrity', 'ValueError')
            self.assertEqual(value['status'], 'failed')
            self.assertFalse(value['retry_authorized'])
            self.assertFalse(value['descendant_exit_confirmed'])
            self.assertEqual(receipt_pin,
                             m.pin((control / 'receipt.json').read_bytes()))
            with patch.object(c, '_control', return_value=control):
                failed = c.failed_record(
                    self.j.plan_raw, self.j.plan_pin, self.j.raws,
                    expected_record_count=1,
                    expected_head_sha256=self.j.head,
                    failed_receipt_pin=receipt_pin, phase='run-budget')
            self.j.raws.append(failed)
            self.assertEqual(v.strict_json(failed)['state'], 'failed')
            with self.assertRaises(ValueError):
                c.next_started_record(
                    self.j.plan_raw, self.j.plan_pin, self.j.raws,
                    expected_record_count=2,
                    expected_head_sha256=self.j.head,
                    manifest_pin=m.pin(manifest))

    def test_reread_preflight_keeps_full_started_record_for_prior_receipt(self):
        manifest = self._start()
        current = v.strict_json(self.j.raws[-1])
        plan = self.j.plan
        manifest_pin = m.pin(manifest)
        attempt, manifest_path, reread_root = c._paths(plan, current)
        receipt_pin = m.pin(b'prior generation receipt')
        request = {
            'phase': 'saved-reread', 'attempt_root': str(attempt),
            'manifest_path': str(manifest_path), 'manifest_pin': manifest_pin,
            'chunk_index': 0, 'reread_root': str(reread_root),
            'generation_receipt_pin': receipt_pin,
            'outer_result_pin': m.pin(b'prior owned result'),
        }

        def pinned(path, expected, maximum=c.MAX_SAVED):
            return manifest if Path(path) == manifest_path else b'prior owned result'

        def prior_receipt(value_plan, value_current, phase, pin):
            self.assertEqual(value_plan, plan)
            self.assertEqual(value_current, current)
            self.assertEqual(value_current['state'], 'started')
            self.assertEqual(value_current['sequence'], 1)
            self.assertEqual(phase, 'run-budget')
            self.assertEqual(pin, receipt_pin)
            return {'status': 'verified'}

        with patch.object(c, '_pinned', side_effect=pinned), \
             patch.object(c, '_read', return_value=(
                 manifest_pin['sha256'] + '\n').encode('ascii')), \
             patch.object(c.copied, '_decode_source_snapshots',
                          return_value={plan['source']['revision']: {}}), \
             patch.object(c.generated, '_validated_snapshots'), \
             patch.object(c.generated, '_source',
                          return_value=plan['source']), \
             patch.object(c.runtime, 'probe_runtime',
                          return_value=plan['runtime_candidate']['tuple']), \
             patch.object(c, '_load_receipt', side_effect=prior_receipt), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'exists', return_value=False):
            c._verified_inputs(plan, request, current)


if __name__ == '__main__':
    unittest.main()
