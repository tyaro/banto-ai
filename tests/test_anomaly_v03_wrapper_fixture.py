"""Fixture wrapper connections; no real observations, processes or publications."""
import copy
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_wrapper_fixture as wrapper
from tests import test_anomaly_v03_slice_fixture as hand
from tests import test_anomaly_v03_consumer_evidence as supplied

SCHEMA = hand.SCHEMA
REVISION = 'a'*40


def retained_inputs(request, revision=REVISION):
    values = {'fixture/input.json': request['fixture_input'], 'fixture/slices.json': request['slice_input'],
              'fixture/coverage.json': request['coverage'],
              'fixture/operation.json': wrapper.operation_descriptor(revision)}
    return {n: supplied.pin(wrapper.v.canonical_json(value)) for n, value in values.items()}


def example(*, inconclusive=False):
    fixture = hand.hand.invented_input()
    if inconclusive:
        fixture['clusters'][0]['candidates'][wrapper.document.I.CANDIDATES[0]]['core']['profile_status'] = 'inconclusive'
    source = hand.invented_slices(fixture)
    base = wrapper.document.build_fixture_document(fixture, SCHEMA)
    connected = wrapper.slices.attach_fixture_slices(base, fixture, source, SCHEMA)
    coverage = {'format': wrapper.COVERAGE_FORMAT, 'invented_only': True, 'layout_ids': list(range(12)),
        'clusters': [{'cluster_id': cluster['cluster_id'], 'candidates': {
            c: {s: ['inconclusive' if cluster['candidates'][c][s]['profile_status'] == 'inconclusive' else 'success']*12
                for s in wrapper.document.I.STRATA[:2]} for c in wrapper.document.I.CANDIDATES}}
            for cluster in fixture['clusters']]}
    request = {'format': wrapper.FORMAT, 'mode': 'fixture', 'invented_only': True,
               'fixture_input': fixture, 'slice_input': source, 'coverage': coverage, 'document': connected}
    # These deliberately invented caller expectations are NOT observations.
    case = supplied.case(role='analysis')
    expected = case['expected']
    expected['inputs'] = retained_inputs(request)
    expected['outputs'] = {'fixture/document.json': supplied.pin(wrapper.v.canonical_json(connected))}
    for name in ('inputs', 'outputs'):
        case['evidence'][name] = copy.deepcopy(expected[name])
    raw = wrapper.v.canonical_json(case['evidence'])
    return request, {'expected_mode': 'fixture', 'expected_revision': REVISION,
        'expected_input_pins': copy.deepcopy(expected['inputs']), 'analysis_record': raw,
        'expected_analysis': {'evidence_pin': supplied.pin(raw), 'invocation': expected},
        'source_snapshots': case['source_snapshots'], 'runtime_snapshots': case['runtime_snapshots']}


def without_document(request, kwargs):
    request['document'] = None
    for name in ('analysis_record', 'expected_analysis', 'source_snapshots', 'runtime_snapshots'):
        kwargs[name] = None
    kwargs['expected_input_pins'] = retained_inputs(request)


class WrapperFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request, cls.kwargs = example()

    def fresh(self):
        return copy.deepcopy((self.request, self.kwargs))

    def build(self, request=None, kwargs=None):
        return wrapper.assemble_fixture_wrapper(self.request if request is None else request, SCHEMA,
                                               **(self.kwargs if kwargs is None else kwargs))

    def test_five_payloads_and_evidence_link_without_formal_promotion(self):
        value = self.build(); payloads = value['payloads']
        self.assertEqual(tuple(payloads), wrapper.PAYLOADS)
        self.assertEqual(payloads['coverage.json']['summary']['planned_evaluations'], 2880)
        self.assertEqual(payloads['coverage.json']['summary']['counts']['success'], 2880)
        self.assertEqual(payloads['analysis.json']['document_draft'], self.request['document']['document_draft'])
        self.assertEqual(sum(map(len, payloads['diagnostics.json']['series'].values())), 2835)
        for name, payload in payloads.items():
            self.assertEqual(value['payload_pins'][name], supplied.pin(wrapper.v.canonical_json(payload)))
            for key, expected in wrapper.CLOSED.items():self.assertEqual(payload[key], expected)
        binding = payloads['execution.json']['analysis_binding']
        self.assertEqual(binding['evidence_pin'], self.kwargs['expected_analysis']['evidence_pin'])
        self.assertEqual(binding['output_pins'], self.kwargs['expected_analysis']['invocation']['outputs'])
        self.assertEqual(payloads['execution.json']['stages']['audit'], 'not_run')
        for field in wrapper.slices.PENDING:self.assertIsNone(payloads['analysis.json']['document_draft'][field])
        self.assertEqual(wrapper.validate_fixture_wrapper(value, self.request, SCHEMA, **self.kwargs)['payloads'], 5)

    def test_assembly_and_validation_do_not_recompute_or_access_io(self):
        with patch('builtins.open', side_effect=AssertionError('file IO')), \
             patch.object(Path, 'open', side_effect=AssertionError('path IO')), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('process')), \
             patch.object(wrapper.document.adapter, 'compute_fixture_packet', side_effect=AssertionError('CI recompute')), \
             patch.object(wrapper.document.I, 'compute_fixture_tables', side_effect=AssertionError('inference')):
            value = self.build()
            self.assertFalse(wrapper.validate_fixture_wrapper(value, self.request, SCHEMA, **self.kwargs)['inference_recomputed'])

    def test_formal_or_engineering_mode_rejected_before_input_access(self):
        for mode in ('holdout', 'formal', 'engineering-dev-smoke', True):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'mode is closed'):
                wrapper.assemble_fixture_wrapper(None, None, expected_mode=mode,
                    expected_revision=None, expected_input_pins=None)

    def test_identity_and_extra_success_claims_rejected(self):
        for name, replacement in [('format', 'formal'), ('mode', 'engineering-dev-smoke'),
                                   ('invented_only', 1), ('formal_permission', True), ('stages', {'analysis':'complete'})]:
            request = {**self.request, name: replacement}
            with self.subTest(name=name), self.assertRaises(ValueError):self.build(request)

    def test_retained_input_pins_are_not_rederived_from_supplied_values(self):
        request, kwargs = self.fresh()
        request['fixture_input']['engineering_ready_assumption'] = False
        with self.assertRaisesRegex(ValueError, 'retained wrapper inputs'):self.build(request, kwargs)
        for name in ('fixture/coverage.json', 'fixture/operation.json'):
            kwargs = copy.deepcopy(self.kwargs);kwargs['expected_input_pins'][name] = supplied.pin(b'other purpose')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'retained wrapper inputs'):self.build(kwargs=kwargs)

    def test_saved_result_preparation_operation_cannot_replace_fixture_analysis(self):
        kwargs = copy.deepcopy(self.kwargs)
        kwargs['expected_analysis']['invocation']['inputs'] = {'saved/input.json': supplied.pin(b'old saved report')}
        with self.assertRaisesRegex(ValueError, 'operation/input inventory'):self.build(kwargs=kwargs)
        kwargs = copy.deepcopy(self.kwargs);kwargs['expected_revision'] = 'd'*40
        kwargs['expected_input_pins'] = retained_inputs(self.request, 'd'*40)
        with self.assertRaisesRegex(ValueError, 'revision binding'):self.build(kwargs=kwargs)

    def test_resealed_wrong_role_mode_and_unconfirmed_exit_rejected(self):
        for field, replacement in [('role', 'reader'), ('mode', 'engineering-dev-smoke'),
                                   ('completion', {'status':'completed','exit_code':0,'worker_exit_confirmed':False,'observation_errors':[]})]:
            kwargs = copy.deepcopy(self.kwargs);value = wrapper.v.strict_json(kwargs['analysis_record'])
            value[field] = replacement;kwargs['analysis_record'] = wrapper.v.canonical_json(value)
            kwargs['expected_analysis']['evidence_pin'] = supplied.pin(kwargs['analysis_record'])
            with self.subTest(field=field), self.assertRaises(ValueError):self.build(kwargs=kwargs)

    def test_document_requires_external_expectation_and_original_output_bytes(self):
        kwargs = copy.deepcopy(self.kwargs);kwargs['expected_analysis'] = None
        with self.assertRaisesRegex(ValueError, 'expectation required'):self.build(kwargs=kwargs)
        kwargs = copy.deepcopy(self.kwargs);kwargs['source_snapshots'][REVISION]['src/banto_ai/entry.py'] = b'# substituted'
        with self.assertRaisesRegex(ValueError, 'source snapshot'):self.build(kwargs=kwargs)
        kwargs = copy.deepcopy(self.kwargs)
        kwargs['expected_analysis']['invocation']['outputs']['fixture/document.json'] = supplied.pin(b'other document')
        value = wrapper.v.strict_json(kwargs['analysis_record']);value['outputs'] = kwargs['expected_analysis']['invocation']['outputs']
        kwargs['analysis_record'] = wrapper.v.canonical_json(value)
        kwargs['expected_analysis']['evidence_pin'] = supplied.pin(kwargs['analysis_record'])
        with self.assertRaisesRegex(ValueError, 'output snapshot'):self.build(kwargs=kwargs)

    def test_coverage_identity_layout_and_profile_cannot_be_relabelled(self):
        for change in ('duplicate', 'missing', 'layout', 'unknown', 'profile'):
            request, kwargs = self.fresh();coverage = request['coverage']
            if change == 'duplicate':coverage['clusters'][1]['cluster_id'] = coverage['clusters'][0]['cluster_id']
            elif change == 'missing':coverage['clusters'].pop()
            elif change == 'layout':coverage['layout_ids'][-1] = 0
            else:
                states = coverage['clusters'][0]['candidates'][wrapper.document.I.CANDIDATES[0]]['core']
                states[0] = True if change == 'unknown' else 'inconclusive'
            kwargs['expected_input_pins'] = retained_inputs(request)
            with self.subTest(change=change), self.assertRaises(ValueError):self.build(request, kwargs)

    def test_failed_or_partial_coverage_cannot_carry_a_completed_document(self):
        for state in ('failed', 'partial', 'not_started'):
            request, kwargs = self.fresh()
            request['coverage']['clusters'][0]['candidates'][wrapper.document.I.CANDIDATES[0]]['core'][0] = state
            kwargs['expected_input_pins'] = retained_inputs(request)
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, 'incomplete coverage'):self.build(request, kwargs)

    def test_incomplete_payloads_retain_failed_slots_and_no_analysis_claims(self):
        request, kwargs = self.fresh()
        request['coverage']['clusters'][0]['candidates'][wrapper.document.I.CANDIDATES[0]]['core'][:3] = ['failed','partial','not_started']
        without_document(request, kwargs);value = self.build(request, kwargs)['payloads']
        self.assertEqual(value['coverage.json']['summary']['counts'],
                         {'success':2877,'inconclusive':0,'partial':1,'failed':1,'not_started':1})
        self.assertEqual(value['coverage.json']['summary']['state'], 'failed')
        self.assertEqual(value['execution.json']['stages']['analysis'], 'blocked_by_coverage')
        self.assertIsNone(value['analysis.json']['document_draft']);self.assertIsNone(value['diagnostics.json']['series'])
        self.assertEqual(value['verification.json']['missing_formal_fields'], list(wrapper.document.FIELDS))
        kwargs['analysis_record'] = self.kwargs['analysis_record']
        with self.assertRaisesRegex(ValueError, 'no analysis claims'):self.build(request, kwargs)

    def test_complete_coverage_alone_is_not_an_analysis_result(self):
        request, kwargs = self.fresh();without_document(request, kwargs)
        value = self.build(request, kwargs)['payloads']
        self.assertEqual(value['execution.json']['stages']['analysis'], 'not_supplied')
        self.assertEqual(value['verification.json']['status'], 'fixture_wrapper_incomplete')
        self.assertFalse(value['verification.json']['formal_ready'])

    def test_inconclusive_outcomes_preserved_without_promoting(self):
        request, kwargs = example(inconclusive=True)
        value = self.build(request, kwargs)['payloads']
        self.assertEqual(value['coverage.json']['summary']['counts']['inconclusive'], 12)
        self.assertEqual(value['coverage.json']['summary']['state'], 'complete')
        self.assertEqual(value['analysis.json']['document_draft']['decision'], 'inconclusive')
        self.assertIsNone(value['analysis.json']['document_draft']['selected_candidate'])
        self.assertFalse(value['analysis.json']['promotion_allowed'])

    def test_resealed_payload_cannot_redefine_retained_wrapper(self):
        value = self.build();value['payloads']['verification.json']['formal_ready'] = True
        value['payload_pins']['verification.json'] = supplied.pin(wrapper.v.canonical_json(value['payloads']['verification.json']))
        with self.assertRaisesRegex(ValueError, 'wrapper payload or binding'):
            wrapper.validate_fixture_wrapper(value, self.request, SCHEMA, **self.kwargs)

    def test_input_and_expectation_are_not_mutated_or_aliased(self):
        request, kwargs = self.fresh();before_request = wrapper.v.canonical_sha256(request)
        before_expected = copy.deepcopy(kwargs);value = self.build(request, kwargs)
        value['payloads']['analysis.json']['document_draft']['candidate_tables'].clear()
        value['payloads']['coverage.json']['declarations']['clusters'].clear()
        value['payloads']['execution.json']['analysis_binding']['source_descriptor']['sources'].clear()
        self.assertEqual(wrapper.v.canonical_sha256(request), before_request)
        self.assertEqual(kwargs, before_expected)


    def test_canonical_json_roundtrip_preserves_pins_and_all_five_payloads(self):
        request = wrapper.v.strict_json(wrapper.v.canonical_json(self.request))
        original = self.build()
        restored = self.build(request)
        self.assertEqual(restored['payload_pins'], original['payload_pins'])
        saved = wrapper.v.strict_json(wrapper.v.canonical_json(original))
        self.assertEqual(wrapper.validate_fixture_wrapper(saved, request, SCHEMA, **self.kwargs)['payloads'], 5)


if __name__ == '__main__':
    unittest.main()
