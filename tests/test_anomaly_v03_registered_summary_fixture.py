"""Invented summaries bound to registered metadata, without saved observations."""
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_registered_fixture as registered
from banto_ai import anomaly_v03_registered_summary_fixture as bridge
from banto_ai import anomaly_v03_document_fixture as document
from banto_ai import anomaly_v03_inference_audit as arithmetic
from banto_ai import anomaly_v03_consumer_input as metadata
from tests.test_anomaly_v03_registered_fixture import attempt, failed_attempt
from tests.test_anomaly_v03_producer_slice_fixture import raw_counts, compact


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RAW = (ROOT / 'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()
REGISTRY_PIN = {'bytes': len(REGISTRY_RAW), 'sha256': hashlib.sha256(REGISTRY_RAW).hexdigest()}
SUMMARY = {'counts': {'machine_recall': [2, 10], 'sensor_recall': [3, 10],
    'precision': [5, 6], 'clean_rate': [1, 3365], 'false_alert_burden': [1, 20],
    **{name: [1710, 1800] for name in arithmetic.AVAILABILITY}},
    'effective_clean_seconds': 3300, 'delay_histogram': [5, 0, 0, 0, 0],
    'profile_status': 'calibrated'}
CELLS = compact(raw_counts(SUMMARY))


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def summary_marker(identity, attempt_number):
    raw = (f"anomaly-v03-invented-summary-v1:{identity['evaluation_id']}:"
           f"attempt-{attempt_number}").encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def one_chunk():
    manifest = registered.planned_fixture(REGISTRY_PIN)
    chunk = manifest['chunks'][0]
    chunk['attempts'] = [attempt(chunk)]
    manifest['producer']['state'] = 'in_progress'
    manifest['coverage']['not_started'] = 2874
    manifest['coverage']['success'] = 6
    return manifest


def complete():
    manifest = registered.planned_fixture(REGISTRY_PIN)
    for chunk in manifest['chunks']:
        chunk['attempts'] = [attempt(chunk)]
    manifest['producer'] = {'state': 'complete', 'failure': None,
                            'worker': {'exit_confirmed': True, 'exit_code': 0}}
    manifest['coverage'] = {state: 2880 if state == 'success' else 0
                            for state in metadata.SLOT_STATES}
    return manifest


def summary_bundle(manifest):
    manifest_raw = v.canonical_json(manifest)
    rows = []
    for chunk in manifest['chunks']:
        if chunk['attempts']:
            record = chunk['attempts'][-1]['record']
            for slot in record['evaluations']:
                if slot['status'] not in ('success', 'inconclusive'):
                    continue
                rows.append({'identity': slot['identity'],
                    'attempt': record['attempt'],
                    'evaluation_marker_sha256': slot['evaluation_sha256'],
                    'summary_marker_sha256': summary_marker(slot['identity'], record['attempt']),
                    'counts': SUMMARY['counts'],
                    'effective_clean_seconds': SUMMARY['effective_clean_seconds'],
                    'delay_histogram': SUMMARY['delay_histogram'],
                    'slice_cells': CELLS})
    bundle = {'format': bridge.FORMAT, 'mode': registered.MODE,
        'invented_only': True, 'registry_pin': REGISTRY_PIN,
        'manifest_pin': pin(manifest_raw), 'rows': rows}
    return bundle


def call(manifest, bundle=None, **kwargs):
    manifest_raw = v.canonical_json(manifest)
    bundle = summary_bundle(manifest) if bundle is None else bundle
    summary_raw = v.canonical_json(bundle)
    return bridge.bind_registered_summaries(manifest_raw, REGISTRY_RAW, summary_raw,
        expected_mode=kwargs.get('mode', registered.MODE),
        expected_manifest_pin=kwargs.get('manifest_pin', pin(manifest_raw)),
        expected_registry_pin=kwargs.get('registry_pin', REGISTRY_PIN),
        expected_summary_pin=kwargs.get('summary_pin', pin(summary_raw)))


class RegisteredSummaryFixtureTests(unittest.TestCase):
    def test_all_registered_slots_project_to_invented_cluster_document_input(self):
        manifest = complete()
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = call(manifest)
        self.assertEqual(result['status'], 'fixture_summaries_bound')
        self.assertTrue(result['supplied_summary_bundle_bytes_verified'])
        self.assertTrue(result['invented_primary_and_slice_consistency_checked'])
        self.assertTrue(result['attempt_specific_summary_marker_checked'])
        self.assertFalse(result['actual_summary_origin_authenticated'])
        self.assertEqual((result['planned_chunks'], result['planned_evaluations'],
                          result['latest_result_marker_rows_checked']), (480, 2880, 2880))
        self.assertEqual(len(result['registration_map']), 40)
        self.assertEqual(result['registration_map'][0]['registered_seed'],
                         v.seed_registry()['entries'][2]['seeds'][0])
        self.assertEqual(result['registration_map'][0]['invented_cluster_id'], 'invented-00')
        cell = result['clusters'][0]['candidates'][arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(cell['counts']['machine_recall'], [24, 120])
        self.assertEqual(cell['counts']['sensor_recall'], [36, 120])
        self.assertEqual(cell['counts']['precision'], [60, 72])
        self.assertEqual(result['diagnostics'][0]['candidates'][arithmetic.CANDIDATES[0]]['core']
                         ['effective_clean_seconds'], 39600)
        self.assertEqual(result['slice_source']['clusters'][0]['candidates']
                         [arithmetic.CANDIDATES[0]]['core']['evaluations'], 12)
        for name in ('real_saved_chunk_reader_used', 'registered_observations_read',
                     'actual_worker_exit_authenticated', 'registered_input_bytes_verified',
                     'formal_permission', 'analysis_authorized', 'independent_s6_complete'):
            self.assertFalse(result[name], name)
        self.assertEqual(result['campaign_evaluations_credited'], 0)

        # Existing small-draw document fixture accepts the projected count shape.
        source = {'format': document.FORMAT, 'invented_only': True,
            'clusters': result['clusters'], 'diagnostics': result['diagnostics'],
            'draws': [list(range(40))], 'engineering_ready_assumption': False}
        schema = v.schemas(v._expected_configs())[7]
        draft = document.build_fixture_document(source, schema)
        self.assertIsNone(draft['document_draft']['status'])
        self.assertFalse(draft['formal_document_validated'])

    def test_partial_or_failed_manifest_returns_no_aggregates_and_keeps_history(self):
        value = registered.planned_fixture(REGISTRY_PIN)
        chunk = value['chunks'][0]
        chunk['attempts'] = [failed_attempt(chunk)]
        value['producer'] = {'state': 'failed',
            'failure': {'stage': 'supervision', 'reason': 'worker_exit', 'evidence_sha256': None},
            'worker': {'exit_confirmed': True, 'exit_code': 1}}
        value['coverage']['not_started'] = 2874
        value['coverage']['success'] = 5
        value['coverage']['partial'] = 1
        result = call(value)
        self.assertEqual(result['status'], 'fixture_summaries_incomplete')
        self.assertEqual(result['latest_result_marker_rows_checked'], 5)
        self.assertTrue(result['invented_primary_and_slice_consistency_checked'])
        self.assertEqual(result['failed_attempt_history'][0]['chunk_index'], 0)
        for name in ('registration_map', 'clusters', 'diagnostics', 'slice_source'):
            self.assertIsNone(result[name])
        bundle = summary_bundle(value)
        bundle['rows'] = bundle['rows'][:-1]
        with self.assertRaisesRegex(ValueError, 'exact latest result-marker summary row inventory'):
            call(value, bundle)

    def test_supplied_subset_is_checked_but_not_aggregated(self):
        value = one_chunk()
        result = call(value)
        self.assertEqual(result['latest_result_marker_rows_checked'], 6)
        self.assertEqual(result['status'], 'fixture_summaries_incomplete')
        self.assertIsNone(result['clusters'])

    def test_global_prelaunch_failure_retains_reason_and_exit_without_rows(self):
        value = registered.planned_fixture(REGISTRY_PIN)
        failure = {'stage': 'supervision', 'reason': 'worker_exit', 'evidence_sha256': None}
        value['producer'] = {'state': 'failed', 'failure': failure,
                             'worker': {'exit_confirmed': True, 'exit_code': 1}}
        result = call(value)
        self.assertEqual(result['status'], 'fixture_summaries_incomplete')
        self.assertEqual(result['coverage']['not_started'], 2880)
        self.assertEqual(result['latest_result_marker_rows_checked'], 0)
        self.assertEqual(result['failed_attempt_history'], [])
        self.assertEqual(result['producer_state'], 'failed')
        self.assertEqual(result['producer_failure'], failure)
        self.assertTrue(result['producer_worker_exit_declared'])
        self.assertIsNone(result['clusters'])

    def test_identity_marker_count_and_slice_tampering_are_rejected(self):
        manifest = one_chunk()
        base = summary_bundle(manifest)
        for kind in ('identity', 'marker', 'count', 'slice'):
            bundle = {**base, 'rows': list(base['rows'])}
            row = copy.deepcopy(bundle['rows'][0])
            bundle['rows'][0] = row
            if kind == 'identity': row['identity']['seed'] += 1
            elif kind == 'marker': row['evaluation_marker_sha256'] = 'a' * 64
            elif kind == 'count': row['counts']['machine_recall'][1] -= 1
            else: row['slice_cells']['incident'][0][1] += 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                call(manifest, bundle)

    def test_external_summary_pin_missing_row_and_formal_mode_reject(self):
        manifest = one_chunk()
        bundle = summary_bundle(manifest)
        with self.assertRaisesRegex(ValueError, 'external invented summary bytes'):
            call(manifest, bundle, summary_pin={'bytes': 1, 'sha256': '0' * 64})
        changed = {**bundle, 'rows': bundle['rows'][:-1]}
        with self.assertRaisesRegex(ValueError, 'exact latest result-marker summary row inventory'):
            call(manifest, changed)
        with self.assertRaisesRegex(ValueError, 'formal/unknown registered summary mode is closed'):
            bridge.bind_registered_summaries(b'?', b'?', b'?', expected_mode='formal',
                expected_manifest_pin=None, expected_registry_pin=None,
                expected_summary_pin=None)

    def test_latest_attempt_label_and_marker_reject_old_attempt_summary(self):
        value = one_chunk()
        chunk = value['chunks'][0]
        chunk['attempts'] = [failed_attempt(chunk), attempt(chunk, 2)]
        bundle = summary_bundle(value)
        self.assertEqual(call(value, bundle)['latest_result_marker_rows_checked'], 6)
        old = {**bundle, 'rows': list(bundle['rows'])}
        old['rows'][0] = copy.deepcopy(old['rows'][0])
        old['rows'][0]['attempt'] = 1
        old['rows'][0]['summary_marker_sha256'] = summary_marker(old['rows'][0]['identity'], 1)
        with self.assertRaisesRegex(ValueError, 'latest registered summary attempt'):
            call(value, old)
        old['rows'][0]['attempt'] = 2
        with self.assertRaisesRegex(ValueError, 'latest invented summary attempt marker'):
            call(value, old)


if __name__ == '__main__':
    unittest.main()
