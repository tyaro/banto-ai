"""Real generation/initial-reader entry wrappers bind caller pins and handles."""
import copy
from contextlib import ExitStack, nullcontext, redirect_stdout
import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_role_runtime_observation as obs
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from tests import test_anomaly_v03_role_runtime_observation as helpers
from tests import test_anomaly_v03_preformal_owned_generated_attempt_negative as negatives


class GenerationRuntimeTests(unittest.TestCase):
    def setUp(self):
        registry = (generated.ROOT / 'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()
        helpers.RuntimeObservationTests.setUp(self)
        self.attempt = self.root / 'artifacts' / (generated.fixture.PREFIX + 'g1')
        self.attempt.mkdir(parents=True)
        for name in generated.SOURCE_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'value = 1\n')
            self.sources[name] = obs._pin(path.read_bytes())
        logical = [*generated.copied.SAVED, *generated.fixture._names(0, 1)[1]]
        self.names = {name: name if name in generated.copied.SAVED else 'run-root/file-' + str(i)
                      for i, name in enumerate(logical)}
        self.content = {name: b'{}' for name in self.names}
        self.content['saved/registry.json'] = registry
        self.pins = {name: obs._pin(raw) for name, raw in self.content.items()}
        self.source = {'revision': 'a' * 40, 'selected_files': [
            {'path': name, 'pin': value} for name, value in self.sources.items()], 'scope': 'invented-check'}
        self.profiles = {}
        for role in ('producer', 'initial-reader'):
            value = {**self.profile, 'format': obs.GENERATION_FORMAT, 'role': role, 'operation': obs.OPERATIONS[role]}
            raw = obs.v.canonical_json(value)
            self.profiles[role] = {'raw': raw, 'expected_pin': obs._pin(raw)}
        self.processes = {role: {'pid': pid, 'creation_time_100ns': pid * 1000,
            'start_token': obs.v.canonical_sha256({'pid': pid, 'creation_time_100ns': pid * 1000})}
            for role, pid in (('producer', 401), ('initial-reader', 402))}
        self.role = 'producer'
        self.handles = {role: object() for role in self.processes}
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(generated, 'ROOT', self.root))
        stack.enter_context(patch.object(generated.copied, 'ROOT', self.root))
        stack.enter_context(patch.object(generated, '_outputs', return_value=self.names))
        stack.enter_context(patch.object(generated, '_source', return_value=self.source))
        stack.enter_context(patch.object(generated.copied, '_source', return_value=self.source))
        stack.enter_context(patch.object(generated, '_validated_snapshots'))
        stack.enter_context(patch.object(generated.copied, '_saved_outputs', return_value=(self.names, 1)))
        stack.enter_context(patch.object(generated.platform, '_platform_scope', return_value=nullcontext()))
        stack.enter_context(patch.object(obs.runtime, 'probe_runtime', return_value=dict(obs.runtime.EXPECTED)))
        stack.enter_context(patch.object(obs, '_stdlib', return_value=self.stdlib))
        stack.enter_context(patch.object(obs.inventory, 'stdlib_paths', return_value=[('stdlib/example.py', self.lib)]))
        stack.enter_context(patch.object(obs.dependencies, 'collect', return_value=self.loaded))
        stack.enter_context(patch.object(obs.dependencies, 'verify_pair', return_value={'status': 'invented-check'}))
        self.identity = stack.enter_context(patch.object(obs.process_evidence, 'creation_observation',
            side_effect=lambda *args: copy.deepcopy(self.processes[self.role])))
        self.produce = stack.enter_context(patch.object(generated, '_generate_attempt', side_effect=self._produce))
        self.read = stack.enter_context(patch.object(generated.copied, '_read_attempt', side_effect=self._read))

    def _base(self, request):
        process = self.processes[self.role]
        return {'invocation_id': request['invocation_id'],
            'process': {'pid': process['pid'], 'parent_pid': os.getpid(), 'start_token': process['start_token']},
            'output_pins': self.pins, 'source_before': self.source, 'source_after': self.source,
            'runtime_before': dict(obs.runtime.EXPECTED), 'runtime_after': dict(obs.runtime.EXPECTED),
            'formal_permission': False}

    def _produce(self, request, root):
        for name, relative in self.names.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.content[name])
        return {**self._base(request), 'format': generated.FORMAT, 'status': 'generated',
            'recipe_id': generated.RECIPE, 'output_file_count': 22,
            'output_bytes': sum(value['bytes'] for value in self.pins.values()),
            'invented_generation_executed': True, 'registered_seed_consumed': False,
            'actual_registered_observations_read': False}

    def _read(self, request, root):
        return {**self._base(request), 'format': generated.copied.READER_FORMAT, 'status': 'read',
                'reader_result': negatives.OwnedGeneratedAttemptNegativeTests.reader_result(self.pins)}

    def _request(self, role):
        return {'format': generated.INVOCATION if role == 'producer' else generated.copied.READER_INVOCATION,
            'root': str(self.attempt), 'chunk_index': 0, 'output_names': self.names, 'external_pins': self.pins,
            'source_snapshots': {}, 'source_revision': 'a' * 40, 'source': self.source,
            'runtime': dict(obs.runtime.EXPECTED), 'invocation_id': 'invented-invocation',
            'runtime_inventory_profile_pin': self.profiles[role]['expected_pin'],
            **({'recipe_id': generated.RECIPE} if role == 'producer' else {'expected_mode': generated.saved.MODE})}

    def _worker(self, role, request=None):
        self.role = role
        target = self.attempt / ('owned-generator' if role == 'producer' else 'owned-reader')
        target.mkdir()
        (target / 'inventory-profile.json').write_bytes(self.profiles[role]['raw'])
        raw = obs.v.canonical_json(self._request(role) if request is None else request)
        path = target / 'invocation.json'
        path.write_bytes(raw)
        function = generated.worker_main if role == 'producer' else generated.copied.reader_worker_main
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = function([str(path), obs._pin(raw)['sha256']])
        return code, json.loads(stream.getvalue()), target, obs._pin(raw)

    def _parent(self, *, active=True, tamper=None, outer=None):
        calls = []
        def supervise(argv, cwd, output, limits, *, boundary, on_started, resource_probe=None):
            self.role = 'producer' if not calls else 'initial-reader'
            role = self.role
            calls.append(role)
            self.assertEqual(limits, generated.LIMITS if role == 'producer' else generated.copied.READER_LIMITS)
            boundary()
            on_started(SimpleNamespace(pid=self.processes[role]['pid'], _handle=self.handles[role]))
            output.mkdir()
            function = generated.worker_main if role == 'producer' else generated.copied.reader_worker_main
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = function(argv[-2:])
            reply = json.loads(stream.getvalue())
            if tamper == role + '-handle':
                reply['runtime_observation']['process']['creation_time_100ns'] += 1
            if tamper == role + '-phase':
                (output.parent / (role + '-runtime-after.json')).write_bytes(b'changed')
            if tamper == role + '-unexpected':
                reply['runtime_observation'] = {}
            raw = obs.v.canonical_json(reply)
            (output / 'report.json').write_bytes(raw)
            return {'status': 'complete' if code == 0 else 'failed', 'exit_code': code,
                'worker_started': True, 'worker_pid': self.processes[role]['pid'],
                'worker_exit_confirmed': True, 'output': obs._pin(raw)}
        with patch.object(generated.supervisor, 'supervise', side_effect=supervise):
            result = generated.generate_and_read(self.attempt, expected_pins=self.pins, source_snapshots={},
                expected_revision='a' * 40, generation_runtime_profiles=self.profiles if active else None, outer_budget=outer)
        for role in calls:
            self.identity.assert_any_call(self.processes[role]['pid'], self.handles[role])
        return result, calls

    def test_producer_wraps_one_actual_operation_with_whole_invocation(self):
        code, reply, target, input_pin = self._worker('producer')
        self.assertEqual(code, 0)
        self.produce.assert_called_once()
        self.read.assert_not_called()
        self.assertEqual(reply['runtime_observation']['input_pin'], input_pin)
        self.assertEqual(reply['runtime_observation']['process'], self.processes['producer'])
        self.assertEqual(reply['runtime_observation']['format'], obs.GENERATION_RECEIPT)
        self.assertTrue((target / 'producer-runtime-after.json').is_file())

    def test_initial_reader_has_its_own_operation_identity_and_profile(self):
        code, reply, target, input_pin = self._worker('initial-reader')
        self.assertEqual(code, 0)
        self.read.assert_called_once()
        self.produce.assert_not_called()
        self.assertEqual(reply['runtime_observation']['input_pin'], input_pin)
        value = json.loads((target / 'initial-reader-runtime-before.json').read_bytes())
        self.assertEqual(value['role'], 'initial-reader')
        self.assertEqual(value['source_revision'], 'a' * 40)

    def test_actual_producer_failure_preserves_before_and_failure(self):
        self.produce.side_effect = ValueError('generation stopped')
        code, reply, target, _ = self._worker('producer')
        self.assertEqual(code, 2)
        self.assertEqual(reply['status'], 'failed')
        self.assertTrue((target / 'producer-runtime-before.json').is_file())
        self.assertTrue((target / 'producer-runtime-failure.json').is_file())
        self.assertFalse((target / 'producer-runtime-after.json').exists())

    def test_initial_reader_failure_preserves_before_without_success(self):
        self.read.side_effect = ValueError('initial read stopped')
        code, _, target, _ = self._worker('initial-reader')
        self.assertEqual(code, 2)
        self.assertTrue((target / 'initial-reader-runtime-failure.json').is_file())
        self.assertFalse((target / 'initial-reader-runtime-after.json').exists())

    def test_invalid_second_candidate_rejects_before_any_owned_role(self):
        profiles = copy.deepcopy(self.profiles)
        profiles['initial-reader']['raw'] += b' '
        with self.assertRaisesRegex(ValueError, 'external pin'):
            generated.generate_and_read(self.attempt, expected_pins=self.pins, source_snapshots={},
                expected_revision='a' * 40, generation_runtime_profiles=profiles)
        self.assertFalse((self.attempt / 'owned-generator').exists())
        self.produce.assert_not_called()

    def test_old_arithmetic_profile_format_does_not_upgrade_generation(self):
        value = {**self.profile, 'role': 'producer', 'operation': obs.OPERATIONS['producer']}
        with self.assertRaises(ValueError):
            obs.validate_profile(value, root=self.root, role='producer')

    def test_worker_revision_difference_stops_before_actual_generation(self):
        request = {**self._request('producer'), 'source_revision': 'b' * 40}
        code, reply, _, _ = self._worker('producer', request)
        self.assertEqual(code, 2)
        self.assertIn('worker revision', reply['detail'])
        self.produce.assert_not_called()

    def test_both_parent_roles_bind_original_handles_and_shared_budget(self):
        outer = negatives.FakeOuterBudget()
        result, calls = self._parent(outer=outer)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(calls, ['producer', 'initial-reader'])
        self.assertIs(result['generation_runtime_observation_checked'], True)
        self.assertEqual(result['runtime_processes'], self.processes)
        self.assertEqual(result['generation_runtime_profile_pins'], {k: v['expected_pin'] for k, v in self.profiles.items()})
        generated.recheck_runtime_profiles(self.attempt, result)
        self.assertEqual([row[0] for row in outer.roles], ['generator', 'reader'])
        self.assertEqual(outer.checkpoints[-1], 'postflight')
        self.assertFalse(result['formal_permission'])

    def test_changed_producer_phase_stops_before_initial_reader(self):
        result, calls = self._parent(tamper='producer-phase')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(calls, ['producer'])
        self.assertIn('phase pin', result['detail'])

    def test_reader_receipt_cannot_substitute_another_original_handle(self):
        result, _ = self._parent(tamper='initial-reader-handle')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('external binding', result['detail'])
        self.assertIs(result['generation_runtime_observation_checked'], False)

    def test_legacy_parent_rejects_an_unrequested_runtime_receipt(self):
        result, calls = self._parent(active=False, tamper='producer-unexpected')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(calls, ['producer'])
        self.assertIn('unexpected', result['detail'])

    def test_final_saved_phase_change_is_detected_without_work_replay(self):
        result, _ = self._parent()
        (self.attempt / 'owned-reader/initial-reader-runtime-after.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'pin'):
            generated.recheck_runtime_profiles(self.attempt, result)
        self.produce.assert_called_once()
        self.read.assert_called_once()

    def test_producer_phase_changed_during_reader_cannot_grant_parent_success(self):
        def read(request, root):
            (root / 'owned-generator/producer-runtime-after.json').write_bytes(b'changed')
            return self._read(request, root)
        self.read.side_effect = read
        result, calls = self._parent()
        self.assertEqual(calls, ['producer', 'initial-reader'])
        self.assertEqual(result['status'], 'failed')
        self.assertIs(result['generation_runtime_observation_checked'], False)
        self.assertIn('pin', result['detail'])


if __name__ == '__main__':
    unittest.main()
