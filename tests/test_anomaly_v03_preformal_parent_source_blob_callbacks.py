"""Replacement blob readers retain pin comparisons and stop without fallback."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole


REVISION = 'b' * 40
DOCUMENT = ('src/first.py', 'src/second.py')
GENERATION = (*DOCUMENT, 'src/third.py')
RAW = {name: (name + '\n').encode() for name in GENERATION}


class ParentSourceBlobCallbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-blob-callback-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'src').mkdir()
        for name, raw in RAW.items():
            (self.root / name).write_bytes(raw)
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(whole, 'ROOT', self.root))
        stack.enter_context(patch.object(whole.document, 'ROOT', self.root))
        stack.enter_context(patch.object(whole, 'SOURCE_NAMES', GENERATION))
        stack.enter_context(patch.object(whole.document, 'SOURCE_NAMES', DOCUMENT))
        self.bare_git = stack.enter_context(patch.object(
            whole.generated.subprocess, 'check_output',
            side_effect=AssertionError('unexpected bare Git fallback')))
        self.identity = Mock(return_value={'head': REVISION.encode() + b'\n', 'status': b''})

    def read(self, **entry):
        self.assertEqual(entry['revision'], REVISION)
        self.assertEqual(entry['expected_output_pin'], whole.generated.copied._pin(RAW[entry['source_path']]))
        return RAW[entry['source_path']]

    def source(self, callback):
        return whole._source(REVISION, git_identity=self.identity, git_blob=callback)

    def test_one_callback_replaces_both_source_loops_with_exact_path_revision_pin(self):
        callback = Mock(side_effect=self.read)
        pins = self.source(callback)
        self.assertEqual(pins, {name: whole.generated.copied._pin(raw) for name, raw in RAW.items()})
        self.assertEqual([row.kwargs['source_path'] for row in callback.call_args_list],
                         list(DOCUMENT + GENERATION))
        self.identity.assert_called_once_with()
        self.bare_git.assert_not_called()

    def test_default_reader_preserves_head_clean_and_each_blob_check(self):
        calls = []

        def git(argv, **options):
            self.assertEqual(argv[:3], ['git', '-C', str(self.root)])
            self.assertEqual(options['timeout'], 10)
            calls.append(argv[3:])
            if argv[3:] == ['rev-parse', 'HEAD']:
                return REVISION.encode() + b'\n'
            if argv[3:] == ['status', '--porcelain']:
                return b''
            self.assertEqual(argv[3], 'show')
            revision, name = argv[4].split(':', 1)
            self.assertEqual(revision, REVISION)
            return RAW[name]

        self.bare_git.side_effect = git
        pins = whole._source(REVISION)
        self.assertEqual(set(pins), set(GENERATION))
        self.assertEqual(calls, [['rev-parse', 'HEAD'], ['status', '--porcelain']] +
                         [['show', REVISION + ':' + name] for name in DOCUMENT + GENERATION])

    def test_document_blob_mismatch_stops_before_generation_loop(self):
        callback = Mock(return_value=b'different')
        with self.assertRaisesRegex(ValueError, 'saved-row document source differs'):
            self.source(callback)
        self.assertEqual(callback.call_count, 1)
        self.bare_git.assert_not_called()

    def test_generation_only_blob_mismatch_is_rejected(self):
        callback = Mock(side_effect=lambda **entry:
                        b'different' if entry['source_path'] == 'src/third.py' else self.read(**entry))
        with self.assertRaisesRegex(ValueError, 'generation-publication selected source changed'):
            self.source(callback)
        self.assertEqual(callback.call_count, 5)
        self.bare_git.assert_not_called()

    def test_callback_stop_preserves_original_exception_without_later_call_or_git(self):
        stop = whole.monitor.resources.ResourceStop('wall_seconds')
        callback = Mock(side_effect=stop)
        with self.assertRaises(type(stop)) as caught:
            self.source(callback)
        self.assertIs(caught.exception, stop)
        self.assertEqual(callback.call_count, 1)
        self.bare_git.assert_not_called()

    def test_invalid_callback_is_rejected_before_identity_or_git(self):
        with self.assertRaisesRegex(ValueError, 'blob callback must be callable'):
            self.source({'invalid': True})
        self.identity.assert_not_called()
        self.bare_git.assert_not_called()

    def test_changed_head_prevents_any_blob_callback(self):
        self.identity.return_value = {'head': b'a' * 40, 'status': b''}
        callback = Mock(side_effect=self.read)
        with self.assertRaisesRegex(ValueError, 'clean expected HEAD'):
            self.source(callback)
        callback.assert_not_called()
        self.bare_git.assert_not_called()

    def test_non_bytes_cannot_bypass_raw_comparison_in_either_loop(self):
        class EqualToEverything:
            def __eq__(self, other):
                return True

        for name in ('src/first.py', 'src/third.py'):
            with self.subTest(name=name):
                callback = Mock(side_effect=lambda **entry:
                                EqualToEverything() if entry['source_path'] == name else self.read(**entry))
                with self.assertRaises(ValueError):
                    self.source(callback)
                self.bare_git.assert_not_called()


if __name__ == '__main__':
    unittest.main()
