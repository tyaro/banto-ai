"""Bounded, owned numerical fixture execution; no registered data or publication."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_fixture_worker as worker
from tests import test_anomaly_v03_wrapper_fixture as examples


def write_inputs(parent, revision, fixture_request):
    parent.mkdir()
    values = {'fixture/input.json': fixture_request['fixture_input'],
              'fixture/slices.json': fixture_request['slice_input'],
              'fixture/coverage.json': fixture_request['coverage'],
              'fixture/operation.json': worker.wrapper.operation_descriptor(revision)}
    records = {}
    for name, value in values.items():
        raw = worker.v.canonical_json(value)
        path = parent / Path(name).name
        path.write_bytes(raw)
        records[name] = {'path': str(path), 'pin': worker.observed._pin(raw), 'links': 1}
    return {'format': worker.FORMAT, 'mode': 'fixture', 'role': 'analysis', 'operation': worker.OPERATION,
            'inputs': records, 'expected_document_pin': worker.observed._pin(
                worker.v.canonical_json(fixture_request['document']))}


@unittest.skipUnless(os.name == 'nt' and sys.version_info[:2] == (3, 14), 'Windows CPython 3.14 observation')
class FixtureWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture, _ = examples.example()
        cls.revision = subprocess.check_output(['git', '-C', str(worker.ROOT), 'rev-parse', 'HEAD'], text=True).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='banto-fixture-worker-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.request = write_inputs(self.root/'inputs', self.revision, self.fixture)
        self.receipts = self.root/'receipts'; self.receipts.mkdir()

    def run_worker(self, request=None, name='attempt'):
        return worker.calculate_with_evidence(self.request if request is None else request,
            expected_revision=self.revision, receipt_parent=self.receipts, receipt_name=name)

    def change_input(self, name, change):
        row = self.request['inputs'][name]; path = Path(row['path'])
        value = json.loads(path.read_text(encoding='utf-8')); change(value)
        raw = worker.v.canonical_json(value); path.write_bytes(raw); row['pin'] = worker.observed._pin(raw)

    def test_owned_child_computes_and_binds_five_payloads_without_parent_inference(self):
        with patch.object(worker.wrapper.document, 'build_fixture_document', side_effect=AssertionError('parent inference')), \
             patch.object(worker.wrapper.document.I, 'compute_fixture_tables', side_effect=AssertionError('parent bootstrap')):
            value = self.run_worker()
        self.assertEqual(value['status'], 'verified', value)
        self.assertTrue(value['fixture_inference_performed'])
        self.assertTrue(value['worker_exit_confirmed'])
        self.assertNotEqual(value['worker_pid'], os.getpid())
        self.assertEqual(value['computation'], {'fixture_only': True, 'clusters': 40, 'replicates': 4})
        self.assertEqual(value['selected_source_files'], 21)
        self.assertEqual(value['authenticated_input_files'], 4)
        target = Path(value['check_directory'])
        self.assertEqual(worker.observed._pin((target/'payload/document.json').read_bytes()), self.request['expected_document_pin'])
        self.assertEqual(set(value['wrapper_payload_pins']), set(worker.wrapper.PAYLOADS))
        for name, pin in value['wrapper_payload_pins'].items():
            self.assertEqual(worker.observed._pin((target/'wrapper'/name).read_bytes()), pin)
        analysis = json.loads((target/'wrapper/analysis.json').read_text(encoding='utf-8'))
        for field in worker.wrapper.slices.PENDING:self.assertIsNone(analysis['document_draft'][field])
        for key, closed in worker.wrapper.CLOSED.items():self.assertEqual(value[key], closed)
        self.assertFalse(any('marker' in p.name for p in target.rglob('*')))

    def test_nonfixture_modes_roles_and_operations_rejected_before_io(self):
        for key, value in [('mode', 'formal'), ('mode', 'engineering-dev-smoke'), ('role', 'reader'),
                           ('operation', 'prepare-saved-result-v1'), ('format', 'registered')]:
            request = copy.deepcopy(self.request); request[key] = value
            with self.subTest(key=key, value=value), patch.object(worker.io, '_local_parent', side_effect=AssertionError('IO')):
                with self.assertRaises(ValueError):self.run_worker(request)

    def test_input_inventory_size_and_links_rejected_before_io(self):
        for kind in ('extra', 'large', 'links'):
            request = copy.deepcopy(self.request)
            if kind == 'extra':request['inputs']['other'] = request['inputs']['fixture/input.json']
            if kind == 'large':request['inputs']['fixture/slices.json']['pin']['bytes'] = 9*1024**2
            if kind == 'links':request['inputs']['fixture/input.json']['links'] = 2
            with self.subTest(kind=kind), patch.object(worker.io, '_local_parent', side_effect=AssertionError('IO')):
                with self.assertRaises(ValueError):self.run_worker(request)

    def test_changed_input_rejected_before_launch(self):
        Path(self.request['inputs']['fixture/input.json']['path']).write_bytes(b'{}')
        with patch.object(worker.supervisor, 'supervise', side_effect=AssertionError('launch')):
            result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIsNone(result['worker_pid'])

    def test_nine_draws_rejected_before_launch(self):
        self.change_input('fixture/input.json', lambda value: value.update(draws=value['draws']*2 + value['draws'][:1]))
        with patch.object(worker.supervisor, 'supervise', side_effect=AssertionError('launch')):
            result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIn('eight', result['detail'])

    def test_partial_coverage_rejected_before_launch(self):
        def change(value):
            candidate = worker.wrapper.document.I.CANDIDATES[0]
            value['clusters'][0]['candidates'][candidate]['core'][0] = 'partial'
        self.change_input('fixture/coverage.json', change)
        with patch.object(worker.supervisor, 'supervise', side_effect=AssertionError('launch')):
            result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIn('coverage', result['detail'])

    def test_wrong_operation_revision_rejected_before_launch(self):
        self.change_input('fixture/operation.json', lambda value: value.update(source_revision='f'*40))
        with patch.object(worker.supervisor, 'supervise', side_effect=AssertionError('launch')):
            result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIn('revision', result['detail'])

    def test_source_revision_mismatch_rejected_before_launch(self):
        with patch.object(worker.supervisor, 'supervise', side_effect=AssertionError('launch')):
            result = worker.calculate_with_evidence(self.request, expected_revision='f'*40,
                receipt_parent=self.receipts, receipt_name='wrong-source')
        self.assertEqual(result['status'], 'failed'); self.assertIsNone(result['worker_pid'])

    def test_wrong_retained_output_pin_rejects_actual_child(self):
        self.request['expected_document_pin']['sha256'] = 'f'*64
        result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertTrue(result['worker_exit_confirmed'])
        target = Path(result['check_directory'])
        monitor = json.loads((target/'supervision.json').read_text(encoding='utf-8'))
        self.assertEqual(monitor['exit_code'], 2); self.assertFalse((target/'wrapper').exists())
        self.assertIn('retained pin', (target/'worker/report.json').read_text(encoding='utf-8'))

    def test_resealed_wrong_role_rejected_by_parent(self):
        original = worker.supervisor.supervise
        def alter(*args, **kwargs):
            monitor = original(*args, **kwargs)
            self.assertEqual(monitor['status'], 'complete', monitor)
            path = args[2]/'report.json'
            reply = json.loads(path.read_text(encoding='utf-8')); reply['evidence']['role'] = 'reader'
            raw = worker.io.json_bytes(reply); path.write_bytes(raw); monitor['output'] = worker.observed._pin(raw)
            return monitor
        with patch.object(worker.supervisor, 'supervise', side_effect=alter):result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIn('role', result['detail'])
        self.assertFalse((Path(result['check_directory'])/'wrapper').exists())

    def test_resealed_wrong_creation_rejected_by_owned_handle(self):
        original = worker.supervisor.supervise
        def alter(*args, **kwargs):
            monitor = original(*args, **kwargs)
            self.assertEqual(monitor['status'], 'complete', monitor)
            path = args[2]/'report.json'
            reply = json.loads(path.read_text(encoding='utf-8')); reply['creation_observation']['start_token'] = 'f'*64
            raw = worker.io.json_bytes(reply); path.write_bytes(raw); monitor['output'] = worker.observed._pin(raw)
            return monitor
        with patch.object(worker.supervisor, 'supervise', side_effect=alter):result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIn('creation', result['detail'])

    def test_retained_expectation_mutation_rejected(self):
        original = worker.supervisor.supervise
        def alter(*args, **kwargs):
            monitor = original(*args, **kwargs)
            self.assertEqual(monitor['status'], 'complete', monitor)
            (args[2].parent/'expected.json').write_bytes(b'{}')
            return monitor
        with patch.object(worker.supervisor, 'supervise', side_effect=alter):result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertIn('retained expectation', result['detail'])

    def test_failed_supervision_does_not_read_or_map_worker_output(self):
        monitor = {'status': 'failed', 'worker_exit_confirmed': True, 'worker_pid': 12345, 'stop_reason': 'wall_limit'}
        with patch.object(worker.supervisor, 'supervise', return_value=monitor), \
             patch.object(worker.wrapper, 'assemble_fixture_wrapper', side_effect=AssertionError('map')):
            result = self.run_worker()
        self.assertEqual(result['status'], 'failed'); self.assertEqual(result['reason'], 'wall_limit')
        self.assertFalse(result['fixture_inference_performed'])

    def test_unreaped_owner_survives_even_receipt_save_failure(self):
        owner = object(); error = worker.supervisor.UnreapedWorker(owner, {'worker_exit_confirmed': False})
        original_save = worker.observed._save
        def save(path, value):
            if path.name == 'supervision.json':raise OSError('receipt unavailable')
            return original_save(path, value)
        with patch.object(worker.supervisor, 'supervise', side_effect=error), patch.object(worker.observed, '_save', side_effect=save):
            with self.assertRaises(worker.supervisor.UnreapedWorker) as caught:self.run_worker()
        self.assertIs(caught.exception, error); self.assertIs(caught.exception.process, owner)

    def test_existing_attempt_and_input_overlap_never_overwritten(self):
        (self.receipts/'attempt').mkdir(); (self.receipts/'attempt/evidence').write_bytes(b'keep')
        with self.assertRaises((ValueError, OSError)):self.run_worker()
        self.assertEqual((self.receipts/'attempt/evidence').read_bytes(), b'keep')
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            worker.calculate_with_evidence(self.request, expected_revision=self.revision,
                receipt_parent=self.root/'inputs', receipt_name='child')


if __name__ == '__main__':unittest.main()
