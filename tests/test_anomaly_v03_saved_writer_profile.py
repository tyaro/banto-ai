"""Timing evidence survives stops without dropping publication checks."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_saved_writer_profile as profile
from banto_ai import anomaly_v03_saved_row_document_publication as publication
from tests import test_anomaly_v03_saved_row_document_publication as payload_tests


class JournalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'phases'
        self.journal = profile.Journal(self.root)

    def test_live_span_keeps_last_phase_without_completion_claim(self):
        with self.journal.phase('writer'):
            with self.journal.phase('slice_mapping'):
                saved = profile.summarize(self.root)
                self.assertEqual(saved['open_phases'], ['writer', 'writer.slice_mapping'])
                self.assertEqual(saved['spans'], [])
        saved = profile.summarize(self.root)
        self.assertEqual(saved['open_phases'], [])
        self.assertEqual([row['status'] for row in saved['spans']], ['end', 'end'])

    def test_failed_operation_is_persisted_and_exception_propagates(self):
        with self.assertRaisesRegex(ValueError, 'fixture stop'):
            with self.journal.phase('writer'):
                with self.journal.phase('source'):
                    raise ValueError('fixture stop')
        saved = profile.summarize(self.root)
        self.assertEqual(saved['open_phases'], [])
        self.assertEqual([row['status'] for row in saved['spans']], ['failed', 'failed'])

    def test_noncontiguous_sequence_rejects(self):
        with self.journal.phase('writer'):
            pass
        (self.root / '000.json').rename(self.root / '099.json')
        with self.assertRaisesRegex(ValueError, 'sequence inventory'):
            profile.summarize(self.root)

    def test_changed_closure_or_backwards_time_rejects(self):
        with self.journal.phase('writer'):
            pass
        path = self.root / '001.json'
        original = json.loads(path.read_bytes())
        for update, message in (({'phase': 'other'}, 'span closure'),
                                ({'elapsed_seconds': -1}, 'event binding')):
            path.write_bytes(publication.io.json_bytes({**original, **update}))
            with self.assertRaisesRegex(ValueError, message):
                profile.summarize(self.root)

    def test_journal_bound_stops_before_operation(self):
        self.journal.count = profile.EVENT_COUNT
        entered = False
        with self.assertRaisesRegex(ValueError, 'journal bound'):
            with self.journal.phase('writer'):
                entered = True
        self.assertFalse(entered)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_journal_is_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            profile.Journal(self.root)


class SharedExecutionTests(unittest.TestCase):
    setUpClass = classmethod(payload_tests.PublicationPayloadTests.setUpClass.__func__)
    setUp = payload_tests.PublicationPayloadTests.setUp

    def test_observation_runs_all_four_retained_audits_and_keeps_payloads(self):
        journal = profile.Journal(self.root / 'phases')
        request = {**self.request, 'role': 'writer', 'source_pins': {}}
        with patch.object(publication, '_source_recheck') as source, \
             patch.object(publication.io, '_local_parent', side_effect=lambda path:path), \
             patch.object(publication.chain.slice_bridge.independent, 'audit_precomputed_slices',
                          wraps=publication.chain.slice_bridge.independent.audit_precomputed_slices) as audit:
            result, files = publication._perform(request, phase=journal.phase)
        self.assertEqual(source.call_count, 4)
        self.assertEqual(audit.call_count, 4)
        for name, raw in files.items():
            self.assertEqual(raw, (self.root / name).read_bytes() + b'\n')
        self.assertTrue((self.root / 'published/.complete').exists())
        self.assertEqual(result['native_acceptance'], 'not_completed')
        saved = profile.summarize(self.root / 'phases')
        self.assertEqual(saved['open_phases'], [])
        self.assertEqual(sum(row['phase'].endswith('independent_count_audit')
                             for row in saved['spans']), 4)

    def test_phase_failure_blocks_publication_and_preserves_failure(self):
        journal = profile.Journal(self.root / 'phases')
        @contextmanager
        def stop(name):
            with journal.phase(name):
                if name == 'primary_mapping':
                    raise ValueError('timing write failed')
                yield
        with patch.object(publication, '_source_recheck'), \
             patch.object(publication.io, 'publish_local_result') as publish:
            with self.assertRaisesRegex(ValueError, 'timing write failed'):
                publication._perform({**self.request, 'role': 'writer', 'source_pins': {}}, phase=stop)
        publish.assert_not_called()
        self.assertFalse((self.root / 'published').exists())
        self.assertEqual(profile.summarize(self.root / 'phases')['spans'][-1]['status'], 'failed')

    def test_wrong_old_pin_or_current_revision_rejects_before_new_root(self):
        target = self.root.parent / 'trial-new'
        historical = {**self.request, 'format': publication.FORMAT + '-request',
                      'role': 'writer', 'source_pins': {}, 'payload_pins': {}}
        (self.root / 'writer').mkdir()
        raw = publication.io.json_bytes(historical)
        (self.root / 'writer/request.json').write_bytes(raw)
        with self.assertRaises(ValueError):
            profile.run(source_root=self.root, expected_request_pin=publication._pin(b'wrong'),
                        expected_worker_revision='b'*40, receipt_name=target.name)
        self.assertFalse(target.exists())
        with patch.object(profile, '_source', side_effect=ValueError('clean expected HEAD')):
            with self.assertRaisesRegex(ValueError, 'clean expected HEAD'):
                profile.run(source_root=self.root, expected_request_pin=publication._pin(raw),
                            expected_worker_revision='b'*40, receipt_name=target.name)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
