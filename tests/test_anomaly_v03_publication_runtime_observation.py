"""Publication work and owned-process identity stay bound to external profiles."""
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
from banto_ai import anomaly_v03_saved_row_document_publication as pub
from banto_ai import anomaly_v03_preformal_saved_row_document_budget as saved
from tests import test_anomaly_v03_role_runtime_observation as helpers
from tests.test_anomaly_v03_preformal_contiguous_document_budget import FakeBudget


class PublicationRuntimeTests(unittest.TestCase):
    def setUp(self):
        helpers.RuntimeObservationTests.setUp(self)
        FakeBudget.instances = []
        FakeBudget.stop_phase = None
        for name in pub.SOURCE_NAMES:
            if name not in self.sources:
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'value = 1\n')
                self.sources[name] = obs._pin(path.read_bytes())
        self.profile.update(format=obs.PUBLICATION_FORMAT, role='writer', operation=obs.OPERATIONS['writer'])
        self.profiles = {}
        for role in ('writer', 'reader'):
            value = {**self.profile, 'role': role, 'operation': obs.OPERATIONS[role]}
            raw = obs.v.canonical_json(value)
            self.profiles[role] = {'raw': raw, 'expected_pin': obs._pin(raw)}
        self.request = {'format': pub.FORMAT + '-request', 'role': 'writer',
            'receipt_root': str(self.receipt), 'publication_root': str(self.receipt / 'published'),
            'source_revision': 'a' * 40, 'source_pins': self.sources,
            'payload_source_pins': {'invented.json': obs._pin(b'{}')},
            'payload_pins': {'invented.json': obs._pin(b'{}\n')}}
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(pub, 'ROOT', self.root))
        stack.enter_context(patch.object(pub.chain.platform_runtime, 'probe_runtime', return_value=dict(obs.runtime.EXPECTED)))
        stack.enter_context(patch.object(obs.runtime, 'probe_runtime', return_value=dict(obs.runtime.EXPECTED)))
        stack.enter_context(patch.object(obs, '_stdlib', return_value=self.stdlib))
        stack.enter_context(patch.object(obs.inventory, 'stdlib_paths', return_value=[('stdlib/example.py', self.lib)]))
        stack.enter_context(patch.object(obs.dependencies, 'collect', return_value=self.loaded))
        stack.enter_context(patch.object(obs.dependencies, 'verify_pair', return_value={'status': 'invented-check'}))
        stack.enter_context(patch.object(obs.process_evidence, 'creation_observation', return_value=self.process))
        self.perform = stack.enter_context(patch.object(pub, '_perform', return_value=(
            {'marker_raw_sha256': 'b' * 64}, {'invented.json': b'{}\n'})))

    def worker(self, *, request=None):
        request = dict(self.request if request is None else request)
        role = request['role']
        target = self.receipt / role
        target.mkdir()
        profile = self.profiles[role]
        request['runtime_inventory_profile_pin'] = profile['expected_pin']
        (target / 'inventory-profile.json').write_bytes(profile['raw'])
        raw = pub.io.json_bytes(request)
        path = target / 'request.json'
        path.write_bytes(raw)
        output = io.StringIO()
        with redirect_stdout(output):
            code = pub.worker_main([str(path), str(len(raw)), obs._pin(raw)['sha256']])
        return code, json.loads(output.getvalue()), target, obs._pin(raw)

    def test_publication_format_is_role_specific_and_old_arithmetic_format_rejects(self):
        bad = {**self.profile, 'format': obs.FORMAT}
        with self.assertRaises(ValueError):
            obs.validate_profile(bad, root=self.root, role='writer')
        self.assertEqual(obs.validate_profile(self.profile, root=self.root, role='writer'), self.profile)
        self.assertNotEqual(obs.receipt_format('writer'), obs.RECEIPT)

    def test_actual_writer_wraps_the_existing_operation_and_binds_whole_request(self):
        code, reply, target, request_pin = self.worker()
        self.assertEqual(code, 0)
        self.assertEqual(self.perform.call_count, 1)
        receipt = reply['runtime_observation']
        self.assertEqual(receipt['input_pin'], request_pin)
        self.assertEqual(receipt['process'], self.process)
        self.assertEqual(receipt['format'], obs.PUBLICATION_RECEIPT)
        for phase in ('before', 'after'):
            value = json.loads((target / ('writer-runtime-' + phase + '.json')).read_bytes())
            self.assertEqual(value['format'], obs.PUBLICATION_RECEIPT)
            self.assertEqual(value['role'], 'writer')
            self.assertEqual(value['input_pin'], request_pin)
        for name in obs.CLOSED:
            self.assertIs(receipt[name], False)

    def test_fresh_reader_uses_its_own_operation_and_profile(self):
        code, reply, target, request_pin = self.worker(request={**self.request, 'role': 'reader',
                                                               'expected_marker_sha256': 'b' * 64})
        self.assertEqual(code, 0)
        self.assertEqual(reply['runtime_observation']['profile_pin'], self.profiles['reader']['expected_pin'])
        before = json.loads((target / 'reader-runtime-before.json').read_bytes())
        self.assertEqual(before['role'], 'reader')
        self.assertEqual(before['input_pin'], request_pin)

    def test_operation_failure_preserves_before_and_failure_but_no_success(self):
        self.perform.side_effect = ValueError('publication stopped')
        code, reply, target, _ = self.worker()
        self.assertEqual(code, 2)
        self.assertEqual(reply['status'], 'rejected')
        self.assertTrue((target / 'writer-runtime-before.json').is_file())
        self.assertTrue((target / 'writer-runtime-failure.json').is_file())
        self.assertFalse((target / 'writer-runtime-after.json').exists())

    def test_code_revision_and_numerical_revision_are_not_silently_interchanged(self):
        code, reply, _, _ = self.worker(request={**self.request, 'source_revision': 'b' * 40,
                                               'worker_source_revision': 'c' * 40})
        self.assertEqual(code, 2)
        self.assertIn('worker revision', reply['detail'])
        self.perform.assert_not_called()

    def test_historical_numerical_revision_is_retained_when_worker_revision_is_explicit(self):
        request = {**self.request, 'source_revision': 'b' * 40, 'worker_source_revision': 'a' * 40}
        code, reply, _, _ = self.worker(request=request)
        self.assertEqual(code, 0)
        self.assertEqual(self.perform.call_args.args[0]['source_revision'], 'b' * 40)
        self.assertEqual(self.perform.call_args.args[0]['worker_source_revision'], 'a' * 40)

    def test_bad_reader_candidate_rejects_before_any_publication_work(self):
        profiles = copy.deepcopy(self.profiles)
        profiles['reader']['raw'] += b' '
        with self.assertRaisesRegex(ValueError, 'external pin'):
            pub.check_runtime_profiles(profiles, revision='a' * 40,
                source_pins=self.sources, runtime=obs.runtime.EXPECTED)
        self.perform.assert_not_called()

    def test_saved_receipt_cannot_be_rehashed_to_another_original_handle(self):
        _, reply, target, request_pin = self.worker()
        receipt = reply['runtime_observation']
        with self.assertRaisesRegex(ValueError, 'external binding'):
            obs.verify_receipt(receipt, root=target, source_root=self.root, role='writer',
                profile_raw=self.profiles['writer']['raw'], profile_pin=self.profiles['writer']['expected_pin'],
                input_pin=request_pin, process={**self.process, 'creation_time_100ns': 457})

    def test_saved_phase_change_is_rejected_by_parent_disk_crosscheck(self):
        _, reply, target, request_pin = self.worker()
        (target / 'writer-runtime-after.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'phase pin'):
            obs.verify_receipt(reply['runtime_observation'], root=target, source_root=self.root, role='writer',
                profile_raw=self.profiles['writer']['raw'], profile_pin=self.profiles['writer']['expected_pin'],
                input_pin=request_pin, process=self.process)

    def test_parent_owner_uses_caller_pin_and_checks_runtime_after_confirmed_exit(self):
        def supervise(argv, cwd, output, limits, *, boundary, on_started, resource_probe):
            boundary()
            on_started(SimpleNamespace(pid=self.process['pid'], _handle=object()))
            output.mkdir()
            raw_request = (self.receipt / 'writer/request.json').read_bytes()
            stream = io.StringIO()
            with patch.object(pub.os, 'getppid', return_value=os.getpid()), redirect_stdout(stream):
                code = pub.worker_main([str(self.receipt / 'writer/request.json'),
                                       str(len(raw_request)), obs._pin(raw_request)['sha256']])
            self.assertEqual(code, 0)
            raw = stream.getvalue().encode()
            (output / 'report.json').write_bytes(raw)
            return {'status': 'complete', 'worker_exit_confirmed': True, 'exit_code': 0,
                'worker_pid': self.process['pid'], 'observation_errors': [], 'output': obs._pin(raw), 'stop_reason': None}
        budget = FakeBudget(self.receipt, pub.chain.LIMITS).start()
        with patch.object(pub.platform, '_platform_scope', return_value=nullcontext()), \
             patch.object(pub.supervisor, 'supervise', side_effect=supervise):
            result = pub._role(self.request, self.receipt, budget, runtime_profile=self.profiles['writer'])
        self.assertTrue(result['worker_exit_confirmed'])
        self.assertEqual(result['runtime_observation']['process'], self.process)
        self.assertEqual(result['process'], {**self.process, 'parent_pid': os.getpid()})
        self.assertEqual(set(budget.roles), {'writer'})
        pub.recheck_runtime_profiles(self.receipt, {'writer': result,
            'publication_runtime_profile_pins': {'writer': self.profiles['writer']['expected_pin']}})

    def test_profile_request_without_external_parent_expectation_rejects_before_new_role_root(self):
        request = {**self.request, 'runtime_inventory_profile_pin': self.profiles['writer']['expected_pin']}
        with self.assertRaisesRegex(ValueError, 'expectation missing'):
            pub._role(request, self.receipt, None)
        self.assertFalse((self.receipt / 'writer').exists())

    def test_saved_control_callers_forward_publication_candidates(self):
        options = dict(control_root=self.root, expected_control_pinset_pin=obs._pin(b'control'),
            expected_mode='fixture', expected_input_pins={}, expected_revision='a' * 40,
            receipt_name='trial-one', publication_runtime_profiles=self.profiles)
        with patch.object(saved, 'run_saved_rows', return_value={}) as run:
            saved.run_saved_control_files(**options)
            saved.run_saved_control_files_with_observation_subset(**options,
                observation_subset=[], expected_observation_subset={})
        for call in run.call_args_list:
            self.assertIs(call.kwargs['publication_runtime_profiles'], self.profiles)


if __name__ == '__main__':
    unittest.main()
