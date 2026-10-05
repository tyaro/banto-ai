"""Opt-in parent source Git calls stay owned and saved verification replays."""
from __future__ import annotations

from contextlib import ExitStack, nullcontext, redirect_stderr
import io as text_io
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_five_role_parent_owned_git as parent_git
from tests import test_anomaly_v03_preformal_five_role_owned_source_anchor_v2 as fixture_module
from tools import preformal_five_role_parent_owned_git as cli


class ParentOwnedGitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.FiveRoleOwnedSourceAnchorV2Tests.setUpClass()

    def setUp(self):
        self.fixture = fixture_module.FiveRoleOwnedSourceAnchorV2Tests(
            'test_real_seven_calls_bind_owner_and_reopen_without_git_rerun')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def _roots(self):
        stack = ExitStack()
        f = self.fixture
        for module in (parent_git, parent_git.preflight, parent_git.source_git,
                       parent_git.owner, parent_git.chain,
                       parent_git.producer_binding.producer):
            stack.enter_context(patch.object(module, 'ROOT', f.root))
        return stack

    def _run(self, name='trial', **options):
        f = self.fixture
        with self._roots():
            return parent_git.run_anchored(
                expected_mode='fixture', join_root=f.join,
                expected_join_receipt_pin=f.join_pin,
                expected_revision=f.revision,
                receipt_parent=f.parent, receipt_name=name,
                git_policy_path=f.policy_path,
                expected_git_policy_pin=f.policy_pin, **options)

    def _verify(self, result, name='trial'):
        with self._roots():
            return parent_git.verify_retained(
                self.fixture.parent / name, result['receipt_pin'])

    def _owned_fake_owner(self, status='verified'):
        f = self.fixture
        save = f._fake_owner(status)

        def run(**kwargs):
            for index in range(4):
                parent_git.owner._source(
                    kwargs['expected_revision'], git_reader=kwargs['git_reader'],
                    git_call_prefix=f'parent-source-{index}-')
            result = save(**kwargs)
            if status == 'verified' and kwargs.get('child_git_policy_path'):
                root = Path(result['check_directory'])
                invocation = parent_git.v.strict_json(
                    (root / 'invocation.json').read_bytes())
                invocation.update(
                    format=(parent_git.owner.OWNED_PRODUCER_INVOCATION if
                            kwargs.get('own_producer_git') else
                            parent_git.owner.OWNED_GIT_INVOCATION),
                    mode='fixture', archive_pin=f.join_pin,
                    bound_pin=f.join_pin, profile_pins=None,
                    result_root=str(root / 'five-role'), invocation_id='a' * 64,
                    child_git_policy_path=str(kwargs['child_git_policy_path']),
                    child_git_policy_pin=kwargs['expected_child_git_policy_pin'])
                invocation_raw = parent_git.io.json_bytes(invocation)
                (root / 'invocation.json').write_bytes(invocation_raw)
                receipt = parent_git.v.strict_json((root / 'receipt.json').read_bytes())
                receipt['invocation_pin'] = parent_git.observed._pin(invocation_raw)
                raw = parent_git.io.json_bytes(receipt)
                (root / 'receipt.json').write_bytes(raw)
                result['receipt_pin'] = parent_git.observed._pin(raw)
                with parent_git.source_git.OwnedSourceGitSession(
                        policy_path=f.policy_path, expected_policy_pin=f.policy_pin,
                        revision=f.revision, receipt_root=root / 'child-git',
                        phase=parent_git.owner.CHILD_GIT_PHASE) as child_reader:
                    parent_git.owner._source(f.revision, git_reader=child_reader,
                                             git_call_prefix='child-source-')
                    for index in range(2):
                        parent_git.chain._git_sources(
                            f.revision, git_reader=child_reader,
                            git_call_prefix=f'child-chain-source-{index}-')
                    parent_git.owner._source(f.revision, git_reader=child_reader,
                                             git_call_prefix='child-boundary-')
                if kwargs.get('own_producer_git'):
                    receipt['inner_result_pin'] = self._fake_producer(root)
                    raw = parent_git.io.json_bytes(receipt)
                    (root / 'receipt.json').write_bytes(raw)
                    result['receipt_pin'] = parent_git.observed._pin(raw)
            return result

        return run

    def _prepare_producer_sources(self):
        f = self.fixture
        producer = parent_git.producer_binding.producer
        for name in producer.SOURCE_FILES:
            if name not in f.sources:
                raw = (name + '\n').encode()
                path = f.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                f.sources[name] = raw
        f._git('-C', str(f.root), 'add', '.')
        f._git('-C', str(f.root), '-c', 'user.name=Fixture',
               '-c', 'user.email=fixture@example.invalid', 'commit', '-q', '-m', 'producer')
        f.revision = f._git('-C', str(f.root), 'rev-parse', 'HEAD').decode().strip()
        f.policy['revision'] = f.revision
        f._save_policy()

    def _fake_producer(self, owner_root):
        f = self.fixture
        producer = parent_git.producer_binding.producer
        target = owner_root / 'five-role' / 'producer'
        (target / 'worker').mkdir(parents=True)

        def save(path, value):
            raw = parent_git.io.json_bytes(value)
            path.write_bytes(raw)
            return parent_git.observed._pin(raw)

        with parent_git.source_git.OwnedSourceGitSession(
                policy_path=f.policy_path, expected_policy_pin=f.policy_pin,
                revision=f.revision, receipt_root=owner_root / 'producer-git',
                phase=parent_git.owner.PRODUCER_GIT_PHASE) as reader:
            for index in range(3):
                source = producer._git_sources(f.revision, git_reader=reader,
                                                git_call_prefix=f'producer-source-{index}-')
            files = {'project/' + name: {
                'category': 'project', 'native': False,
                'physical_path': str(f.root / name),
                'pin': parent_git.observed._pin(f.sources[name])}
                for name in sorted(producer.SOURCE_FILES)}
            pair = {'before': {'files': files}, 'after': {'files': files}}
            git = producer._dependency_git(f.revision, git_reader=reader)
            for logical in files:
                name = logical[len('project/'):]
                self.assertEqual(git('show', f.revision + ':' + name), f.sources[name])
                self.assertEqual(git('show', f.revision + ':' + name), f.sources[name])
            producer._git_sources(f.revision, git_reader=reader,
                                  git_call_prefix='producer-source-3-')
        invocation = {'format': producer.INVOCATION, 'invocation_id': 'a' * 64,
                      'source_revision': f.revision, 'source': source}
        reply = {'format': producer.FORMAT, 'status': 'joined',
                 'invocation_id': invocation['invocation_id'],
                 'source_before': source, 'source_after': source,
                 'dependencies_before': pair['before'], 'dependencies_after': pair['after']}
        result = {'format': producer.FORMAT, 'status': 'verified', 'mode': 'fixture',
                  'source_revision': f.revision, 'profile_required': False,
                  'source_closure_complete': False, 'runtime_closure_complete': False,
                  'formal_permission': False,
                  'invocation_pin': save(target / 'invocation.json', invocation),
                  'stdout_pin': save(target / 'worker' / 'report.json', reply),
                  'dependency_pin': save(target / 'dependencies.json', pair),
                  'dependency_observation': {'project_files': len(files)}}
        top = {'status': 'verified', 'source_revision': f.revision,
               'producer': {'result_pin': save(target / 'result.json', result)}}
        return save(owner_root / 'five-role' / 'result.json', top)

    def test_producer_opt_in_binds_inventory_and_replays_without_git(self):
        self._prepare_producer_sources()
        with patch.object(parent_git.owner, 'run_owned', side_effect=self._owned_fake_owner()), \
             patch.object(parent_git.owner, 'verify_retained', side_effect=self._owned_fake_verifier), \
             patch.object(subprocess, 'check_output', side_effect=AssertionError('bare Git')):
            result = self._run('producer-owned', own_producer_git=True)
            self.assertEqual(result['status'], 'verified', result)
            self.assertEqual(result['format'], parent_git.PRODUCER_FORMAT)
            self.assertEqual(result['producer_git_call_count'], 49)
            self.assertTrue(result['child_fixed_git_owned'])
            self.assertTrue(result['producer_v1_git_owned'])
            self.assertFalse(result['inner_v1_git_owned'])
            with patch.object(parent_git.source_git.owned_git, 'run_owned',
                              side_effect=AssertionError('Git relaunched')):
                self.assertEqual(self._verify(result, 'producer-owned')['call_status'], 'verified')
                root = self.fixture.parent / 'producer-owned'
                saved_owner = parent_git.v.strict_json((root / 'attempt' / 'receipt.json').read_bytes())
                with self._roots():
                    expected = parent_git.producer_binding.expected_calls(root / 'attempt', saved_owner)
                manifest = parent_git.v.strict_json((root / 'attempt' / 'producer-git' / 'manifest.json').read_bytes())
                manifest['calls'][30]['source_path'] = producer_name = parent_git.owner.SOURCE
                self.assertNotEqual(expected[30][2], producer_name)
                with self.assertRaisesRegex(ValueError, 'call order'):
                    parent_git.producer_binding.verify_calls(manifest['calls'], expected)
                (root / 'attempt' / 'five-role' / 'producer' / 'dependencies.json').write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError, 'producer Git binding .*dependencies.json'):
                    self._verify(result, 'producer-owned')

    def test_child_opt_in_binds_all_68_calls_and_replays_without_git(self):
        with patch.object(parent_git.owner, 'run_owned',
                          side_effect=self._owned_fake_owner()), \
             patch.object(parent_git.owner, 'verify_retained',
                          side_effect=self._owned_fake_verifier), \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            result = self._run('child-owned', own_child_git=True)
            self.assertEqual(result['status'], 'verified', result)
            self.assertEqual(result['format'], parent_git.CHILD_FORMAT)
            self.assertEqual((result['source_git_call_count'],
                              result['parent_git_call_count'],
                              result['child_git_call_count']), (7, 35, 26))
            self.assertTrue(result['child_fixed_git_owned'])
            self.assertFalse(result['inner_v1_git_owned'])
            with patch.object(parent_git.source_git.owned_git, 'run_owned',
                              side_effect=AssertionError('Git relaunched')):
                verified = self._verify(result, 'child-owned')
            self.assertEqual(verified['child_git_call_count'], 26)
            self.assertFalse(verified['runtime_closure_complete'])

    def test_child_opt_in_cannot_downgrade_invocation_to_unowned_child(self):
        f = self.fixture
        with patch.object(parent_git.owner, 'run_owned',
                          side_effect=self._owned_fake_owner()), \
             patch.object(parent_git.owner, 'verify_retained',
                          side_effect=self._owned_fake_verifier):
            result = self._run('child-downgrade', own_child_git=True)
            self.assertEqual(result['status'], 'verified', result)
            root = f.parent / 'child-downgrade'
            owner_root = root / 'attempt'
            invocation = parent_git.v.strict_json(
                (owner_root / 'invocation.json').read_bytes())
            invocation['format'] = parent_git.owner.INVOCATION
            del invocation['child_git_policy_path']
            del invocation['child_git_policy_pin']
            raw = parent_git.io.json_bytes(invocation)
            (owner_root / 'invocation.json').write_bytes(raw)
            receipt = parent_git.v.strict_json((owner_root / 'receipt.json').read_bytes())
            receipt['invocation_pin'] = parent_git.observed._pin(raw)
            raw = parent_git.io.json_bytes(receipt)
            (owner_root / 'receipt.json').write_bytes(raw)
            outer = parent_git.v.strict_json((root / 'receipt.json').read_bytes())
            outer['owner_receipt_pin'] = parent_git.observed._pin(raw)
            raw = parent_git.io.json_bytes(outer)
            (root / 'receipt.json').write_bytes(raw)
            result['receipt_pin'] = parent_git.observed._pin(raw)
            with self.assertRaisesRegex(ValueError, 'owned child invocation'):
                self._verify(result, 'child-downgrade')

    def _owned_fake_verifier(self, root, pin, *, git_reader=None,
                             git_call_prefix=''):
        parent_git.owner._source(
            self.fixture.revision, git_reader=git_reader,
            git_call_prefix=git_call_prefix)
        return self.fixture._verified_owner(root, pin)

    def test_parent_calls_and_retained_replay_never_use_bare_git(self):
        with patch.object(parent_git.owner, 'run_owned',
                          side_effect=self._owned_fake_owner()) as run, \
             patch.object(parent_git.owner, 'verify_retained',
                          side_effect=self._owned_fake_verifier) as verify, \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            result = self._run()
            self.assertEqual(result['status'], 'verified', result)
            self.assertEqual(result['source_git_call_count'], 7)
            self.assertEqual(result['parent_git_call_count'], 35)
            self.assertTrue(result['parent_v1_git_owned'])
            self.assertFalse(result['inner_v1_git_owned'])
            self.assertFalse(result['source_closure_complete'])
            manifest = parent_git.v.strict_json((
                self.fixture.parent / 'trial' / 'parent-git' /
                'manifest.json').read_bytes())
            self.assertEqual(len({row['call_id'] for row in manifest['calls']}), 35)
            with patch.object(parent_git.source_git.owned_git, 'run_owned',
                              side_effect=AssertionError('Git relaunched')):
                retained = self._verify(result)
            self.assertEqual(retained['call_status'], 'verified')
            self.assertEqual(retained['parent_git_call_count'], 35)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(verify.call_count, 2)

    def test_dirty_source_after_preflight_stops_before_owner_launch(self):
        f = self.fixture
        launched = []

        def changed(**kwargs):
            (f.root / parent_git.owner.SOURCE).write_bytes(b'changed source\n')
            parent_git.owner._source(
                kwargs['expected_revision'], git_reader=kwargs['git_reader'],
                git_call_prefix='parent-source-0-')
            launched.append(True)
            return f._fake_owner('verified')(**kwargs)

        with patch.object(parent_git.owner, 'run_owned', side_effect=changed), \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            result = self._run()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'owner_rejected')
        self.assertEqual(result['parent_git_status'], 'failed')
        self.assertEqual(result['parent_git_call_count'], 2)
        self.assertFalse(launched)
        self.assertEqual(self._verify(result)['call_status'], 'failed')

    def test_changed_owner_blob_after_clean_status_stops_before_launch(self):
        f = self.fixture
        original = parent_git.observed._file
        started = False

        def read(path, maximum):
            if started and Path(path) == f.root / parent_git.owner.SOURCE:
                return b'changed blob bytes\n'
            return original(path, maximum)

        def changed(**kwargs):
            nonlocal started
            started = True
            parent_git.owner._source(
                kwargs['expected_revision'], git_reader=kwargs['git_reader'],
                git_call_prefix='parent-source-0-')
            self.fail('changed source blob accepted')

        with patch.object(parent_git.owner, 'run_owned', side_effect=changed), \
             patch.object(parent_git.observed, '_file', side_effect=read), \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            result = self._run('changed-blob')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'owner_rejected')
        self.assertEqual(result['parent_git_status'], 'failed')
        self.assertEqual(result['parent_git_call_count'], 7)
        self.assertEqual(self._verify(result, 'changed-blob')['call_status'],
                         'failed')

    def test_unexpected_extra_boundary_cannot_certify_parent_inventory(self):
        f = self.fixture
        save = f._fake_owner('verified')

        def extra(**kwargs):
            for index in range(5):
                parent_git.owner._source(
                    kwargs['expected_revision'], git_reader=kwargs['git_reader'],
                    git_call_prefix=f'parent-source-{index}-')
            return save(**kwargs)

        with patch.object(parent_git.owner, 'run_owned', side_effect=extra), \
             patch.object(parent_git.owner, 'verify_retained',
                          side_effect=self._owned_fake_verifier):
            result = self._run('extra-boundary')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'owner_rejected')
        self.assertFalse(result['parent_v1_git_owned'])
        self.assertEqual(result['parent_git_call_count'], 42)
        self.assertEqual(self._verify(result, 'extra-boundary')['call_status'],
                         'failed')

    def test_real_parent_boundary_rejects_dirty_source_before_spawn(self):
        f = self.fixture
        inputs = {'archive_pin': f.join_pin, 'bound_pin': f.join_pin,
                  'profile_pins': None}

        def supervise(*args, boundary, **kwargs):
            (f.root / parent_git.owner.SOURCE).write_bytes(b'changed boundary\n')
            boundary()
            self.fail('dirty boundary accepted')

        with self._roots(), \
             patch.object(parent_git.owner, '_inputs', return_value=inputs), \
             patch.object(parent_git.owner.chain.four.platform,
                          '_platform_scope', return_value=nullcontext()), \
             patch.object(parent_git.owner.job_owner, 'supervise_cli',
                          side_effect=supervise) as supervise_mock, \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            with parent_git.source_git.OwnedSourceGitSession(
                    policy_path=f.policy_path,
                    expected_policy_pin=f.policy_pin,
                    revision=f.revision,
                    receipt_root=f.artifacts / 'boundary-git',
                    phase='parent-source-boundaries') as reader:
                result = parent_git.owner.run_owned(
                    expected_mode='fixture', join_root=f.join,
                    expected_join_receipt_pin=f.join_pin,
                    expected_revision=f.revision,
                    receipt_parent=f.parent, receipt_name='boundary-attempt',
                    git_reader=reader)
            self.assertEqual(reader.manifest_result['status'], 'failed')
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['all_job_processes_exit_confirmed'])
        self.assertEqual(supervise_mock.call_count, 1)

    def test_real_parent_entry_and_verifier_use_35_owned_calls(self):
        f = self.fixture
        inputs = {'archive_pin': f.join_pin, 'bound_pin': f.join_pin,
                  'profile_pins': None}
        report = {'job': {'accounting': {'active_processes': 0},
                          'memory': {'peak': 1}}}
        inner = {'inner_result_pin': f.join_pin}
        real_observe = parent_git.owner.observed.creation_observation

        def observe(pid, handle):
            if pid == 99999999:
                return {'pid': pid}
            return real_observe(pid, handle)

        def supervise(*args, boundary, on_started, **kwargs):
            boundary()
            on_started(SimpleNamespace(pid=99999999, _handle=0))
            boundary()
            return report

        with self._roots(), \
             patch.object(parent_git.owner, '_inputs', return_value=inputs), \
             patch.object(parent_git.owner, '_job_complete'), \
             patch.object(parent_git.owner, '_inner', return_value=inner), \
             patch.object(parent_git.owner.observed,
                          'creation_observation', side_effect=observe), \
             patch.object(parent_git.owner.chain.four.platform,
                          '_platform_scope', return_value=nullcontext()), \
             patch.object(parent_git.owner.job_owner, 'supervise_cli',
                          side_effect=supervise), \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            git_root = f.artifacts / 'real-parent-git'
            with parent_git.source_git.OwnedSourceGitSession(
                    policy_path=f.policy_path,
                    expected_policy_pin=f.policy_pin,
                    revision=f.revision, receipt_root=git_root,
                    phase='parent-source-boundaries') as reader:
                result = parent_git.owner.run_owned(
                    expected_mode='fixture', join_root=f.join,
                    expected_join_receipt_pin=f.join_pin,
                    expected_revision=f.revision,
                    receipt_parent=f.parent, receipt_name='real-parent',
                    git_reader=reader)
                self.assertEqual(result['status'], 'verified',
                                 (result, reader.calls))
                verified = parent_git.owner.verify_retained(
                    f.parent / 'real-parent', result['receipt_pin'],
                    git_reader=reader, git_call_prefix='parent-verify-')
                self.assertEqual(verified['status'], 'verified_retained')
            self.assertEqual(reader.manifest_result['status'], 'verified')
            self.assertEqual(reader.manifest_result['call_count'], 35)
            checked = parent_git.source_git.verify_retained(
                git_root, reader.manifest_result['manifest_pin'],
                policy_path=f.policy_path, expected_policy_pin=f.policy_pin,
                revision=f.revision, phase='parent-source-boundaries')
            parent_git._parent_calls(checked['calls'], f._source())
            replay = parent_git._SavedGitReader(git_root, checked['calls'])
            saved = parent_git.owner.verify_retained(
                f.parent / 'real-parent', result['receipt_pin'],
                git_reader=replay, git_call_prefix='parent-verify-')
            replay.finish()
            self.assertEqual(saved['status'], 'verified_retained')

    def test_saved_parent_stdout_tamper_is_rejected(self):
        with patch.object(parent_git.owner, 'run_owned',
                          side_effect=self._owned_fake_owner()), \
             patch.object(parent_git.owner, 'verify_retained',
                          side_effect=self._owned_fake_verifier):
            result = self._run()
            path = (self.fixture.parent / 'trial' / 'parent-git' /
                    'parent-verify-head' / 'stdout.bin')
            path.write_bytes(b'wrong revision\n')
            with self.assertRaises(ValueError):
                self._verify(result)

    def test_candidate_set_is_rejected_before_owned_or_bare_git(self):
        f = self.fixture
        candidate_path = f.artifacts / 'candidate-set.json'
        candidate_pin = parent_git.observed._pin(b'candidate set fixture')
        with self._roots(), \
             patch.object(subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')), \
             patch.object(parent_git.source_git.owned_git, 'run_owned',
                          side_effect=AssertionError('owned Git invoked')):
            with self.assertRaisesRegex(ValueError, 'candidate profiles'):
                parent_git.run_anchored(
                    expected_mode='fixture', join_root=f.join,
                    expected_join_receipt_pin=f.join_pin,
                    expected_revision=f.revision,
                    receipt_parent=f.parent, receipt_name='candidate-rejected',
                    git_policy_path=f.policy_path,
                    expected_git_policy_pin=f.policy_pin,
                    candidate_set_path=candidate_path,
                    expected_candidate_set_pin=candidate_pin)
        self.assertFalse((f.parent / 'candidate-rejected').exists())

    def test_retained_candidate_injection_is_rejected_without_git(self):
        f = self.fixture
        with patch.object(parent_git.owner, 'run_owned',
                          side_effect=self._owned_fake_owner()), \
             patch.object(parent_git.owner, 'verify_retained',
                          side_effect=self._owned_fake_verifier):
            result = self._run('candidate-injection')
            path = f.parent / 'candidate-injection' / 'receipt.json'
            receipt = parent_git.v.strict_json(path.read_bytes())
            receipt['candidate_set_path'] = str(f.artifacts / 'candidate.json')
            receipt['candidate_set_pin'] = parent_git.observed._pin(b'candidate')
            raw = parent_git.io.json_bytes(receipt)
            path.write_bytes(raw)
            changed_pin = parent_git.observed._pin(raw)
            with self._roots(), \
                 patch.object(subprocess, 'check_output',
                              side_effect=AssertionError('bare Git invoked')), \
                 patch.object(parent_git.source_git.owned_git, 'run_owned',
                              side_effect=AssertionError('owned Git invoked')):
                with self.assertRaisesRegex(ValueError,
                                            'excludes candidate profiles'):
                    parent_git.verify_retained(
                        f.parent / 'candidate-injection', changed_pin)

    def test_cli_rejects_candidate_set_before_entry(self):
        f = self.fixture
        args = [
            'run', '--join-root', str(f.join),
            '--join-receipt-bytes', str(f.join_pin['bytes']),
            '--join-receipt-sha256', f.join_pin['sha256'],
            '--revision', f.revision,
            '--git-policy-path', str(f.policy_path),
            '--git-policy-bytes', str(f.policy_pin['bytes']),
            '--git-policy-sha256', f.policy_pin['sha256'],
            '--receipt-parent', str(f.parent),
            '--receipt-name', 'cli-candidate',
            '--candidate-set-path', str(f.artifacts / 'candidate.json'),
            '--candidate-set-bytes', '1',
            '--candidate-set-sha256', '0' * 64]
        with patch.object(cli.anchor, 'run_anchored',
                          side_effect=AssertionError('entry invoked')), \
             redirect_stderr(text_io.StringIO()) as error:
            with self.assertRaises(SystemExit) as raised:
                cli.main(args)
        self.assertEqual(raised.exception.code, 2)
        self.assertIn('candidate profiles use unowned parent Git',
                      error.getvalue())
        self.assertFalse((f.parent / 'cli-candidate').exists())


if __name__ == '__main__':
    unittest.main()
