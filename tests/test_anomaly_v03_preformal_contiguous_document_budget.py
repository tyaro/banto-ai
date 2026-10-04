"""Fail-closed orchestration checks for one invented contiguous budget."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_contiguous_document_budget as chain
from tests.test_anomaly_v03_bound_fixture_pipeline import example


REVISION = 'a' * 40


class FakeBudget:
    instances = []
    stop_phase = None

    def __init__(self, root, limits):
        self.root = root
        self.limits = limits
        self._thread = None
        self.phases = []
        self.roles = {}
        self.outputs = {}
        self.closed = False
        type(self).instances.append(self)

    def start(self):
        self._thread = object()
        return self

    def checkpoint(self, phase):
        self.phases.append(phase)
        if phase == type(self).stop_phase:
            raise chain.draw_bridge.resources.ResourceStop('pipeline_wall_limit')

    def probe(self):
        return None

    def record_role(self, role, status, result_pin=None, worker_pid=None,
                    exit_confirmed=None):
        self.roles[role] = {'status': status, 'exit': exit_confirmed,
                            'pin': result_pin}

    def record_output(self, name, pin):
        self.outputs[name] = pin

    def close(self):
        self.closed = True
        return {
            'passed': type(self).stop_phase is None,
            'stop_reason': ('pipeline_wall_limit' if type(self).stop_phase else None),
            'both_arithmetic_child_exits_reported':
                set(self.roles) == {'analysis', 'audit'} and all(
                    row['status'] == 'complete' and row['exit']
                    for row in self.roles.values()),
            'all_mapping_outputs_reported':
                set(self.outputs) == {'document', 'slices', 'slice-count-audit'},
        }


class LatchedBudget:
    def __init__(self):
        self.latched = False

    def checkpoint(self, phase):
        if self.latched:
            raise chain.draw_bridge.resources.ResourceStop('pipeline_wall_limit')

    def record_output(self, name, pin):
        raise AssertionError('output recorded after stop')


class ContiguousDocumentBudgetTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='banto-contiguous-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.producer_parent = self.root / 'artifacts/anomaly-v03-preformal-five-role-26h2'
        self.producer = self.producer_parent / 'trial-01/producer'
        output = self.producer / 'output'
        (output / 'projection/fixture').mkdir(parents=True)
        self.output_parent = self.root / 'artifacts/contiguous'
        bound = chain.draw_bridge.projection.v.canonical_json(example())
        bound_pin = chain.draw_bridge._pin(bound)
        prepared = chain.draw_bridge.projection.prepare_inputs(
            bound, expected_mode='fixture', expected_pin=bound_pin,
            expected_revision=REVISION, draws=[list(range(40))])
        (output / 'bound.json').write_bytes(bound)
        for name, raw in prepared['files'].items():
            path = output / 'projection' / name
            path.write_bytes(raw)
        self.projection_pins = {
            name: chain.draw_bridge._pin(raw)
            for name, raw in prepared['files'].items()
        }
        receipt = {
            'format': chain.draw_bridge.producer.FORMAT,
            'mode': 'fixture', 'status': 'verified',
            'owned_producer_join_executed': True,
            'worker_exit_confirmed': True,
            'real_producer_executed': False,
            'registered_data_read': False, 'new_evaluations': 0,
            'formal_permission': False, 'promotion_allowed': False,
            'source_revision': REVISION,
            'bound_path': str(output / 'bound.json'),
            'projection_root': str(output / 'projection'),
            'bound_pin': bound_pin,
            'projection_pins': self.projection_pins,
        }
        raw = chain.draw_bridge._raw(receipt)
        (self.producer / 'result.json').write_bytes(raw)
        self.result_pin = chain.draw_bridge._pin(raw)
        self.patch_parent = patch.object(chain.draw_bridge, 'PRODUCER_PARENT',
                                         self.producer_parent)
        self.patch_parent.start()
        self.addCleanup(self.patch_parent.stop)
        FakeBudget.instances = []
        FakeBudget.stop_phase = None

    def run_chain(self, name, **options):
        with patch.object(chain, 'OUTPUT_PARENT', self.output_parent), \
             patch.object(chain, '_source_pins',
                          return_value={'selected': self.result_pin}), \
             patch.object(chain.platform_runtime, 'probe_runtime',
                          return_value={'test': True}), \
             patch.object(chain, 'ContiguousBudget', FakeBudget):
            return chain.run_chain(
                expected_mode='fixture', producer_root=self.producer,
                expected_producer_result_pin=self.result_pin,
                expected_projection_pins=self.projection_pins,
                expected_revision=REVISION, receipt_name=name,
                receipt_parent=self.output_parent, **options)

    @staticmethod
    def fake_arithmetic(root, input_pin, budget, result):
        calculation = {'fake': 'full-draw-result'}
        audit = {'fake': 'independent-arithmetic-result'}
        result['calculation_pin'] = chain._write_value(
            root / 'calculation.json', calculation, chain.MAX_CONTROL)
        result['arithmetic_audit_pin'] = chain._write_value(
            root / 'audit.json', audit, chain.MAX_CONTROL)
        for role in ('analysis', 'audit'):
            budget.checkpoint(role)
            budget.record_role(role, 'complete', result_pin=result['calculation_pin'],
                               worker_pid=100 if role == 'analysis' else 101,
                               exit_confirmed=True)
        result['both_arithmetic_children_verified'] = True
        return calculation, audit

    @staticmethod
    def fake_document(root, binding, producer_input, calculation, audit,
                      budget, result):
        budget.checkpoint('document')
        value = {'invented_document': True}
        result['document_pin'] = chain._write_value(
            root / 'document.json', value, chain.MAX_CONTROL)
        budget.record_output('document', result['document_pin'])
        return value, {'fixed': True}

    @staticmethod
    def fake_slices(root, binding, producer_input, source, document, schema,
                    budget, result):
        budget.checkpoint('slices')
        for name, file_name, field in (
                ('slices', 'slices.json', 'slices_pin'),
                ('slice-count-audit', 'slice-count-audit.json',
                 'slice_count_audit_pin')):
            pin = chain._write_value(root / file_name, {name: True},
                                     chain.MAX_CONTROL)
            result[field] = pin
            budget.record_output(name, pin)

    def test_bad_external_pin_rejects_before_new_root_or_child(self):
        wrong = dict(self.projection_pins)
        wrong['fixture/slices.json'] = {'bytes': 1, 'sha256': '0' * 64}
        with patch.object(chain, 'OUTPUT_PARENT', self.output_parent), \
             patch.object(chain, '_arithmetic',
                          side_effect=AssertionError('arithmetic started')):
            with self.assertRaisesRegex(ValueError, 'external projection pins differ'):
                chain.run_chain(
                    expected_mode='fixture', producer_root=self.producer,
                    expected_producer_result_pin=self.result_pin,
                    expected_projection_pins=wrong,
                    expected_revision=REVISION, receipt_name='trial-bad',
                    receipt_parent=self.output_parent)
        self.assertFalse(self.output_parent.exists())

    def test_one_budget_spans_two_children_document_and_slices(self):
        with patch.object(chain, '_arithmetic', side_effect=self.fake_arithmetic), \
             patch.object(chain, '_document', side_effect=self.fake_document), \
             patch.object(chain, '_slices', side_effect=self.fake_slices):
            result = self.run_chain('trial-good')
        budget = FakeBudget.instances[0]
        self.assertEqual(len(FakeBudget.instances), 1)
        self.assertTrue(budget.closed)
        self.assertEqual(budget.phases,
                         ['preflight', 'analysis', 'audit', 'document',
                          'slices', 'postflight'])
        self.assertEqual(result['status'], 'measured')
        self.assertTrue(result['same_budget_50000_arithmetic_document_slices_measured'])
        self.assertFalse(result['full_end_to_end_budget_measured'])
        self.assertFalse(result['formal_50000_draw_budget_measured'])
        self.assertIsNone(result['smoke_capacity_twice_passed'])
        for name in ('result.json', 'resource-budget.json', 'document.json',
                     'slices.json', 'slice-count-audit.json'):
            self.assertTrue((self.output_parent / 'trial-good' / name).is_file())

    def test_arithmetic_failure_never_starts_document_or_slices(self):
        with patch.object(chain, '_arithmetic',
                          side_effect=chain.draw_bridge.resources.ResourceStop(
                              'bridge_child_private_limit')), \
             patch.object(chain, '_document',
                          side_effect=AssertionError('document started')), \
             patch.object(chain, '_slices',
                          side_effect=AssertionError('slices started')):
            result = self.run_chain('trial-arithmetic-failed')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'bridge_child_private_limit')
        self.assertTrue(FakeBudget.instances[0].closed)
        target = self.output_parent / 'trial-arithmetic-failed'
        self.assertTrue((target / 'result.json').is_file())
        self.assertTrue((target / 'resource-budget.json').is_file())
        self.assertFalse((target / 'document.json').exists())
        self.assertFalse((target / 'slices.json').exists())

    def test_failed_audit_supervision_blocks_document_before_mapping(self):
        def supervise(role, root, input_pin, calculation_pin, budget):
            if role == 'analysis':
                chain._write_value(root / 'calculation.json', {'fake': True},
                                   chain.MAX_CONTROL)
            return {'status': 'complete' if role == 'analysis' else 'failed',
                    'pid': 100 if role == 'analysis' else 101,
                    'worker_exit_confirmed': True,
                    'stop_reason': None if role == 'analysis' else
                                   'bridge_child_wall_limit'}
        with patch.object(chain.draw_bridge, '_supervise', side_effect=supervise), \
             patch.object(chain.draw_bridge, '_verify_role'), \
             patch.object(chain, '_document',
                          side_effect=AssertionError('document started')):
            result = self.run_chain('trial-audit-failed')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'bridge_child_wall_limit')
        self.assertEqual(result['stage'], 'audit')
        target = self.output_parent / 'trial-audit-failed'
        self.assertTrue((target / 'calculation.json').is_file())
        self.assertTrue((target / 'audit-supervision.json').is_file())
        self.assertFalse((target / 'document.json').exists())

    def test_bad_full_draw_audit_blocks_document(self):
        def supervise(role, root, input_pin, calculation_pin, budget):
            name = 'calculation.json' if role == 'analysis' else 'audit.json'
            chain._write_value(root / name, {'wrong_draw_contract': True},
                               chain.MAX_CONTROL)
            return {'status': 'complete', 'pid': 100 if role == 'analysis' else 101,
                    'worker_exit_confirmed': True, 'stop_reason': None}
        with patch.object(chain.draw_bridge, '_supervise', side_effect=supervise), \
             patch.object(chain.draw_bridge, '_verify_role'), \
             patch.object(chain, '_document',
                          side_effect=AssertionError('document started')):
            result = self.run_chain('trial-bad-draw')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('audit_report_fields', result['detail'])
        self.assertFalse(result['both_arithmetic_children_verified'])
        target = self.output_parent / 'trial-bad-draw'
        self.assertTrue((target / 'audit.json').is_file())
        self.assertFalse((target / 'document.json').exists())

    def test_external_change_before_document_blocks_mapping(self):
        original = chain._external
        calls = 0
        def changed(*args):
            nonlocal calls
            calls += 1
            binding, producer_input, source = original(*args)
            if calls == 2:
                binding = {**binding, 'source_scope': 'changed'}
            return binding, producer_input, source
        with patch.object(chain, '_external', side_effect=changed), \
             patch.object(chain, '_arithmetic', side_effect=self.fake_arithmetic), \
             patch.object(chain, '_document',
                          side_effect=AssertionError('document started')):
            result = self.run_chain('trial-external-changed')
        self.assertEqual(calls, 2)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('external producer changed before document', result['detail'])
        self.assertFalse((self.output_parent / 'trial-external-changed' /
                          'document.json').exists())

    def test_slice_failure_keeps_document_and_terminal_failure(self):
        def failed_slices(root, binding, producer_input, source, document, schema,
                          budget, result):
            budget.checkpoint('slices')
            chain._write_value(root / 'slice-partial.json', {'partial': True},
                               chain.MAX_CONTROL)
            raise ValueError('fixture slice count mismatch')
        with patch.object(chain, '_arithmetic', side_effect=self.fake_arithmetic), \
             patch.object(chain, '_document', side_effect=self.fake_document), \
             patch.object(chain, '_slices', side_effect=failed_slices):
            result = self.run_chain('trial-slice-failed')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'slices')
        self.assertIn('fixture slice count mismatch', result['detail'])
        target = self.output_parent / 'trial-slice-failed'
        self.assertTrue((target / 'document.json').is_file())
        self.assertTrue((target / 'slice-partial.json').is_file())
        self.assertTrue((target / 'result.json').is_file())
        self.assertTrue((target / 'resource-budget.json').is_file())

    def test_document_budget_stop_retains_partial_root_and_terminal_receipt(self):
        FakeBudget.stop_phase = 'document'
        with patch.object(chain, '_arithmetic', side_effect=self.fake_arithmetic), \
             patch.object(chain, '_document', side_effect=self.fake_document), \
             patch.object(chain, '_slices',
                          side_effect=AssertionError('slices started')):
            result = self.run_chain('trial-document-stop')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        target = self.output_parent / 'trial-document-stop'
        self.assertTrue((target / 'calculation.json').is_file())
        self.assertTrue((target / 'audit.json').is_file())
        self.assertFalse((target / 'document.json').exists())
        self.assertTrue((target / 'result.json').is_file())
        self.assertTrue((target / 'resource-budget.json').is_file())

    def test_document_mapping_stop_blocks_document_write(self):
        target = self.output_parent / 'document-latched'
        target.mkdir(parents=True)
        budget = LatchedBudget()
        packet = {'fixture_candidate_tables': [],
                  'fixture_selected_candidate': None,
                  'fixture_decision': None}
        original_draft = chain.document_bridge.document._draft

        def draft_then_stop(value):
            draft = original_draft(value)
            budget.latched = True
            return draft

        with patch.object(chain.document_bridge.adapter,
                          'map_precomputed_fixture_packet', return_value=packet), \
             patch.object(chain.document_bridge.document, '_draft',
                          side_effect=draft_then_stop):
            with self.assertRaises(chain.draw_bridge.resources.ResourceStop):
                chain._document(
                    target, {'clusters': []}, {'diagnostics': []}, {},
                    {'draw_sha256': '0' * 64}, budget,
                    {'input_pin': self.result_pin,
                     'calculation_pin': self.result_pin,
                     'arithmetic_audit_pin': self.result_pin})
        self.assertFalse((target / 'document.json').exists())

    def test_slice_derivation_stop_blocks_count_audit_and_writes(self):
        target = self.output_parent / 'slices-derived-latched'
        target.mkdir(parents=True)
        budget = LatchedBudget()
        derived = {'slices': [], 'diagnostic_series': [],
                   'diagnostic_details': [],
                   'slice_input_canonical_sha256': '0' * 64}

        def derive_then_stop(*args):
            budget.latched = True
            return derived

        with patch.object(chain.slice_bridge.slices,
                          'derive_precomputed_slices',
                          side_effect=derive_then_stop), \
             patch.object(chain.slice_bridge.independent,
                          'audit_precomputed_slices',
                          side_effect=AssertionError('count audit after stop')):
            with self.assertRaises(chain.draw_bridge.resources.ResourceStop):
                chain._slices(
                    target, {'clusters': [], 'projection_pins':
                             {'fixture/slices.json': self.result_pin}},
                    {'diagnostics': []}, {},
                    {'fixture_packet': {}, 'document_draft': {'slices': None}},
                    {}, budget, {'document_pin': self.result_pin})
        self.assertFalse((target / 'slices.json').exists())
        self.assertFalse((target / 'slice-count-audit.json').exists())

    def test_count_audit_stop_blocks_slice_and_audit_writes(self):
        target = self.output_parent / 'slices-audited-latched'
        target.mkdir(parents=True)
        budget = LatchedBudget()
        derived = {'slices': [], 'diagnostic_series': [],
                   'diagnostic_details': [],
                   'slice_input_canonical_sha256': '0' * 64}

        def audit_then_stop(*args):
            budget.latched = True
            return {'count_audit_completed': True}

        with patch.object(chain.slice_bridge.slices,
                          'derive_precomputed_slices', return_value=derived), \
             patch.object(chain.slice_bridge, '_audit_input', return_value={}), \
             patch.object(chain.slice_bridge.independent,
                          'audit_precomputed_slices',
                          side_effect=audit_then_stop), \
             patch.object(chain.document_bridge, '_same_fields'):
            with self.assertRaises(chain.draw_bridge.resources.ResourceStop):
                chain._slices(
                    target, {'clusters': [], 'projection_pins':
                             {'fixture/slices.json': self.result_pin}},
                    {'diagnostics': []}, {},
                    {'fixture_packet': {}, 'document_draft': {'slices': None}},
                    {}, budget, {'document_pin': self.result_pin})
        self.assertFalse((target / 'slices.json').exists())
        self.assertFalse((target / 'slice-count-audit.json').exists())

    def test_unreaped_child_preserves_failure_receipt_and_raises(self):
        owner = chain.draw_bridge.draw_budget.UnreapedMeasurement(
            object(), 'audit', {'stop_reason': None})
        with patch.object(chain, '_arithmetic', side_effect=owner), \
             patch.object(chain, '_document',
                          side_effect=AssertionError('document started')):
            with self.assertRaises(chain.draw_bridge.draw_budget.UnreapedMeasurement):
                self.run_chain('trial-unreaped')
        target = self.output_parent / 'trial-unreaped'
        self.assertEqual(owner.receipt, target)
        self.assertEqual(json.loads((target / 'result.json').read_bytes())['reason'],
                         'owned_child_exit_unconfirmed')
        self.assertTrue((target / 'resource-budget.json').is_file())

    def test_budget_scope_phases_and_tightening_are_independent(self):
        self.assertNotEqual(chain.FORMAT, chain.draw_bridge.FORMAT)
        self.assertIn('document', chain.PHASES)
        self.assertIn('slices', chain.PHASES)
        with self.assertRaisesRegex(ValueError, 'only tighten'):
            chain._limits({**chain.LIMITS, 'wall_seconds': 1201})
        self.assertEqual(chain._limits()['wall_seconds'], 1200)


if __name__ == '__main__':
    unittest.main()
