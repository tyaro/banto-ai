"""Invented five-child handoff, failure stop, and identity composition."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_platform_five_role_fixture as chain


PIN = {'bytes': 2, 'sha256': chain.observed._pin(b'{}')['sha256']}
REVISION = 'a' * 40
FILES = {name: b'{}' for name in chain.four.INPUT_NAMES}


class FakeBudget:
    def __init__(self, root, value=None, *, publication_roots=()):
        self.root = root
        self._thread = None
        self.roles = {}

    def start(self):
        self._thread = object()
        return self

    def checkpoint(self, phase=None):
        return None

    def record_role(self, role, status, result_pin=None, worker_pid=None, exit_confirmed=None):
        self.roles[role] = exit_confirmed

    def close(self):
        return {'passed': True, 'stop_reason': None,
                'caller_reported_all_five_exits':
                    set(self.roles) == {'producer', 'analysis', 'audit', 'writer', 'reader'} and
                    all(self.roles.values())}


def identity(number):
    return {'pid': number, 'start_token': f'start-{number}',
            'invocation_id': f'invocation-{number}', 'evidence_pin': PIN}


class FiveRoleFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-five-role-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.parent = self.artifacts / 'five-role'
        self.join = self.artifacts / 'anomaly-v03-preformal-join-budget-fixture'

    def call_chain(self, **options):
        with patch.object(chain, 'ROOT', self.root):
            return chain.run_chain(expected_mode='fixture', join_root=self.join,
                expected_join_receipt_pin=PIN, expected_revision=REVISION,
                receipt_name='attempt', receipt_parent=self.parent, **options)

    def test_closed_mode_rejected_before_receipt_io(self):
        with patch.object(chain.io, '_local_parent', side_effect=AssertionError('receipt IO')):
            for mode in ('formal', 'holdout', 'engineering-dev-smoke', True):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    chain.run_chain(expected_mode=mode, join_root=None,
                        expected_join_receipt_pin=None, expected_revision=None,
                        receipt_name=None)

    def test_failed_producer_retains_pin_and_stops_all_consumers(self):
        failed = {'check_directory': str(self.parent / 'attempt' / 'producer'),
                  'result_pin': PIN, 'status': 'failed',
                  'worker_exit_confirmed': True,
                  'owned_producer_join_executed': False,
                  'real_producer_executed': False}
        with patch.object(chain, '_git_sources', return_value={'source': PIN}), \
             patch.object(chain, '_external_archive', return_value=(self.join / 'invented-inputs.zip',
                 PIN, PIN, {'input_scope': 'invented'})), \
             patch.object(chain.chain_budget, 'PreformalChainBudget', FakeBudget), \
             patch.object(chain.producer, 'join_with_evidence', return_value=failed) as producer, \
             patch.object(chain.four, '_saved_result'), \
             patch.object(chain.four, '_run_roles', side_effect=AssertionError('consumer after failed producer')):
            result = self.call_chain()
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['producer']['result_pin'], PIN)
        self.assertEqual(result['producer']['status'], 'failed')
        self.assertFalse(result['owned_producer_join_executed'])
        self.assertTrue(result['combined_resource_budget_measured'])
        self.assertFalse(result['combined_resource_budget_passed'])
        self.assertFalse(result['formal_permission'])

    def test_five_distinct_owned_identities_include_fresh_producer(self):
        reader = object()
        verified = {'check_directory': str(self.parent / 'attempt' / 'producer'),
                    'result_pin': PIN, 'status': 'verified',
                    'worker_exit_confirmed': True,
                    'owned_producer_join_executed': True,
                    'real_producer_executed': False,
                    'projection_pins': {name: PIN for name in chain.four.INPUT_NAMES},
                    'bound_pin': PIN, 'stdout_pin': PIN}
        def four_roles(target, files, revision, state, *, resource_budget=None,
                       role_profiles=None):
            self.assertEqual(files, FILES)
            self.assertEqual(revision, REVISION)
            state['analysis'] = {'status': 'verified', 'result_pin': PIN}
            state['audit'] = {'status': 'verified', 'result_pin': PIN}
            state['publication'] = {'status': 'verified', 'result_pin': PIN}
            state['identities'] = {name: identity(index) for index, name in
                enumerate(('analysis', 'audit', 'writer', 'reader'), 2)}
            for name in ('analysis', 'audit', 'writer', 'reader'):
                resource_budget.record_role(name, 'verified', result_pin=PIN,
                                            exit_confirmed=True)
        with patch.object(chain, '_git_sources', return_value={'source': PIN}) as source, \
             patch.object(chain, '_external_archive', return_value=(self.join / 'invented-inputs.zip',
                 PIN, PIN, {'input_scope': 'invented'})), \
             patch.object(chain.chain_budget, 'PreformalChainBudget', FakeBudget), \
             patch.object(chain.producer, 'join_with_evidence', return_value=verified) as producer, \
             patch.object(chain.four, '_saved_result'), \
             patch.object(chain, '_producer_identity', return_value=identity(1)), \
             patch.object(chain, '_fresh_projection', return_value=FILES), \
             patch.object(chain.four, '_run_roles', side_effect=four_roles) as consumers, \
             patch.object(chain.four, '_pin_file'):
            result = self.call_chain(git_reader=reader)
        self.assertEqual([call.kwargs for call in source.call_args_list], [
            {'git_reader': reader, 'git_call_prefix': 'child-chain-source-0-'},
            {'git_reader': reader, 'git_call_prefix': 'child-chain-source-1-'}])
        self.assertEqual((producer.call_count, consumers.call_count), (1, 1))
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['stage'], 'complete')
        self.assertEqual(set(result['identities']),
                         {'producer', 'analysis', 'audit', 'writer', 'reader'})
        self.assertTrue(result['combined_resource_budget_measured'])
        self.assertTrue(result['combined_resource_budget_passed'])
        self.assertTrue(result['five_role_budget_closure_passed'])
        self.assertFalse(result['real_producer_executed'])
        self.assertFalse(result['formal_permission'])

    def test_bad_external_candidate_set_fails_before_producer_with_receipt(self):
        with patch.object(chain.chain_budget, 'PreformalChainBudget', FakeBudget), \
             patch.object(chain.role_profiles, 'load_pinned_candidate_set',
                          side_effect=ValueError('candidate set pin changed')) as load, \
             patch.object(chain.producer, 'join_with_evidence',
                          side_effect=AssertionError('producer launched')) as producer, \
             patch.object(chain, '_external_archive',
                          side_effect=AssertionError('archive read')):
            result = self.call_chain(
                candidate_set_path=self.artifacts / 'external' / 'candidate-set.json',
                expected_candidate_set_pin=PIN)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(producer.call_count, 0)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stage'], 'preflight')
        self.assertTrue(result['profile_required'])
        self.assertFalse(result['before_work_profile_enforcement'])
        self.assertFalse(result['formal_permission'])
        self.assertEqual(chain.v.strict_json((self.parent / 'attempt' /
                                              'result.json').read_bytes())['status'], 'failed')
        self.assertFalse((self.parent / 'attempt' / 'producer').exists())

    def test_duplicate_process_identity_rejects_chain(self):
        state = {'identities': {name: identity(index) for index, name in
                                enumerate(('producer', 'analysis', 'audit', 'writer', 'reader'), 1)}}
        state['identities']['reader'] = dict(state['identities']['writer'])
        with self.assertRaisesRegex(ValueError, 'five distinct owned process'):
            chain._check_five_identities(state)

    def test_unreaped_owner_survives_outer_receipt_failure(self):
        owner = chain.four.analysis.supervisor.UnreapedWorker(object(),
            {'worker_exit_confirmed': False})
        with patch.object(chain, '_git_sources', return_value={'source': PIN}), \
             patch.object(chain, '_external_archive', return_value=(
                 self.join / 'invented-inputs.zip', PIN, PIN, {})), \
             patch.object(chain.chain_budget, 'PreformalChainBudget', FakeBudget), \
             patch.object(chain.producer, 'join_with_evidence', side_effect=owner), \
             patch.object(chain, '_save', side_effect=OSError('receipt write failed')):
            with self.assertRaises(chain.four.analysis.supervisor.UnreapedWorker) as caught:
                self.call_chain()
        self.assertIs(caught.exception, owner)
        self.assertIsInstance(owner.outer_receipt_error, OSError)


if __name__ == '__main__':
    unittest.main()
