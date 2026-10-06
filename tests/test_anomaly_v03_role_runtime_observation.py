"""External runtime pins reject drift; failure evidence never grants acceptance."""
import copy
from contextlib import ExitStack
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_role_runtime_observation as obs
from banto_ai import anomaly_v03_preformal_bound_draw_bridge as bridge


class RuntimeObservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.receipt = self.root / 'receipt'
        self.receipt.mkdir()
        self.sources = {}
        for name in ['src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py',
                     'src/banto_ai/anomaly_v03_role_runtime_observation.py']:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'value = 1\n')
            self.sources[name] = obs._pin(path.read_bytes())
        self.lib = self.root / 'Lib' / 'example.py'
        self.lib.parent.mkdir()
        self.lib.write_bytes(b'stdlib = 1\n')
        self.stdlib = {'stdlib/example.py': obs._pin(self.lib.read_bytes())}
        self.native = self.root / 'python.dll'
        self.native.write_bytes(b'invented-native')
        native_row = {**obs.dependencies.file_observation(self.native, native=True),
                      'native': True, 'category': 'native'}
        self.loaded = {'format': obs.dependencies.FORMAT, 'scope': dict(obs.dependencies.SCOPE),
            'files': {'python-files/python.dll': native_row}, 'native_files': ['python-files/python.dll'],
            'modules': {'example_builtin': {'kind': 'built-in', 'file': None, 'cache_candidate': None}}}
        self.profile = {'format': obs.FORMAT, 'mode': 'fixture', 'acceptance': 'candidate-not-accepted',
            'role': 'analysis', 'operation': obs.OPERATIONS['analysis'], 'source_root': str(self.root),
            'source_revision': 'a' * 40, 'runtime': dict(obs.runtime.EXPECTED),
            'source_files': self.sources, 'stdlib_files': self.stdlib,
            'native_files': {str(self.native): native_row['pin']}, 'cache_files': {}, 'scope': dict(obs.CLOSED)}
        self.process = {'pid': 123, 'creation_time_100ns': 456, 'start_token': 'a' * 64}
        self.input_pin = obs._pin(b'input')

    def observed(self, operation, *, stdlib=None, loaded=None):
        with ExitStack() as stack:
            stack.enter_context(patch.object(obs.runtime, 'probe_runtime', return_value=dict(obs.runtime.EXPECTED)))
            stack.enter_context(patch.object(obs, '_stdlib', return_value=self.stdlib if stdlib is None else stdlib))
            stack.enter_context(patch.object(obs.inventory, 'stdlib_paths', return_value=[('stdlib/example.py', self.lib)]))
            stack.enter_context(patch.object(obs.dependencies, 'collect', return_value=self.loaded if loaded is None else loaded))
            stack.enter_context(patch.object(obs.process_evidence, 'creation_observation', return_value=self.process))
            raw = obs.v.canonical_json(self.profile)
            return obs.run_observed(operation, root=self.receipt, source_root=self.root, role='analysis',
                profile_raw=raw, profile_pin=obs._pin(raw), input_pin=self.input_pin)

    def test_external_pin_wrong_role_revision_root_and_scope_are_rejected(self):
        for field, value in [('role', 'audit'), ('source_revision', 'a' * 39),
                             ('source_root', str(self.receipt)), ('scope', {**obs.CLOSED, 'formal_permission': 0})]:
            profile = copy.deepcopy(self.profile)
            profile[field] = value
            raw = obs.v.canonical_json(profile)
            with self.subTest(field=field), self.assertRaises(ValueError):
                obs.load_profile(raw, obs._pin(raw), root=self.root, role='analysis')
        raw = obs.v.canonical_json(self.profile)
        with self.assertRaisesRegex(ValueError, 'external pin'):
            obs.load_profile(raw + b' ', obs._pin(raw), root=self.root, role='analysis')

    def test_success_receipts_bind_input_process_and_full_disk_pin_summaries(self):
        result, receipt = self.observed(lambda: {'value': 123})
        self.assertEqual(result, {'value': 123})
        self.assertEqual(receipt['process'], self.process)
        for phase in ('before', 'after'):
            path = self.receipt / ('analysis-runtime-' + phase + '.json')
            self.assertEqual(obs._pin(path.read_bytes()), receipt[phase + '_pin'])
            saved = json.loads(path.read_bytes())
            self.assertEqual(saved['input_pin'], self.input_pin)
            self.assertEqual(saved['source_inventory_pin'], obs._pin(obs.v.canonical_json(self.sources)))
            self.assertEqual(saved['stdlib_files'], 1)
            for name in obs.CLOSED:
                self.assertIs(saved[name], False)

    def test_changed_source_rejects_before_work_and_preserves_failure(self):
        (self.root / next(iter(self.sources))).write_bytes(b'value = 2\n')
        with self.assertRaisesRegex(ValueError, 'source bytes differ'):
            self.observed(lambda: self.fail('operation started'))
        self.assertTrue((self.receipt / 'analysis-runtime-failure.json').is_file())
        self.assertFalse((self.receipt / 'analysis-runtime-before.json').exists())

    def test_stdlib_drift_and_unregistered_loaded_dll_reject_before_work(self):
        with self.assertRaisesRegex(ValueError, 'stdlib pins differ'):
            self.observed(lambda: self.fail('operation started'), stdlib={})
        (self.receipt / 'analysis-runtime-failure.json').unlink()
        loaded = copy.deepcopy(self.loaded)
        loaded['files']['python-files/python.dll']['physical_path'] = str(self.root / 'unknown.dll')
        with self.assertRaisesRegex(ValueError, 'unexpected/changed loaded'):
            self.observed(lambda: self.fail('operation started'), loaded=loaded)

    def test_operation_failure_keeps_before_and_failure_without_after(self):
        def operation():
            raise ValueError('calculation failed')
        with self.assertRaisesRegex(ValueError, 'calculation failed'):
            self.observed(operation)
        self.assertTrue((self.receipt / 'analysis-runtime-before.json').is_file())
        self.assertTrue((self.receipt / 'analysis-runtime-failure.json').is_file())
        self.assertFalse((self.receipt / 'analysis-runtime-after.json').exists())

    def test_after_source_drift_rejects_even_after_operation_returns(self):
        def operation():
            (self.root / next(iter(self.sources))).write_bytes(b'value = 2\n')
            return {'value': 1}
        with self.assertRaisesRegex(ValueError, 'source bytes differ'):
            self.observed(operation)
        self.assertFalse((self.receipt / 'analysis-runtime-after.json').exists())

    def test_existing_failure_file_does_not_mask_original_operation_error(self):
        (self.receipt / 'analysis-runtime-failure.json').write_bytes(b'previous')
        def operation():
            raise RuntimeError('original failure')
        with self.assertRaisesRegex(RuntimeError, 'original failure'):
            self.observed(operation)
        self.assertEqual((self.receipt / 'analysis-runtime-failure.json').read_bytes(), b'previous')

    def test_saved_metadata_forgery_rejects_before_dependency_crosscheck(self):
        _, receipt = self.observed(lambda: {})
        before = json.loads((self.receipt / 'analysis-runtime-before.json').read_bytes())
        after = json.loads((self.receipt / 'analysis-runtime-after.json').read_bytes())
        after['stdlib_bytes'] += 1
        with patch.object(obs, '_stdlib', return_value=self.stdlib), \
             patch.object(obs.inventory, 'stdlib_paths', return_value=[('stdlib/example.py', self.lib)]), \
             patch.object(obs.dependencies, 'verify_pair', side_effect=AssertionError('accepted')), \
             self.assertRaisesRegex(ValueError, 'binding differs'):
            obs.crosscheck_saved(self.profile, before, after, root=self.root, input_pin=self.input_pin,
                process=self.process, profile_pin=receipt['profile_pin'])

    def test_actual_child_only_observer_runs_the_existing_operation(self):
        def observed(operation, **kwargs):
            self.assertEqual(kwargs['role'], 'analysis')
            self.assertEqual(kwargs['profile_pin'], self.input_pin)
            return operation(), {'invented-observer-test': True}
        with patch.object(bridge, '_read', return_value=b'{}'), \
             patch.object(bridge, '_check_input'), \
             patch.object(bridge, '_calculate', return_value={'status': 'complete'}) as calculate, \
             patch.object(obs, 'run_observed', side_effect=observed), patch('sys.stdout', new_callable=io.StringIO):
            bridge._child('analysis', self.receipt, self.input_pin, inventory_profile_pin=self.input_pin)
        self.assertEqual(calculate.call_count, 1)
        self.assertEqual(calculate.call_args.args[0], 'analysis')

    def test_parent_rejects_a_rehashed_report_with_another_owned_process(self):
        output_pin = obs._pin(b'calculation')
        report = {'format': bridge.FORMAT + '-role', 'role': 'analysis', 'status': 'complete',
            'replicates': bridge.REPLICATES, 'draw_sha256': bridge.frozen.BOOTSTRAP_HASH,
            'output_pin': output_pin, 'registered_data_read': False,
            'formal_bootstrap_performed': False, 'formal_permission': False, 'independent_s6_complete': False}
        report, receipt = self.observed(lambda: report)
        report['runtime_observation'] = receipt
        raw = obs.v.canonical_json(report)
        (self.receipt / 'analysis-stdout.json').write_bytes(raw)
        profile_raw = obs.v.canonical_json(self.profile)
        (self.receipt / 'analysis-inventory-profile.json').write_bytes(profile_raw)
        (self.receipt / 'input.json').write_bytes(b'input')
        supervision = {'status': 'complete', 'worker_exit_confirmed': True,
            'pid': 124, 'process_identity': {**self.process, 'pid': 124}, 'stdout_pin': obs._pin(raw)}
        with patch.object(bridge, 'ROOT', self.root), \
             patch.object(obs, 'crosscheck_saved', side_effect=AssertionError('accepted')), \
             self.assertRaisesRegex(ValueError, 'owned PID differs'):
            bridge._verify_role(self.receipt, 'analysis', supervision, output_pin,
                                inventory_profile_pin=obs._pin(profile_raw))

    def test_parent_rejects_changed_native_pins_in_saved_snapshot(self):
        _, receipt = self.observed(lambda: {})
        before = json.loads((self.receipt / 'analysis-runtime-before.json').read_bytes())
        after = json.loads((self.receipt / 'analysis-runtime-after.json').read_bytes())
        after['loaded']['files']['python-files/python.dll']['pin']['sha256'] = '0' * 64
        with patch.object(obs, '_stdlib', return_value=self.stdlib), \
             patch.object(obs.inventory, 'stdlib_paths', return_value=[('stdlib/example.py', self.lib)]), \
             patch.object(obs.dependencies, 'verify_pair', side_effect=AssertionError('accepted')), \
             self.assertRaisesRegex(ValueError, 'unexpected/changed loaded'):
            obs.crosscheck_saved(self.profile, before, after, root=self.root, input_pin=self.input_pin,
                                process=self.process, profile_pin=receipt['profile_pin'])

    def test_child_option_is_not_silently_applied_to_a_measurement(self):
        with self.assertRaisesRegex(ValueError, 'actual child option'):
            bridge.main(['--measure', 'attempt', 'producer', '1', 'a' * 64,
                         '--inventory-profile', '1', 'a' * 64])


if __name__ == '__main__':
    unittest.main()
