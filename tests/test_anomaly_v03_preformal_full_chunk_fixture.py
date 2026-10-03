"""Full numeric/ledger reader over a wholly invented one-chunk scaffold.

The anchor explicitly describes only chunk 0. Other 119 chunks have no
payloads or authenticated coverage. Auxiliary dataset files are externally
pinned placeholders. All six evaluations are engineered inconclusive. No
registered holdout observation is generated or read.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from banto_ai import _anomaly_v03_io as io
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import anomaly_v03_saved_chunk_summary as summary
from banto_ai import anomaly_v03_scoring as producer
from tests.test_anomaly_v03_ledger_audit import zero_result
from tests.test_anomaly_v03_scoring import encode, saved_row


PREFIX = 'anomaly-v03-preformal-invented-full-chunk-'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def encoded(value):
    return v.canonical_json(value) + b'\n'


def result_for(identity, observations, hashes):
    profile = producer.fit_profiles(identity, observations,
                                    expected_sha256=hashes['observations'])
    scored = producer.score_test(profile, observations,
                                 expected_sha256=hashes['observations'])
    result = zero_result()
    result.update(identity=copy.deepcopy(identity), input_hashes=dict(hashes),
                  profiles=profile.ledger_rows(), scores=scored,
                  events=v.event_inventory(identity),
                  status={'run_status': 'complete',
                          'engineering_status': 'inconclusive',
                          'performance_status': 'not_evaluated'})
    positives = sorted((event for event in result['events']
                        if event['event_class'] in ('machine', 'sensor')),
                       key=lambda event: (event['start_ms'], event['event_id']))
    for incident, event in zip(result['incidents'], positives):
        incident.update(event_id=event['event_id'], dataset_id=event['dataset_id'])
    for item in result['metrics']['availability']:
        item['metric'].update(numerator=0, value=0.0)
    result['metrics'].update(effective_clean_seconds=0,
                             effective_clean_rate=None)
    return result


class InventedFullChunkFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = checkpoints.fixed_plan('a' * 40, 'b' * 40)
        cls.identities = cls.plan['chunks'][0]['identities']
        cls.observations, cls.observation_digest = encode([
            saved_row(equipment, sample, constant=True)
            for equipment in ('motor-01', 'conveyor-01') for sample in range(9000)])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix=PREFIX, dir=Path(__file__).resolve().parents[1] / 'artifacts')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / 'run-root'
        self.run.mkdir()
        self.saved = self.root / 'saved'
        self.saved.mkdir()
        self.files = {}
        self.stem = 'run/attempts/chunks/000/attempt-0002'
        self.put('run/metadata/plan.json', encoded(self.plan))
        binding = {'campaign_plan_sha256': v.canonical_sha256(self.plan),
                   'chunk_index': 0, 'attempt': 2,
                   **{key: self.plan['chunks'][0][key]
                      for key in ('role', 'seed', 'layout', 'identities_sha256')}}
        audit_path = self.stem + '/audit/report.json'
        self.put(audit_path, encoded({'status': 'ledger_checks_passed',
                                      'input': {'binding': binding}}))
        self.old_audit_pin = self.files[audit_path]
        self.outcomes = []
        self.evaluation_paths = []
        for identity in self.identities:
            directory = self.stem + '/result/payload/datasets/' + identity['dataset_id'] + '/'
            if identity['candidate_id'] == self.identities[0]['candidate_id']:
                dataset = {
                    'observations': self.observations,
                    'events': b''.join(v.canonical_json(e) + b'\n'
                                     for e in v.event_inventory(identity)),
                    'origins': encoded({'invented_only': True, 'kind': 'origins'}),
                    'quality_mask': encoded({'invented_only': True, 'kind': 'quality-mask'}),
                    'split': encoded({'invented_only': True, 'kind': 'split'}),
                    'targets': encoded({'invented_only': True, 'kind': 'targets'}),
                }
                for key, name in summary.reader.DATASET_INPUTS.items():
                    self.put(directory + name, dataset[key])
                hashes = {key: pin(raw)['sha256'] for key, raw in dataset.items()}
            result = result_for(identity, self.observations, hashes)
            relative = self.stem + '/result/payload/evaluations/' + identity['evaluation_id'] + '.json'
            self.put(relative, encoded(result))
            self.evaluation_paths.append(relative)
            self.outcomes.append({'evaluation_id': identity['evaluation_id'],
                                  'status': 'inconclusive'})
        self.seal()

    def put(self, relative, raw):
        path = self.run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        io._exclusive(path, raw)
        self.files[relative] = pin(raw)

    def seal(self):
        chunk_evidence = {'audit_sha256': self.old_audit_pin['sha256'],
                          'marker_sha256': 'c' * 64,
                          'supervision_sha256': 'd' * 64}
        chunk = {'chunk_index': 0, 'status': 'verified_inconclusive',
                 'evidence': chunk_evidence,
                 'attempts': [{'attempt': 1, 'status': 'failed'},
                              {'attempt': 2, 'status': 'verified_inconclusive',
                               'attempt_root': self.stem.removeprefix('run/attempts/'),
                               'evidence': chunk_evidence,
                               'context': {'source_bindings': self.plan['source_bindings']}}],
                 'outcome': {'worker_exit_confirmed': True,
                             'slots': self.outcomes}}
        evidence = {'run_root': str(self.run), 'files': self.files,
                    'fixture_scope': 'caller-declared-invented-one-chunk',
                    'registered_data_read': False,
                    'journal_state': {'plan_sha256': v.canonical_sha256(self.plan),
                                      'next_unverified_chunk': 1,
                                      'chunks': [chunk]}}
        evidence_raw = encoded(evidence)
        (self.saved / 'evidence.json').write_bytes(evidence_raw)
        self.anchor = self.saved / 'savepoint-evidence.json'
        anchor = {'format': summary.reader.PARTIAL_FIXTURE_FORMAT,
                  'status': 'partial_fixture', 'completed_chunk_index': 0,
                  'next_unverified_chunk': 1, 'formal_permission': False,
                  'registered_data_read': False,
                  'evidence': pin(evidence_raw),
                  'artifacts': {'evidence.json': pin(evidence_raw)}}
        anchor_raw = encoded(anchor)
        self.anchor.write_bytes(anchor_raw)
        self.anchor_digest = pin(anchor_raw)['sha256']

    def call(self):
        return summary.read_partial_fixture_chunk_summaries(
            self.anchor, self.anchor_digest, self.run, 0)

    def test_real_reader_rederives_six_invented_evaluations(self):
        checked = self.call()
        self.assertEqual(checked['status'], 'selected_chunk_summaries_verified')
        self.assertEqual(checked['scope'], 'one-invented-partial-fixture-chunk')
        self.assertTrue(checked['fixture_partial'])
        self.assertFalse(checked['other_chunks_authenticated'])
        self.assertFalse(checked['audit']['registered_data_read'])
        self.assertEqual(checked['evaluations_checked'], 6)
        self.assertEqual(checked['audit']['prior_attempts_not_credited'], 1)
        self.assertTrue(checked['current_observation_profile_score_audit'])
        self.assertTrue(checked['current_ledger_audit'])
        self.assertTrue(checked['primary_slice_consistency_checked'])
        self.assertEqual(len(checked['audit']['input_pins']), 20)
        self.assertTrue(all(row['evaluation_outcome'] == 'inconclusive'
                            and row['primary']['counts']['precision'] == [0, 0]
                            and row['primary']['effective_clean_seconds'] == 0
                            and row['slices']['evaluations'] == 1
                            for row in checked['evaluations']))
        self.assertFalse(checked['formal_permission'])
        self.assertEqual(checked['campaign_evaluations_credited'], 0)
        original_anchor = self.anchor.read_bytes()
        self.anchor.write_bytes(original_anchor + b' ')
        with self.assertRaisesRegex(ValueError, 'pinned file hash changed'):
            self.call()
        self.anchor.write_bytes(original_anchor)
        saved_evaluation = self.run / self.evaluation_paths[0]
        original = saved_evaluation.read_bytes()
        saved_evaluation.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'pinned file'):
            self.call()
        saved_evaluation.write_bytes(original)
        evidence_path = self.saved / 'evidence.json'
        evidence = json.loads(evidence_path.read_bytes())
        evidence['journal_state']['chunks'][0]['attempts'].append(
            {'attempt': 3, 'status': 'failed'})
        raw = encoded(evidence)
        evidence_path.write_bytes(raw)
        anchor = json.loads(self.anchor.read_bytes())
        anchor['evidence'] = anchor['artifacts']['evidence.json'] = pin(raw)
        raw = encoded(anchor)
        self.anchor.write_bytes(raw)
        self.anchor_digest = pin(raw)['sha256']
        with self.assertRaisesRegex(ValueError, 'final attempt'):
            self.call()

    def test_partial_anchor_rejects_completion_claim_and_wrong_journal_extent(self):
        anchor = json.loads(self.anchor.read_bytes())
        anchor['full_120_chunks_completed'] = True
        raw = encoded(anchor)
        self.anchor.write_bytes(raw)
        self.anchor_digest = pin(raw)['sha256']
        with self.assertRaisesRegex(ValueError, 'partial fixture anchor fields'):
            self.call()
        anchor.pop('full_120_chunks_completed')
        raw = encoded(anchor)
        self.anchor.write_bytes(raw)
        self.anchor_digest = pin(raw)['sha256']
        with self.assertRaisesRegex(ValueError, 'completed savepoint required'):
            summary.read_chunk_summaries(self.anchor, self.anchor_digest, self.run, 0,
                                         expected_mode='fixture')
        evidence_path = self.saved / 'evidence.json'
        evidence = json.loads(evidence_path.read_bytes())
        evidence['journal_state']['chunks'].append(None)
        raw = encoded(evidence)
        evidence_path.write_bytes(raw)
        anchor['evidence'] = anchor['artifacts']['evidence.json'] = pin(raw)
        raw = encoded(anchor)
        self.anchor.write_bytes(raw)
        self.anchor_digest = pin(raw)['sha256']
        with self.assertRaisesRegex(ValueError, 'one partial fixture chunk'):
            self.call()


if __name__ == '__main__':
    unittest.main()
