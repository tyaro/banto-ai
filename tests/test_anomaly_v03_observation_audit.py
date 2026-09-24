"""Small authenticated IO fixtures; expensive numeric/ledger tests are separate."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import anomaly_v03_observation_audit as audit


def encoded(value):
    return v.canonical_json(value) + b'\n'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class ConnectedAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root/'run-root'
        self.run.mkdir()
        self.saved = self.root/'saved'
        self.saved.mkdir()
        self.anchor = self.saved/'savepoint-evidence.json'
        self.plan = checkpoints.fixed_plan('a'*40, 'b'*40)
        self.plan_hash = v.canonical_sha256(self.plan)
        self.identities = self.plan['chunks'][0]['identities']
        self.stem = 'run/attempts/chunks/000/attempt-0002'
        self.files = {}
        self.put('run/metadata/plan.json', encoded(self.plan))
        binding = {'campaign_plan_sha256': self.plan_hash, 'chunk_index': 0, 'attempt': 2,
            **{k: self.plan['chunks'][0][k] for k in ('role','seed','layout','identities_sha256')}}
        self.audit_name = self.stem+'/audit/report.json'
        self.put(self.audit_name, encoded({'status': 'ledger_checks_passed', 'input': {'binding': binding}}))
        evidence = {'audit_sha256': self.files[self.audit_name]['sha256'], 'marker_sha256': 'c'*64, 'supervision_sha256': 'd'*64}
        self.chunk = {'chunk_index': 0, 'status': 'verified_complete', 'evidence': evidence,
            'attempts': [{'attempt': 1, 'status': 'failed'}, {'attempt': 2, 'status': 'verified_complete',
                'attempt_root': self.stem.removeprefix('run/attempts/'), 'evidence': evidence,
                'context': {'source_bindings': self.plan['source_bindings']}}],
            'outcome': {'worker_exit_confirmed': True, 'slots': [
                {'evaluation_id': i['evaluation_id'], 'status': 'success'} for i in self.identities]}}
        self.evidence = {'run_root': str(self.run), 'files': self.files,
            'journal_state': {'plan_sha256': self.plan_hash, 'next_unverified_chunk': None,
                'chunks': [self.chunk]+[None]*119}}
        self.results = []
        for identity in self.identities:
            directory = self.stem+'/result/payload/datasets/'+identity['dataset_id']+'/'
            hashes = {}
            # The schema's input event hash names the complete ledger, whereas
            # events.jsonl is the separate enabled-event generation input.
            dataset_files = {'observations': 'observations.jsonl', 'events': 'event-ledger.jsonl',
                'origins': 'origins.json', 'quality_mask': 'quality-mask.jsonl',
                'split': 'split-manifest.json', 'targets': 'targets.json'}
            for key, name in dataset_files.items():
                raw = encoded({'fixture': key})
                self.put(directory+name, raw)
                hashes[key] = pin(raw)['sha256']
            self.put(directory+'events.jsonl', encoded({'fixture': 'enabled-events-only'}))
            name = self.stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json'
            self.put(name, encoded({'identity': identity, 'input_hashes': hashes,
                'events': v.event_inventory(identity)}))
            self.results.append(name)
        self.seal()
        self.order = []
        def numeric(result, observations, *, expected_observation_sha256):
            self.assertEqual(hashlib.sha256(observations).hexdigest(), expected_observation_sha256)
            self.order.append(('numeric', result['identity']['evaluation_id']))
            return {'evaluation_outcome': 'success', 'score_derivation_verified': True}
        def ledger(result):
            self.order.append(('ledger', result['identity']['evaluation_id']))
            return {'status': 'ledger_checks_passed', 'score_derivation_verified': False}
        self.numeric = self.enterContext(patch.object(audit.scores, 'audit_score_derivation', side_effect=numeric))
        self.ledger = self.enterContext(patch.object(audit.ledger, 'audit_evaluation', side_effect=ledger))

    def put(self, name, raw):
        path = self.run/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.files[name] = pin(raw)

    def seal(self):
        raw = encoded(self.evidence)
        (self.saved/'evidence.json').write_bytes(raw)
        self.manifest = {'status': 'completed', 'full_120_chunks_completed': True,
            'cumulative_verified_chunks': 120, 'cumulative_verified_evaluations': 720,
            'next_unverified_chunk': None, 'formal_permission': False,
            'evidence': pin(raw), 'artifacts': {'evidence.json': pin(raw)}}
        raw = encoded(self.manifest)
        self.anchor.write_bytes(raw)
        self.digest = pin(raw)['sha256']

    def call(self, **kwargs):
        args = {'savepoint': self.anchor, 'savepoint_sha256': self.digest,
                'run_root': self.run, 'chunk_index': 0} | kwargs
        return audit.audit_completed_chunk(**args)

    def test_six_ordered_audits_failed_attempt_not_read_and_read_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = self.call()
        self.assertEqual(report['attempt'], 2)
        self.assertEqual(report['prior_attempts_not_credited'], 1)
        self.assertEqual(report['evaluations_checked'], 6)
        self.assertEqual(self.order, [(kind, i['evaluation_id']) for i in self.identities for kind in ('numeric', 'ledger')])
        self.assertTrue(report['score_derivation_verified'])
        self.assertFalse(report['evaluations'][0]['ledger_audit']['score_derivation_verified'])
        self.assertEqual(len(report['input_pins']), 20)
        self.assertEqual(report['campaign_evaluations_credited'], 0)
        for key in ('formal_permission','independent_s6_complete','promotion_allowed'):
            self.assertFalse(report[key])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_external_anchor_and_nested_evidence_hashes_required(self):
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.call(savepoint_sha256='f'*64)
        path = self.saved/'evidence.json'
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'verified_complete', b'verified_incomple', 1))
        with self.assertRaises(ValueError):
            self.call()
        self.numeric.assert_not_called()

    def test_full_event_ledger_is_authenticated_not_enabled_event_input(self):
        report = self.call()
        names = report['input_pins']
        self.assertEqual(sum(name.endswith('/event-ledger.jsonl') for name in names), 2)
        self.assertFalse(any(name.endswith('/events.jsonl') for name in names))

    def test_changed_missing_and_unpinned_evaluation_rejected(self):
        path = self.run/self.results[0]
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'"seed":', b'"Seed":', 1))
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.call()
        path.unlink()
        with self.assertRaises(ValueError):
            self.call()
        path.write_bytes(raw)
        del self.files[self.results[0]]
        self.seal()
        with self.assertRaises(KeyError):
            self.call()
        self.numeric.assert_not_called()

    def test_registered_plan_rejects_unknown_seed_and_extra_duplicate_slot(self):
        for mutation in ('seed', 'duplicate'):
            changed = copy.deepcopy(self.plan)
            if mutation == 'seed':
                changed['chunks'][0]['identities'][0]['seed'] = 7
            else:
                changed['chunks'][0]['identities'].append(changed['chunks'][0]['identities'][0])
            self.put('run/metadata/plan.json', encoded(changed))
            self.seal()
            with self.assertRaisesRegex(ValueError, 'plan changed'):
                self.call()
        self.numeric.assert_not_called()

    def test_evaluation_identity_events_and_input_hash_bindings(self):
        original = json.loads((self.run/self.results[0]).read_bytes())
        for field in ('identity', 'events', 'input_hashes'):
            changed = copy.deepcopy(original)
            if field == 'identity':
                changed[field] = self.identities[1]
            elif field == 'events':
                changed[field][0]['start_sample'] += 1
            else:
                changed[field]['observations'] = 'f'*64
            self.put(self.results[0], encoded(changed))
            self.seal()
            with self.assertRaises(ValueError):
                self.call()
        self.numeric.assert_not_called()

    def test_failure_in_numeric_or_ledger_never_returns_pass(self):
        self.numeric.side_effect = ValueError('wrong normal profile')
        with self.assertRaisesRegex(ValueError, 'wrong normal profile'):
            self.call()
        self.ledger.assert_not_called()
        self.numeric.side_effect = None
        self.numeric.return_value = {'evaluation_outcome': 'success'}
        self.ledger.side_effect = ValueError('wrong incident')
        with self.assertRaisesRegex(ValueError, 'wrong incident'):
            self.call()
        self.assertEqual(self.ledger.call_count, 1)

    def test_inconclusive_is_preserved_and_cannot_be_hidden(self):
        self.numeric.side_effect = None
        self.numeric.return_value = {'evaluation_outcome': 'inconclusive'}
        with self.assertRaisesRegex(ValueError, 'outcome differs'):
            self.call()
        self.ledger.assert_not_called()
        self.chunk['status'] = self.chunk['attempts'][-1]['status'] = 'verified_inconclusive'
        for slot in self.chunk['outcome']['slots']:
            slot['status'] = 'inconclusive'
        self.seal()
        report = self.call()
        self.assertTrue(all(r['evaluation_outcome'] == 'inconclusive' for r in report['evaluations']))
        self.assertFalse(report['promotion_allowed'])

    def test_final_failed_attempt_cannot_fall_back_to_old_verified_one(self):
        self.chunk['attempts'].append({'attempt': 3, 'status': 'failed'})
        self.seal()
        with self.assertRaisesRegex(ValueError, 'final attempt'):
            self.call()
        self.numeric.assert_not_called()

    def test_old_audit_attempt_and_pin_bindings(self):
        old = json.loads((self.run/self.audit_name).read_bytes())
        old['input']['binding']['attempt'] = 1
        self.put(self.audit_name, encoded(old))
        self.seal()
        with self.assertRaisesRegex(ValueError, 'audit pin'):
            self.call()
        self.chunk['evidence']['audit_sha256'] = self.files[self.audit_name]['sha256']
        self.seal()
        with self.assertRaisesRegex(ValueError, 'audit selection'):
            self.call()

    def test_explicit_root_size_caps_and_chunk_range(self):
        with self.assertRaisesRegex(ValueError, 'run root'):
            self.call(run_root=self.root)
        for index in (-1, 120, True):
            with self.assertRaisesRegex(ValueError, 'chunk index'):
                self.call(chunk_index=index)
        self.files[self.results[0]]['bytes'] = 33*audit.MIB
        self.seal()
        with self.assertRaisesRegex(ValueError, 'size limit'):
            self.call()
        self.numeric.assert_not_called()

    def test_nonregular_paths_and_duplicate_json_fail_closed(self):
        with self.assertRaises(ValueError):
            audit.read_pinned(self.run/'..'/'saved'/'evidence.json', self.manifest['evidence'], 8*audit.MIB)
        link = self.root/'hardlink.json'
        os.link(self.anchor, link)
        with self.assertRaisesRegex(ValueError, 'multiply-linked'):
            self.call()
        link.unlink()
        raw = (self.run/self.results[0]).read_bytes().replace(b'{', b'{"identity":null,', 1)
        self.put(self.results[0], raw)
        self.seal()
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            self.call()

    def test_cli_reports_error_with_nonzero_status_no_success_output(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = audit.main(['--savepoint', str(self.anchor), '--savepoint-sha256', 'f'*64,
                '--run-root', str(self.run), '--chunk-index', '0'])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(json.loads(err.getvalue())['status'], 'audit_failed')


if __name__ == '__main__':
    unittest.main()
