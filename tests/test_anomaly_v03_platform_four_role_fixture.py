"""Stop-on-failure and saved-byte boundaries of the preformal four-role chain."""
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_platform_four_role_fixture as chain


PIN = {'bytes': 2, 'sha256': chain.observed._pin(b'{}')['sha256']}
REVISION = 'a' * 40
FILES = {name: b'{}' for name in chain.INPUT_NAMES}


def _request_boundary_on_this_platform():
    # These two tests exercise role ordering with mocked children. The real
    # request validator requires Windows paths and is covered separately.
    if sys.platform == 'win32':
        return nullcontext()
    return patch.object(chain.analysis, '_request')


def _audit_request_boundary_on_this_platform():
    if sys.platform == 'win32':
        return nullcontext()
    return patch.object(chain.audit, '_request')


class FourRoleFixtureTests(unittest.TestCase):
    def test_closed_mode_rejected_before_receipt_or_join_io(self):
        with patch.object(chain.io, '_local_parent', side_effect=AssertionError('receipt IO')):
            for mode in ('formal', 'holdout', 'engineering-dev-smoke', True):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    chain.run_chain(expected_mode=mode, join_root=None,
                        expected_join_receipt_pin=None, expected_revision=None,
                        receipt_name=None)

    def test_analysis_failure_stops_audit_and_publication(self):
        with tempfile.TemporaryDirectory(prefix='banto-four-role-analysis-') as directory:
            root = Path(directory).resolve()
            failed = {'check_directory': str(root / 'analysis'), 'result_pin': PIN,
                      'status': 'failed', 'resource_budget_passed': False,
                      'worker_exit_confirmed': False, 'fixture_inference_performed': False}
            with patch.object(chain, '_reference_document', return_value=b'{}'), \
                 patch.object(chain, '_saved_result'), \
                 _request_boundary_on_this_platform(), \
                 patch.object(chain.numeric, 'calculate_fixture', return_value=failed) as analysis, \
                 patch.object(chain.numeric, 'audit_fixture', side_effect=AssertionError('audit after failed analysis')), \
                 patch.object(chain.publication, 'publish_with_evidence', side_effect=AssertionError('publication after failed analysis')):
                state = {'identities': {}}
                with self.assertRaisesRegex(ValueError, 'owned analysis failed'):
                    chain._run_roles(root, FILES, REVISION, state)
            self.assertEqual(analysis.call_count, 1)
            self.assertEqual(state['analysis']['result_pin'], PIN)
            self.assertEqual(state['analysis']['status'], 'failed')
            self.assertTrue((root / 'reference' / 'document.json').is_file())

    def test_audit_failure_stops_writer_and_reader(self):
        with tempfile.TemporaryDirectory(prefix='banto-four-role-audit-') as directory:
            root = Path(directory).resolve()
            verified = {'check_directory': str(root / 'analysis'), 'result_pin': PIN,
                        'evidence_pin': PIN, 'status': 'verified',
                        'resource_budget_passed': True, 'worker_exit_confirmed': True,
                        'fixture_inference_performed': True}
            failed = {'check_directory': str(root / 'audit'), 'result_pin': PIN,
                      'status': 'failed', 'resource_budget_passed': False,
                      'worker_exit_confirmed': True, 'fixture_numerical_audit_performed': False,
                      'fixture_slice_audit_performed': False}
            identity = {'pid': 1, 'start_token': 'token', 'invocation_id': 'invocation',
                        'evidence_pin': PIN}
            with patch.object(chain, '_reference_document', return_value=b'{}'), \
                 patch.object(chain, '_saved_result'), \
                 _request_boundary_on_this_platform(), \
                 _audit_request_boundary_on_this_platform(), \
                 patch.object(chain, '_role_identity', return_value=identity), \
                 patch.object(chain.numeric, 'calculate_fixture', return_value=verified) as analysis, \
                 patch.object(chain.numeric, 'audit_fixture', return_value=failed) as audit, \
                 patch.object(chain.publication, 'publish_with_evidence', side_effect=AssertionError('publication after failed audit')):
                state = {'identities': {}}
                with self.assertRaisesRegex(ValueError, 'owned audit failed'):
                    chain._run_roles(root, FILES, REVISION, state)
            self.assertEqual((analysis.call_count, audit.call_count), (1, 1))
            self.assertEqual(state['audit']['result_pin'], PIN)
            self.assertEqual(state['audit']['status'], 'failed')
            self.assertFalse((root / 'publication').exists())

    def test_postflight_failure_is_not_labeled_complete(self):
        with tempfile.TemporaryDirectory(prefix='banto-four-role-postflight-') as directory:
            parent = Path(directory).resolve()
            changed = {'bytes': 2, 'sha256': 'f' * 64}
            with patch.object(chain, '_git_source', side_effect=[PIN, changed]), \
                 patch.object(chain, '_join_projection', return_value=(FILES, {'join_revision': REVISION})), \
                 patch.object(chain, '_run_roles'):
                result = chain.run_chain(expected_mode='fixture', join_root=parent / 'old-join',
                    expected_join_receipt_pin=PIN, expected_revision=REVISION,
                    receipt_name='attempt', receipt_parent=parent)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['stage'], 'postflight')
            self.assertIn('chain source changed', result['detail'])

    def test_failure_receipt_keeps_all_formal_flags_closed(self):
        with tempfile.TemporaryDirectory(prefix='banto-four-role-result-') as directory:
            parent = Path(directory).resolve()
            with patch.object(chain, '_git_source', return_value=PIN), \
                 patch.object(chain, '_join_projection', return_value=(FILES, {'join_revision': REVISION})), \
                 patch.object(chain, '_run_roles', side_effect=ValueError('trial stopped')):
                result = chain.run_chain(expected_mode='fixture', join_root=parent / 'old-join',
                    expected_join_receipt_pin=PIN, expected_revision=REVISION,
                    receipt_name='attempt', receipt_parent=parent)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['reason'], 'four_role_fixture_rejected')
            self.assertFalse(result['formal_permission'])
            self.assertFalse(result['owned_producer_executed'])
            self.assertFalse(result['registered_data_read'])
            self.assertEqual(chain.v.strict_json((parent / 'attempt' / 'result.json').read_bytes())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
