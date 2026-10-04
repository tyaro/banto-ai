"""Two-slot invented owner gates; no native process or observation read."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_controller as c
from banto_ai import anomaly_v03_preformal_campaign_metadata as m
from banto_ai import anomaly_v03_preformal_campaign_store as store
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied
from banto_ai import anomaly_v03_preformal_saved_row_reread as reread
from tests.test_anomaly_v03_preformal_campaign_metadata import Journal
from tests._anomaly_v03_preformal_campaign_test_paths import PortableCampaignPaths


def _manifest(journal, index):
    plan = journal.plan
    source = copy.deepcopy(plan['source'])
    source['selected_files'] = list(reversed([
        row for row in source['selected_files']
        if row['path'] in generated.SOURCE_FILES]))
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


class ControllerGateTests(PortableCampaignPaths):
    def test_shortened_owned_cli_wall_keeps_other_limits(self):
        self.assertEqual(c._effective_limits(), c.LIMITS)
        shortened = c._effective_limits(12.5)
        self.assertEqual(shortened,
                         {**c.LIMITS, 'wall_seconds': 12.5})
        self.assertEqual(c._effective_limits(901), c.LIMITS)
        self.assertTrue(c._valid_saved_limits(shortened))
        for bad in (0, -1, True, float('nan'), float('inf'), '12'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                c._effective_limits(bad)
        for changed in ({'wall_seconds': 0}, {'wall_seconds': 901},
                        {'private_bytes': c.LIMITS['private_bytes'] - 1},
                        {'output_bytes': True}):
            with self.subTest(changed=changed):
                self.assertFalse(c._valid_saved_limits({**shortened, **changed}))

    def setUp(self):
        root = (str(c.ROOT / 'artifacts' /
                    'anomaly-v03-preformal-campaign-aaaaaaaa')
                if os.name != 'nt' else None)
        self.j = Journal(root)
        original = self.j.plan
        source = copy.deepcopy(original['source'])
        source['selected_files'] = [
            {'path': name, 'pin': m.pin(name.encode('utf-8'))}
            for name in generated.SOURCE_FILES]
        source['selected_files'].append({
            'path': 'src/banto_ai/another_selected.py',
            'pin': m.pin(b'another selected source')})
        self.j.plan = m.fixed_plan(
            original['campaign_id'], original['root'], original['path_code'],
            original['registry_pin'], source, original['runtime_candidate'],
            original['budget_candidate'])
        self.j.plan_raw = m.encode_plan(self.j.plan)
        self.j.plan_pin = m.pin(self.j.plan_raw)

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
        self.assertEqual(request['argv'][-8:], [
            '--campaign-plan-path', str(Path(self.j.plan['root']) /
                                        'plan.json'),
            '--campaign-anchor-pin',
            f"{self.j.plan_pin['bytes']}:{self.j.plan_pin['sha256']}",
            '--campaign-chunk-index', '0', '--campaign-attempt', '1'])
        self.assertTrue(request['attempt_root'].endswith('-h001'))
        self.assertIsNone(request['generation_receipt_pin'])
        self.assertFalse(request['formal_permission'])
        self.assertEqual(request['campaign_evaluations_credited'], 0)
        self.assertEqual(c.encode_request(request)[-1:], b'\n')

    def test_selected_sources_include_new_child_context(self):
        name = 'src/banto_ai/anomaly_v03_preformal_campaign_child_context.py'
        self.assertIn(name, store.SOURCE_EXTRA)
        self.assertIn(name, generated.SOURCE_FILES)
        self.assertIn(name, copied.SOURCE_FILES)
        self.assertIn(name, reread.SOURCE_FILES)

    def test_outer_owner_rejects_modified_child_campaign_echo(self):
        context = {'plan_path': 'p', 'anchor_pin': m.pin(b'plan'),
                   'chunk_index': 0, 'attempt': 1}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            directory = root / 'owned-generator'
            (directory / 'worker').mkdir(parents=True)
            (directory / 'invocation.json').write_bytes(v.canonical_json({
                'format': generated.CAMPAIGN_INVOCATION,
                'invocation_id': 'a' * 64,
                'campaign_context': context}))
            reply = {'format': generated.CAMPAIGN_FORMAT,
                     'invocation_id': 'a' * 64,
                     'process': {'pid': 21, 'parent_pid': 20,
                                 'start_token': 'started'},
                     'campaign_context': {**context, 'chunk_index': 1}}
            stdout = v.canonical_json(reply)
            (directory / 'worker/report.json').write_bytes(stdout)
            (directory / 'supervision.json').write_bytes(v.canonical_json({
                'status': 'complete', 'exit_code': 0,
                'worker_exit_confirmed': True, 'worker_pid': 21,
                'output': m.pin(stdout)}))
            with patch.object(c.child_context, 'verify_context',
                              return_value=context):
                with self.assertRaises(ValueError):
                    c._inner_role(root, 'generator', 20, 21, 'started',
                                  context, 'attempt', 'a' * 40,
                                  generated.CAMPAIGN_INVOCATION,
                                  generated.CAMPAIGN_FORMAT)

    def test_outer_owner_rechecks_all_v2_child_formats_and_ids(self):
        context = {'plan_path': 'p', 'anchor_pin': m.pin(b'plan'),
                   'chunk_index': 0, 'attempt': 1}
        roles = (
            ('generator', generated.CAMPAIGN_INVOCATION,
             generated.CAMPAIGN_FORMAT),
            ('reader', copied.CAMPAIGN_READER_INVOCATION,
             copied.CAMPAIGN_READER_FORMAT),
            ('reader', reread.CAMPAIGN_INVOCATION_FORMAT,
             reread.CAMPAIGN_CHILD_FORMAT),
        )
        for role, invocation_format, reply_format in roles:
            for tamper in (None, 'invocation_format', 'reply_format',
                           'invocation_id'):
                with self.subTest(role=role, format=reply_format,
                                  tamper=tamper):
                    with tempfile.TemporaryDirectory() as folder:
                        root = Path(folder)
                        directory = root / ('owned-' + role)
                        (directory / 'worker').mkdir(parents=True)
                        invocation = {
                            'format': invocation_format,
                            'invocation_id': 'a' * 64,
                            'campaign_context': context,
                        }
                        reply = {
                            'format': reply_format,
                            'invocation_id': 'a' * 64,
                            'process': {'pid': 21, 'parent_pid': 20,
                                        'start_token': 'started'},
                            'campaign_context': context,
                        }
                        if tamper == 'invocation_format':
                            invocation['format'] = invocation_format[:-1] + '1'
                        elif tamper == 'reply_format':
                            reply['format'] = reply_format[:-1] + '1'
                        elif tamper == 'invocation_id':
                            reply['invocation_id'] = 'b' * 64
                        (directory / 'invocation.json').write_bytes(
                            v.canonical_json(invocation))
                        stdout = v.canonical_json(reply)
                        (directory / 'worker/report.json').write_bytes(stdout)
                        (directory / 'supervision.json').write_bytes(
                            v.canonical_json({
                                'status': 'complete', 'exit_code': 0,
                                'worker_exit_confirmed': True,
                                'worker_pid': 21, 'output': m.pin(stdout)}))
                        with patch.object(c.child_context, 'verify_context',
                                          return_value=context):
                            call = lambda: c._inner_role(
                                root, role, 20, 21, 'started', context,
                                'attempt', 'a' * 40,
                                invocation_format, reply_format)
                            if tamper is None:
                                self.assertEqual(call()[1], m.pin(stdout))
                            else:
                                with self.assertRaises(ValueError):
                                    call()

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
        for changed in ('missing', 'wrong_pin', 'extra', 'revision', 'scope'):
            value = v.strict_json(manifest)
            rows = value['source']['selected_files']
            if changed == 'missing':
                rows.pop()
            elif changed == 'wrong_pin':
                rows[0]['pin'] = m.pin(b'wrong source')
            elif changed == 'extra':
                rows.append(copy.deepcopy(
                    self.j.plan['source']['selected_files'][-1]))
            elif changed == 'revision':
                value['source']['revision'] = 'f' * 40
            else:
                value['source']['scope'] = 'other'
            bad = v.canonical_json(value)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                c._manifest(self.j.plan, v.strict_json(self.j.raws[-1]),
                            bad, m.pin(bad))

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
             patch.object(c.store, '_live_matches'), \
             patch.object(c, '_read', return_value=(
                 manifest_pin['sha256'] + '\n').encode('ascii')), \
             patch.object(c.copied, '_decode_source_snapshots',
                          return_value={plan['source']['revision']: {}}), \
             patch.object(c.generated, '_validated_snapshots'), \
             patch.object(c.generated, '_source',
                          return_value=v.strict_json(manifest)['source']) as source, \
             patch.object(c.runtime, 'probe_runtime',
                          return_value=plan['runtime_candidate']['tuple']), \
             patch.object(c, '_load_receipt', side_effect=prior_receipt), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'exists', return_value=False):
            c._verified_inputs(plan, request, current)
            changed = copy.deepcopy(v.strict_json(manifest)['source'])
            changed['selected_files'][0]['pin'] = m.pin(b'wrong live source')
            source.return_value = changed
            with self.assertRaises(ValueError):
                c._verified_inputs(plan, request, current)

    def test_execution_boundaries_check_full_plan_extra_and_subset(self):
        plan = self.j.plan
        manifest = v.strict_json(_manifest(self.j, 0))
        request = {'manifest_path': manifest['root'] + '-manifest',
                   'manifest_pin': m.pin(b'manifest')}
        with patch.object(c, '_pinned', return_value=b'manifest'), \
             patch.object(c.store, '_live_matches') as live, \
             patch.object(c.generated, '_source',
                          return_value=manifest['source']) as source, \
             patch.object(c.runtime, 'probe_runtime',
                          return_value=plan['runtime_candidate']['tuple']):
            c._verified_inputs_before_or_after(plan, request)
            live.assert_called_once_with(plan)
            changed = copy.deepcopy(manifest['source'])
            changed['selected_files'][0]['pin'] = m.pin(b'wrong source')
            source.return_value = changed
            with self.assertRaises(ValueError):
                c._verified_inputs_before_or_after(plan, request)
            live.side_effect = ValueError('plan extra source drift')
            with self.assertRaisesRegex(ValueError, 'plan extra source drift'):
                c._verified_inputs_before_or_after(plan, request)
        with patch.object(c.store, '_live_matches',
                          side_effect=ValueError('plan extra source drift')):
            with self.assertRaisesRegex(ValueError, 'plan extra source drift'):
                c._verified_inputs(plan, request, {'state': 'started'})


if __name__ == '__main__':
    unittest.main()
