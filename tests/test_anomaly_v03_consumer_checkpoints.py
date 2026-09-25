"""Invented checkpoint/manifest metadata only; no observations or score replay."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as p
from banto_ai import anomaly_v03_chunk_contract as contract
from banto_ai import anomaly_v03_consumer_checkpoints as adapter
from banto_ai import anomaly_v03_consumer_input as consumer
from banto_ai import anomaly_v03_engineering_contract as legacy
from banto_ai import anomaly_v03_materializer as materializer
from tests.test_anomaly_v03_checkpoints import JournalFixture


def digest(text):
    return v.canonical_sha256(text)


def manifest(fixture, index, attempt):
    value = contract.new_manifest(fixture.plan, index, attempt)
    value.update(state='complete', runtime=copy.deepcopy(fixture.context['runtime']),
        source={'revision': fixture.plan['source_bindings']['producer_revision'],
                'sources': [{'path': 'src/invented.py', 'raw_sha256': digest('source'), 'byte_count': 1}]})
    for dataset in value['datasets']:
        ident = dataset['identity']['dataset_id']
        dataset['files'] = [{'path': 'datasets/' + ident + '/' + name, 'bytes': 1,
                             'sha256': digest(ident + name)} for name in materializer.DATASET_FILES]
    for row in value['slots']:
        ident = row['identity']
        row.update(status='success',
            input_hashes={key: digest(ident['dataset_id'] + name) for key, name in materializer.INPUT_FILES.items()},
            evaluation={'path': 'evaluations/' + ident['evaluation_id'] + '.json',
                        'bytes': 1, 'sha256': digest(ident['evaluation_id'])})
    value['resources']['payload_bytes'] = 2 * len(materializer.DATASET_FILES) + 6
    legacy.refresh_coverage(value)
    return value


class ConsumerCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f = JournalFixture()
        entries = []
        for index in range(120):
            attempt = 1
            if index == 119:
                f.add('running', chunk=index)
                f.add('failed', chunk=index, reason='resource_limit')
                entries.append({'chunk_index': index, 'attempt': 1, 'manifest': None})
                attempt = 2
            f.complete(chunk=index, attempt=attempt)
            entries.append({'chunk_index': index, 'attempt': attempt, 'manifest': manifest(f, index, attempt)})
        cls.baseline = (f, entries)

    def setUp(self):
        self.f, self.entries = copy.deepcopy(self.baseline)

    def run_adapter(self, **overrides):
        args = dict(expected_mode=adapter.MODE, expected_plan_sha256=self.f.plan_hash,
                    expected_record_count=len(self.f.records), expected_head_sha256=self.f.head,
                    expected_manifests_sha256=v.canonical_sha256(self.entries))
        return adapter.adapt_completed_journal(self.f.plan, self.f.records, self.entries, **(args | overrides))

    def known_failed(self, complete=False):
        value = manifest(self.f, 119, 1)
        if not complete:
            value.update(state='failed', failure={'stage': 'evaluation', 'reason': 'exception'})
            for row in value['slots'][1:]:
                row.update(status='not_started', input_hashes=None, evaluation=None)
            value['slots'][1].update(status='failed', input_hashes=copy.deepcopy(value['slots'][0]['input_hashes']))
            legacy.refresh_coverage(value)
        self.entries[-2]['manifest'] = value
        return value

    def test_complete_362_record_campaign_selects_latest_without_synthesizing_producer_marker(self):
        out = self.run_adapter()
        self.assertEqual((out['bindings']['record_count'], out['attempt_count']), (362, 121))
        self.assertEqual(out['coverage'], dict.fromkeys(consumer.SLOT_STATES, 0) | {'success': 720})
        self.assertEqual([x['selected_attempt'] for x in out['chunks']], [1] * 119 + [2])
        self.assertEqual(out['declared_complete_chunks'], 120)
        self.assertNotIn('producer', out)
        self.assertTrue(out['journal_declares_coverage_complete'])
        for key in ('input_bytes_verified', 'publication_verified', 'producer_exit_verified',
                    'source_runtime_accepted', 'result_trusted', 'campaign_completed', 'execution_authorized',
                    'analysis_authorized', 'formal_permission', 'promotion_allowed', 'independent_s6_complete'):
            self.assertIs(out[key], False)
        self.assertEqual(out['performance_status'], 'not_evaluated')
        self.assertIsNone(out['selected_candidate'])
        slots = out['chunks'][-1]['attempts'][-1]['evaluations']
        self.assertEqual(slots[0]['input_hashes'], self.entries[-1]['manifest']['slots'][0]['input_hashes'])
        self.assertEqual(slots[0]['evaluation_sha256'], self.entries[-1]['manifest']['slots'][0]['evaluation']['sha256'])

    def test_missing_failure_manifest_is_unknown_and_exact_failure_record_is_retained(self):
        out = self.run_adapter()
        failed = out['chunks'][-1]['attempts'][0]
        self.assertIsNone(failed['evaluations'])
        self.assertEqual(failed['evaluation_detail'], 'unreported')
        self.assertEqual(out['failed_attempt_history'][0]['terminal_record'], self.f.records[-4])
        self.assertEqual(out['failed_attempt_history'][0]['terminal_record_sha256'], p.record_hash(self.f.records[-4]))

    def test_known_partial_failure_retains_success_prefix_and_independent_failure_reasons(self):
        self.known_failed()
        out = self.run_adapter()
        failed = out['chunks'][-1]['attempts'][0]
        self.assertEqual([r['status'] for r in failed['evaluations']], ['success', 'failed'] + ['not_started'] * 4)
        self.assertEqual(failed['reason'], 'resource_limit')
        self.assertEqual(failed['manifest_failure'], {'stage': 'evaluation', 'reason': 'exception'})
        self.assertEqual(out['coverage']['success'], 720)

    def test_failed_supervision_after_complete_manifest_does_not_erase_evidence(self):
        self.known_failed(complete=True)
        evidence = {'marker_sha256': digest('old marker'), 'supervision_sha256': digest('old supervision'),
                    'audit_sha256': None}
        self.f.records[-4]['evidence'] = evidence
        self.f.rechain()
        out = self.run_adapter()
        failed = out['chunks'][-1]['attempts'][0]
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['manifest_state'], 'complete')
        self.assertEqual(failed['evidence'], evidence)
        self.assertEqual(len(out['failed_attempt_history']), 1)

    def test_inconclusive_is_complete_but_never_promoted_to_success(self):
        self.entries[-1]['manifest']['slots'][0]['status'] = 'inconclusive'
        legacy.refresh_coverage(self.entries[-1]['manifest'])
        self.f.records[-1]['status'] = 'verified_inconclusive'
        self.f.records[-1]['outcome']['slots'][0]['status'] = 'inconclusive'
        self.f.rechain()
        out = self.run_adapter()
        self.assertEqual((out['coverage']['success'], out['coverage']['inconclusive']), (719, 1))
        self.assertEqual(out['chunks'][-1]['attempts'][-1]['evaluations'][0]['profile_status'], 'inconclusive')
        self.assertEqual(out['profile_status_source'], 'manifest_slot_status_only')

    def test_formal_and_fixture_rejected_before_any_journal_or_digest_processing(self):
        with patch.object(p, 'reduce_journal', side_effect=AssertionError('journal touched')), \
             patch.object(v, 'canonical_sha256', side_effect=AssertionError('digest touched')):
            for mode in ('formal', 'holdout', 'fixture', None, True):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    adapter.adapt_completed_journal(None, None, None, expected_mode=mode,
                        expected_plan_sha256=None, expected_record_count=None,
                        expected_head_sha256=None, expected_manifests_sha256=None)

    def test_external_plan_head_count_and_manifest_pins_are_required(self):
        for overrides in ({'expected_plan_sha256': '0' * 64}, {'expected_head_sha256': '0' * 64},
                          {'expected_record_count': 360}, {'expected_record_count': True},
                          {'expected_manifests_sha256': '0' * 64}, {'expected_manifests_sha256': None}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.run_adapter(**overrides)

    def test_omitted_or_reordered_attempts_not_silently_selected(self):
        for change in ('omitted', 'reordered', 'duplicate', 'extra_key', 'bool_attempt'):
            with self.subTest(change=change):
                entries = copy.deepcopy(self.entries)
                if change == 'omitted': self.entries.pop(-2)
                if change == 'reordered': self.entries[-2:] = self.entries[-2:][::-1]
                if change == 'duplicate': self.entries[-2] = copy.deepcopy(self.entries[-1])
                if change == 'extra_key': self.entries[0]['trusted'] = True
                if change == 'bool_attempt': self.entries[0]['attempt'] = True
                with self.assertRaises(ValueError): self.run_adapter()
                self.entries = entries

    def test_corrupted_journal_chain_or_incomplete_coverage_rejected(self):
        self.f.records[-1]['previous_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.run_adapter()
        self.f.rechain()
        self.f.records.pop()
        with self.assertRaisesRegex(ValueError, 'completed checkpoint'): self.run_adapter()

    def test_verified_manifest_mandatory_even_with_published_journal(self):
        self.entries[0]['manifest'] = None
        with self.assertRaisesRegex(ValueError, 'missing manifest'): self.run_adapter()

    def test_manifest_attempt_identity_source_and_runtime_must_match_journal(self):
        original = copy.deepcopy(self.entries[0]['manifest'])
        for change in ('attempt', 'identity', 'source', 'runtime', 'planned'):
            with self.subTest(change=change):
                value = self.entries[0]['manifest'] = copy.deepcopy(original)
                if change == 'attempt': value['plan']['binding']['attempt'] = 2
                if change == 'identity': value['slots'][0]['identity']['role'] = 'holdout'
                if change == 'source': value['source']['revision'] = 'f' * 40
                if change == 'runtime': value['runtime']['os_ubr'] += 1
                if change == 'planned': self.entries[0]['manifest'] = contract.new_manifest(self.f.plan, 0, 1)
                with self.assertRaises(ValueError): self.run_adapter()

    def test_slot_outcome_disagreement_with_journal_rejected(self):
        value = self.entries[0]['manifest']
        value['slots'][0]['status'] = 'inconclusive'
        legacy.refresh_coverage(value)
        with self.assertRaisesRegex(ValueError, 'outcome mismatch'): self.run_adapter()

    def test_changed_input_hash_or_missing_sixth_pin_rejected(self):
        first = self.entries[0]['manifest']['slots'][0]['input_hashes']
        first['observations'] = '0' * 64
        with self.assertRaises(ValueError): self.run_adapter()
        del first['targets']
        with self.assertRaises(ValueError): self.run_adapter()

    def test_individually_consistent_retry_manifest_cannot_change_known_input_bytes(self):
        value = self.known_failed(complete=True)
        dataset = value['datasets'][0]
        for entry in dataset['files']:
            if entry['path'].endswith('/observations.jsonl'): entry['sha256'] = '0' * 64
        for row in value['slots'][:3]: row['input_hashes']['observations'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'retry input pins differ'): self.run_adapter()

    def test_returned_data_is_independent_and_no_io_or_computation_occurs(self):
        before = v.canonical_sha256([self.f.plan, self.f.records, self.entries])
        with ExitStack() as stack:
            for target in ('builtins.open', 'io.open', 'subprocess.Popen',
                           'banto_ai.anomaly_v03_materializer.materialize_pair',
                           'banto_ai.anomaly_v03_chunk_contract.audit_chunk_payloads'):
                stack.enter_context(patch(target, side_effect=AssertionError('forbidden: ' + target)))
            stack.enter_context(patch.object(Path, 'read_bytes', side_effect=AssertionError('file read')))
            out = self.run_adapter()
        self.assertEqual(json.loads(json.dumps(out)), out)
        out['chunks'][0]['identities'].clear()
        out['failed_attempt_history'][0]['terminal_record']['context'].clear()
        self.assertEqual(v.canonical_sha256([self.f.plan, self.f.records, self.entries]), before)


if __name__ == '__main__':
    unittest.main()
