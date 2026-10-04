"""Authenticated IO tests reuse the small completed-savepoint fixture, no RNG."""
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from tests import test_anomaly_v03_observation_audit as fixtures
from banto_ai import anomaly_v03_generation_io as audit


class GenerationIOTests(unittest.TestCase):
    put = fixtures.ConnectedAuditTests.put
    seal = fixtures.ConnectedAuditTests.seal

    def setUp(self):
        fixtures.ConnectedAuditTests.setUp(self)
        def verify(role, seed, layout, captures, *, expected_sha256):
            self.assertEqual((role, seed, layout), tuple(self.plan['chunks'][0][k] for k in ('role', 'seed', 'layout')))
            self.assertEqual(set(captures), {'core', 'quality-stress'})
            for s, files in captures.items():
                self.assertEqual(set(files), set(audit.generation.FILES))
                for name, raw in files.items():
                    self.assertEqual(fixtures.pin(raw)['sha256'], expected_sha256[s][name])
            return {'status': 'generation_checks_passed', 'datasets_checked': 2}
        self.generation = self.enterContext(patch.object(audit.generation, 'audit_generation_pair', side_effect=verify))

    def call(self, **kwargs):
        return audit.audit_completed_generation(**({'savepoint': self.anchor, 'savepoint_sha256': self.digest,
            'run_root': self.run, 'chunk_index': 0} | kwargs))

    def test_only_selected_verified_attempt_and_eight_inputs_read_no_score_replay(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.call()
        self.assertEqual(result['attempt'], 2)
        self.assertEqual(result['prior_attempts_not_credited'], 1)
        self.assertEqual(len(result['input_pins']), 10)  # plan + old audit + 8 files
        self.assertEqual(result['generation_audit']['datasets_checked'], 2)
        self.assertEqual(sum(n.endswith('/events.jsonl') for n in result['input_pins']), 2)
        self.assertFalse(any('/evaluations/' in n for n in result['input_pins']))
        self.numeric.assert_not_called()
        self.ledger.assert_not_called()
        self.generation.assert_called_once()
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        for key in ('formal_permission', 'promotion_allowed', 'independent_s6_complete'):
            self.assertIs(result[key], False)
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_hash_or_missing_file_fails_before_reconstruction(self):
        path = self.run / (self.stem+'/result/payload/datasets/'+self.identities[0]['dataset_id']+'/observations.jsonl')
        path.write_bytes(path.read_bytes().replace(b'fixture', b'Fixture'))
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.call()
        path.unlink()
        with self.assertRaises(ValueError):
            self.call()
        self.generation.assert_not_called()

    test_external_anchor_and_nested_evidence_hashes_required = fixtures.ConnectedAuditTests.test_external_anchor_and_nested_evidence_hashes_required
    test_registered_plan_rejects_unknown_seed_and_extra_duplicate_slot = fixtures.ConnectedAuditTests.test_registered_plan_rejects_unknown_seed_and_extra_duplicate_slot
    test_final_failed_attempt_cannot_fall_back_to_old_verified_one = fixtures.ConnectedAuditTests.test_final_failed_attempt_cannot_fall_back_to_old_verified_one
    test_old_audit_attempt_and_pin_bindings = fixtures.ConnectedAuditTests.test_old_audit_attempt_and_pin_bindings

    def test_explicit_root_invalid_index_and_size_cap(self):
        with self.assertRaisesRegex(ValueError, 'run root'):
            self.call(run_root=self.root)
        for index in (-1, 120, True):
            with self.assertRaisesRegex(ValueError, 'chunk index'):
                self.call(chunk_index=index)
        name = self.stem+'/result/payload/datasets/'+self.identities[0]['dataset_id']+'/observations.jsonl'
        self.files[name]['bytes'] = 17 * audit.MIB
        self.seal()
        with self.assertRaisesRegex(ValueError, 'size limit'):
            self.call()
        self.generation.assert_not_called()

    def test_failure_propagates_to_cli_without_success_report(self):
        self.generation.side_effect = ValueError('different bytes')
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = audit.main(['--savepoint', str(self.anchor), '--savepoint-sha256', self.digest,
                               '--run-root', str(self.run), '--chunk-index', '0'])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(json.loads(stderr.getvalue())['status'], 'audit_failed')


if __name__ == '__main__':
    unittest.main()
