"""Saved physical reads keep caller pins, original handle identity and failures."""
import copy
from contextlib import ExitStack, nullcontext, redirect_stdout
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_role_runtime_observation as obs
from banto_ai import anomaly_v03_preformal_saved_row_reread as reread
from tests import test_anomaly_v03_preformal_saved_row_reread as saved_inputs


class SavedReaderRuntimeTests(unittest.TestCase):
    def setUp(self):
        saved_inputs.SavedRowRereadTests.setUp(self)
        saved_inputs.FakeBudget.stop_on = None
        self.repo = self.source.parent / 'checkout'
        self.repo.mkdir()
        self.sources = {}
        for name in reread.SOURCE_FILES:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'value = 1\n')
            self.sources[name] = obs._pin(path.read_bytes())
        self.lib = self.repo / 'Lib/example.py'
        self.lib.parent.mkdir()
        self.lib.write_bytes(b'library = 1\n')
        self.stdlib = {'stdlib/example.py': obs._pin(self.lib.read_bytes())}
        self.native = self.repo / 'python.dll'
        self.native.write_bytes(b'invented-native')
        row = {**obs.dependencies.file_observation(self.native, native=True),
               'native': True, 'category': 'native'}
        self.loaded = {'format': obs.dependencies.FORMAT, 'scope': dict(obs.dependencies.SCOPE),
            'files': {'python-files/python.dll': row}, 'native_files': ['python-files/python.dll'],
            'modules': {'example_builtin': {'kind': 'built-in', 'file': None, 'cache_candidate': None}}}
        self.profile = {'format': obs.SAVED_READER_FORMAT, 'mode': 'fixture',
            'acceptance': 'candidate-not-accepted', 'role': 'saved-reader',
            'operation': obs.OPERATIONS['saved-reader'], 'source_root': str(self.repo),
            'source_revision': 'b' * 40, 'runtime': dict(obs.runtime.EXPECTED),
            'source_files': self.sources, 'stdlib_files': self.stdlib,
            'native_files': {str(self.native): row['pin']}, 'cache_files': {}, 'scope': dict(obs.CLOSED)}
        raw = obs.v.canonical_json(self.profile)
        self.entry = {'raw': raw, 'expected_pin': obs._pin(raw)}
        self.process = {'pid': 42, 'creation_time_100ns': 456, 'start_token': 'f' * 64}
        self.current_source = {'revision': 'b' * 40, 'selected_files': [
            {'path': name, 'pin': pin} for name, pin in self.sources.items()], 'scope': 'test-selected-source'}
        self.current_runtime = dict(obs.runtime.EXPECTED)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(reread, 'ROOT', self.repo))
        stack.enter_context(patch.object(reread, '_roots', return_value=(self.source, self.target, self.manifest_path)))
        stack.enter_context(patch.object(reread, '_roots_for_child', return_value=(self.source, self.target, self.manifest_path)))
        stack.enter_context(patch.object(reread.generated, '_outputs', return_value={key: key for key in self.output_pins}))
        stack.enter_context(patch.object(reread, '_source', return_value=self.current_source))
        stack.enter_context(patch.object(obs.runtime, 'probe_runtime', return_value=self.current_runtime))
        stack.enter_context(patch.object(obs, '_stdlib', return_value=self.stdlib))
        stack.enter_context(patch.object(obs.inventory, 'stdlib_paths', return_value=[('stdlib/example.py', self.lib)]))
        stack.enter_context(patch.object(obs.dependencies, 'collect', return_value=self.loaded))
        stack.enter_context(patch.object(obs.dependencies, 'verify_pair', return_value={'status': 'invented-check'}))
        self.identity = stack.enter_context(patch.object(obs.process_evidence, 'creation_observation', return_value=self.process))
        stack.enter_context(patch.object(reread.budget_module, 'FixtureBudget', saved_inputs.FakeBudget))
        stack.enter_context(patch.object(reread.platform, '_platform_scope', return_value=nullcontext()))
        self.recheck = stack.enter_context(patch.object(reread, '_recheck_saved_outputs',
            return_value={'saved_files': 22, 'disk_pin_recheck_completed': True}))
        self.operation = stack.enter_context(patch.object(reread, '_read_attempt', side_effect=self._reply))

    def _reply(self, request, source, target, manifest):
        return {'format': reread.CAMPAIGN_CHILD_FORMAT if 'campaign_context' in request else reread.CHILD_FORMAT,
            'status': 'read', 'invocation_id': request['invocation_id'],
            'process': {'pid': 42, 'parent_pid': os.getpid(), 'start_token': self.process['start_token']},
            'source': self.current_source, 'runtime': self.current_runtime, 'manifest_pin': self.manifest_pin,
            'output_pins': self.output_pins, 'reader_result': copy.deepcopy(self.old_reader),
            'actual_registered_observations_read': False, 'formal_permission': False,
            **({'campaign_context': request['campaign_context']} if 'campaign_context' in request else {})}

    def _worker(self, request):
        root = self.target / 'owned-reader'
        root.mkdir(parents=True, exist_ok=True)
        (root / 'inventory-profile.json').write_bytes(self.entry['raw'])
        raw = obs.v.canonical_json(request)
        path = root / 'invocation.json'
        path.write_bytes(raw)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = reread.reader_worker_main([str(path), obs._pin(raw)['sha256']])
        return code, json.loads(stream.getvalue()), root, obs._pin(raw)

    def _request(self):
        return {'format': reread.INVOCATION_FORMAT, 'source_root': str(self.source),
            'output_root': str(self.target), 'manifest_path': str(self.manifest_path),
            'manifest_pin': self.manifest_pin, 'external_pins': self.output_pins,
            'source_snapshots': self.manifest['source_snapshots'], 'chunk_index': 0,
            'current_revision': 'b' * 40, 'current_source': self.current_source,
            'runtime': self.current_runtime, 'invocation_id': 'invented-invocation',
            'runtime_inventory_profile_pin': self.entry['expected_pin']}

    def _parent(self, *, active=True, tamper=None):
        handle = object()

        def supervise(argv, cwd, output, limits, *, boundary, on_started, resource_probe):
            self.assertIsNone(resource_probe())
            self.assertEqual(limits, reread.copied.READER_LIMITS)
            boundary()
            on_started(SimpleNamespace(pid=42, _handle=handle))
            output.mkdir()
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = reread.reader_worker_main(argv[-2:])
            reply = json.loads(stream.getvalue())
            if tamper == 'handle':
                reply['runtime_observation']['process']['creation_time_100ns'] += 1
            if tamper == 'unexpected':
                reply['runtime_observation'] = {}
            if tamper == 'phase':
                (self.target / 'owned-reader/saved-reader-runtime-after.json').write_bytes(b'changed')
            raw = obs.v.canonical_json(reply)
            (output / 'report.json').write_bytes(raw)
            return {'status': 'complete', 'exit_code': code, 'worker_pid': 42,
                    'worker_exit_confirmed': True, 'worker_started': True, 'output': obs._pin(raw)}

        with patch.object(reread.supervisor, 'supervise', side_effect=supervise):
            result = reread.run_reread(self.source, self.target, expected_manifest_pin=self.manifest_pin,
                expected_outer_result_pin=self.outer_pin, expected_revision='b' * 40,
                saved_reader_runtime_profile=self.entry if active else None)
        self.identity.assert_any_call(42, handle)
        return result

    def test_worker_wraps_exactly_one_read_with_whole_invocation_pin(self):
        code, reply, root, input_pin = self._worker(self._request())
        self.assertEqual(code, 0)
        self.operation.assert_called_once()
        receipt = reply['runtime_observation']
        self.assertEqual(receipt['format'], obs.SAVED_READER_RECEIPT)
        self.assertEqual(receipt['input_pin'], input_pin)
        self.assertEqual(receipt['process'], self.process)
        for phase in ('before', 'after'):
            value = json.loads((root / ('saved-reader-runtime-' + phase + '.json')).read_bytes())
            self.assertEqual(value['role'], 'saved-reader')
            self.assertEqual(value['source_revision'], 'b' * 40)
        for key in obs.CLOSED:
            self.assertIs(receipt[key], False)

    def test_worker_failure_keeps_before_and_failure_without_after(self):
        self.operation.side_effect = ValueError('physical read stopped')
        code, reply, root, _ = self._worker(self._request())
        self.assertEqual(code, 2)
        self.assertEqual(reply['status'], 'failed')
        self.assertTrue((root / 'saved-reader-runtime-before.json').is_file())
        self.assertTrue((root / 'saved-reader-runtime-failure.json').is_file())
        self.assertFalse((root / 'saved-reader-runtime-after.json').exists())

    def test_worker_revision_is_current_code_not_historical_payload(self):
        code, reply, _, _ = self._worker({**self._request(), 'current_revision': 'a' * 40})
        self.assertEqual(code, 2)
        self.assertIn('worker revision', reply['detail'])
        self.operation.assert_not_called()

    def test_arithmetic_format_cannot_substitute_for_saved_reader(self):
        value = {**self.profile, 'format': obs.FORMAT}
        with self.assertRaisesRegex(ValueError, 'role/root/scope'):
            obs.validate_profile(value, root=self.repo, role='saved-reader')

    def test_invalid_external_pin_rejects_before_output_root_or_child(self):
        with patch.object(reread.supervisor, 'supervise') as child, self.assertRaisesRegex(ValueError, 'external pin'):
            reread.run_reread(self.source, self.target, expected_manifest_pin=self.manifest_pin,
                expected_outer_result_pin=self.outer_pin, expected_revision='b' * 40,
                saved_reader_runtime_profile={**self.entry, 'raw': self.entry['raw'] + b' '})
        child.assert_not_called()
        self.assertFalse(self.target.exists())

    def test_selected_git_pin_mismatch_stops_before_child_launch(self):
        self.current_source['selected_files'][0]['pin'] = obs._pin(b'other-current-source')
        with patch.object(reread.supervisor, 'supervise') as child:
            result = reread.run_reread(self.source, self.target, expected_manifest_pin=self.manifest_pin,
                expected_outer_result_pin=self.outer_pin, expected_revision='b' * 40,
                saved_reader_runtime_profile=self.entry)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('selected Git source', result['detail'])
        child.assert_not_called()

    def test_parent_binds_original_handle_and_rechecks_profile_phases_after_rows(self):
        result = self._parent()
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['historic_source_revision'], 'a' * 40)
        self.assertEqual(result['current_revision'], 'b' * 40)
        self.assertIs(result['saved_reader_runtime_observation_checked'], True)
        self.assertEqual(result['child_process'], self.process)
        self.assertEqual(result['saved_reader_runtime_profile_pin'], self.entry['expected_pin'])
        self.assertTrue(result['saved_rows_final_disk_recheck_completed'])
        reread.recheck_runtime_profile(self.target, result)
        self.assertLessEqual((self.target / 'result.json').stat().st_size, reread.MAX_RESULT)
        self.assertFalse(result['formal_permission'])

    def test_reply_cannot_substitute_another_creation_time(self):
        result = self._parent(tamper='handle')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('external binding', result['detail'])
        self.assertFalse((self.target / 'rows.json').exists())

    def test_phase_changed_after_exit_rejects_before_projection(self):
        result = self._parent(tamper='phase')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('phase pin', result['detail'])
        self.assertFalse((self.target / 'rows.json').exists())

    def test_phase_changed_during_projection_rejects_final_success(self):
        def mutate(*args):
            (self.target / 'owned-reader/saved-reader-runtime-after.json').write_bytes(b'changed')
            return {'saved_files': 22}
        self.recheck.side_effect = mutate
        result = self._parent()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('pin', result['detail'])
        self.assertTrue((self.target / 'rows.json').exists())

    def test_unrequested_runtime_receipt_cannot_upgrade_legacy_read(self):
        result = self._parent(active=False, tamper='unexpected')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('unexpected', result['detail'])


if __name__ == '__main__':
    unittest.main()
