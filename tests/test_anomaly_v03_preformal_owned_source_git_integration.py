"""The optional owned reader replaces each selected v1 bare Git call."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_platform_five_role_fixture as chain
from banto_ai import anomaly_v03_preformal_five_role_job_owner as owner


REVISION = 'a' * 40


class Reader:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def run(self, *, call_id, operation, source_path=None,
            expected_output_pin=None):
        self.calls.append((call_id, operation, source_path,
                           expected_output_pin))
        if operation == 'head':
            return (REVISION + '\n').encode('ascii')
        if operation == 'status':
            return b''
        raw = self.values[source_path]
        if expected_output_pin != owner.observed._pin(raw):
            raise ValueError('reader expected pin mismatch')
        return raw


class OwnedSourceGitIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-source-git-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.values = {}
        for index, name in enumerate((*chain.SOURCES, owner.SOURCE)):
            raw = f'committed source {index}\n'.encode('ascii')
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.values[name] = raw

    def test_owner_selected_sources_use_seven_reader_calls_not_bare_git(self):
        reader = Reader(self.values)
        with patch.object(chain, 'ROOT', self.root), \
             patch.object(owner, 'ROOT', self.root), \
             patch.object(chain.subprocess, 'check_output',
                          side_effect=AssertionError('bare Git used')):
            result = owner._source(REVISION, git_reader=reader)
        self.assertEqual(result['revision'], REVISION)
        self.assertEqual(result['owner'],
                         owner.observed._pin(self.values[owner.SOURCE]))
        self.assertEqual([call[0] for call in reader.calls],
                         ['head', 'status', 'selected-source-0',
                          'selected-source-1', 'selected-source-2',
                          'selected-source-3', 'owner-source'])
        self.assertEqual([call[1] for call in reader.calls],
                         ['head', 'status'] + ['source_blob'] * 5)
        self.assertEqual([call[2] for call in reader.calls[2:]],
                         [*chain.SOURCES, owner.SOURCE])

    def test_wrong_blob_and_dirty_status_fail_closed(self):
        class WrongBlob(Reader):
            def run(self, **kwargs):
                if kwargs['call_id'] == 'selected-source-1':
                    return b'wrong committed bytes\n'
                return super().run(**kwargs)

        class Dirty(Reader):
            def run(self, **kwargs):
                if kwargs['operation'] == 'status':
                    return b' M src/banto_ai/anomaly_v03.py\n'
                return super().run(**kwargs)

        with patch.object(chain, 'ROOT', self.root), \
             patch.object(owner, 'ROOT', self.root), \
             patch.object(chain.subprocess, 'check_output',
                          side_effect=AssertionError('bare Git used')):
            with self.assertRaises(ValueError):
                owner._source(REVISION, git_reader=WrongBlob(self.values))
            with self.assertRaises(ValueError):
                owner._source(REVISION, git_reader=Dirty(self.values))


if __name__ == '__main__':
    unittest.main()
