"""Focused invented-archive and preflight rejection checks for the owned join."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from banto_ai import anomaly_v03_owned_producer_fixture as owned


def archive(entries):
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as saved:
        for name, raw in entries:
            saved.writestr(name, raw)
    return stream.getvalue()


class OwnedProducerFixtureTests(unittest.TestCase):
    def setUp(self):
        self.manifest = owned.primary.v.canonical_json({
            'registration_pin': {'bytes': 1, 'sha256': '0' * 64}})
        self.entries = [
            ('primary/manifest.json', self.manifest),
            ('slices/manifest.json', b'{}'),
            ('primary/files/registration.json', b'{}'),
            ('slices/files/slices/invented.json', b'{}'),
        ]

    def test_owned_dependency_git_caches_and_rejects_unsafe_requests(self):
        revision = 'a' * 40
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = 'src/banto_ai/fixture.py'
            path = root / name
            path.parent.mkdir(parents=True)
            path.write_bytes(b'fixture\n')
            calls = []

            class Reader:
                def run(self, **kwargs):
                    calls.append(kwargs)
                    return b'fixture\n'

            with patch.object(owned, 'ROOT', root), \
                 patch.object(owned.subprocess, 'check_output', side_effect=AssertionError('bare Git')):
                git = owned._dependency_git(revision, git_reader=Reader())
                self.assertEqual(git('show', revision + ':' + name), b'fixture\n')
                self.assertEqual(git('show', revision + ':' + name), b'fixture\n')
                for args in (('show', 'b' * 40 + ':' + name),
                             ('show', revision + ':../escape'),
                             ('show', revision + ':docs/file.md'), ('status',)):
                    with self.assertRaises(ValueError):
                        git(*args)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]['expected_output_pin'], owned._pin(b'fixture\n'))
            self.assertEqual(calls[0]['call_id'], 'producer-dependency-0')

    def test_owned_producer_rejects_profile_loader_before_disk_or_git(self):
        with patch.object(owned.dependencies, 'load_five_role_profile',
                          side_effect=AssertionError('profile loader')):
            with self.assertRaisesRegex(ValueError, 'excludes unowned profile'):
                owned.join_with_evidence('unused', owned._pin(b'archive'),
                    expected_revision='a' * 40, receipt_parent='unused', receipt_name='unused',
                    git_reader=object(), dependency_profile_raw=b'{}',
                    expected_dependency_profile_pin=owned._pin(b'{}'))

    def test_decodes_names_without_extracting_or_granting_a_role(self):
        case = owned._decode_archive(archive(self.entries), (1, 1))
        self.assertEqual(case['expected_mode'], 'fixture')
        self.assertEqual(case['primary_input']['expected_mode'], 'fixture')
        self.assertEqual(set(case['primary_input']['snapshots']), {'registration.json'})
        self.assertEqual(set(case['snapshots']), {'slices/invented.json'})

    def test_rejects_case_alias_and_parent_traversal(self):
        altered = self.entries + [('primary/files/REGISTRATION.json', b'{}')]
        with self.assertRaisesRegex(ValueError, 'duplicate invented archive entry'):
            owned._decode_archive(archive(altered), (2, 1))
        altered = self.entries[:-1] + [('slices/files/../escaped.json', b'{}')]
        with self.assertRaises(ValueError):
            owned._decode_archive(archive(altered), (1, 1))

    def test_expansion_cap_is_checked_before_member_read(self):
        with patch.object(owned, 'UNCOMPRESSED_MAX', 20):
            with self.assertRaisesRegex(ValueError, 'expanded byte limit'):
                owned._decode_archive(archive(self.entries), (1, 1))

    def test_external_pin_failure_creates_no_worker_or_receipt(self):
        with tempfile.TemporaryDirectory(dir=owned.ROOT / 'artifacts') as temporary:
            parent = Path(temporary)
            (parent / 'input').mkdir()
            source = parent / 'input' / 'invented.zip'
            source.write_bytes(archive(self.entries))
            wrong = {'bytes': source.stat().st_size, 'sha256': '0' * 64}
            with self.assertRaisesRegex(ValueError, 'external invented archive pin'):
                owned.join_with_evidence(
                    source, wrong, expected_revision='a' * 40,
                    receipt_parent=parent, receipt_name='producer-attempt')
            self.assertFalse((parent / 'producer-attempt').exists())

    def test_saved_projection_inventory_uses_exact_regular_file_names(self):
        with tempfile.TemporaryDirectory(dir=owned.ROOT / 'artifacts') as temporary:
            output = Path(temporary)
            for name in ('bound.json', *(('projection/' + item)
                         for item in owned.projection.analysis.INPUT_LIMITS)):
                path = output / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'{}')
            owned._require_output_inventory(output)
            (output / 'projection' / 'unexpected.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'producer exact output inventory'):
                owned._require_output_inventory(output)

    def test_dependency_crosscheck_rejects_before_retaining_a_receipt(self):
        with tempfile.TemporaryDirectory(dir=owned.ROOT / 'artifacts') as temporary:
            target = Path(temporary)
            with patch.object(owned.dependencies, 'verify_pair',
                              side_effect=ValueError('parent dependency disk mismatch')):
                with self.assertRaisesRegex(ValueError, 'parent dependency disk mismatch'):
                    owned._retain_dependencies(target, {'before': 1}, {'after': 2},
                                               'a' * 40)
            self.assertFalse((target / 'dependencies.json').exists())
            self.assertFalse((target / 'dependency-crosscheck.json').exists())

    def test_dependency_receipts_are_pinned_after_parent_crosscheck(self):
        before, after = {'phase': 'before'}, {'phase': 'after'}
        crosscheck = {'status': 'observed_dependencies_disk_git_matched',
                      'source_closure_complete': False,
                      'runtime_closure_complete': False,
                      'formal_permission': False}
        with tempfile.TemporaryDirectory(dir=owned.ROOT / 'artifacts') as temporary:
            target = Path(temporary)
            with patch.object(owned.dependencies, 'verify_pair', return_value=crosscheck) as verify:
                pin, observation = owned._retain_dependencies(target, before, after,
                                                               'a' * 40)
            self.assertEqual(pin, owned._pin((target / 'dependencies.json').read_bytes()))
            self.assertEqual(observation, crosscheck)
            self.assertEqual(owned.primary.v.strict_json(
                (target / 'dependency-crosscheck.json').read_bytes()), crosscheck)
            self.assertEqual(verify.call_args.kwargs['required_sources'],
                             owned.SOURCE_FILES)

    def test_dependency_git_reader_rejects_unpinned_or_parent_paths(self):
        git = owned._dependency_git('a' * 40)
        with patch.object(owned.subprocess, 'check_output',
                          side_effect=AssertionError('Git should not be invoked')):
            with self.assertRaises(ValueError):
                git('show', 'b' * 40 + ':src/banto_ai/anomaly_v03.py')
            with self.assertRaises(ValueError):
                git('show', 'a' * 40 + ':../outside.py')

    def test_profile_mismatch_rejects_child_before_archive_read(self):
        with tempfile.TemporaryDirectory(dir=owned.ROOT / 'artifacts') as temporary:
            root = Path(temporary)
            output = root / 'output'
            output.mkdir()
            archive_path = root / 'invented.zip'
            invocation = {'output_root': str(output), 'source_revision': 'a' * 40,
                          'archive_path': str(archive_path),
                          'dependency_profile_pin': owned._pin(b'{}')}
            def file_read(path, maximum):
                self.assertNotEqual(Path(path), archive_path,
                                    'archive read before profile mismatch')
                return b'{}'
            with patch.object(owned, '_load_invocation', return_value=invocation), \
                 patch.object(owned, '_sources', return_value={}), \
                 patch.object(owned.runtime, 'probe_runtime', return_value={}), \
                 patch.object(owned.observed, 'creation_observation', return_value={}), \
                 patch.object(owned.observed, '_file', side_effect=file_read), \
                 patch.object(owned.dependencies, 'load_five_role_profile', return_value={}), \
                 patch.object(owned.dependencies, 'collect', return_value={}), \
                 patch.object(owned.dependencies, 'match_five_role_profile',
                              side_effect=ValueError('before profile mismatch')) as match:
                exit_code = owned.worker_main([str(root / 'invocation.json'), '2',
                                               owned._pin(b'{}')['sha256']])
            self.assertEqual(exit_code, 2)
            self.assertEqual(match.call_count, 1)
            self.assertFalse(archive_path.exists())
            self.assertFalse((output / 'bound.json').exists())


if __name__ == '__main__':
    unittest.main()
