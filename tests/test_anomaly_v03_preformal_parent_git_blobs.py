"""Actor boundary fixtures; no native Job or Git execution in these tests."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_parent_git_blobs as blobs
from banto_ai import anomaly_v03_preformal_owned_git_job as tree
from tests import test_anomaly_v03_preformal_git_receipt_archive as archive_helpers


class Budget:
    def __init__(self):
        self.stop = None
        self.phases = []
    def probe(self):
        return self.stop
    def checkpoint(self, phase):
        self.phases.append(phase)
        if self.stop is not None:
            raise tree.owner.resources.ResourceStop(self.stop)


class ParentGitBlobActorTests(unittest.TestCase):
    def setUp(self):
        fixture = archive_helpers.GitReceiptArchiveTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root/'artifacts/outer'; self.root.mkdir()
        self.entry = {'path':str(fixture.root/'artifacts/policy/policy.json'),
                      'expected_pin':blobs.observed._pin(b'policy'),
                      'policy':copy.deepcopy(fixture.policy),'revision':fixture.policy['revision']}
        self.budget = Budget()
        self.requests = ('src/a.py','src/b.py','src/a.py')
        self.data = {'src/a.py':b'a\n','src/b.py':b'b\n'}
        self.addCleanup(patch.stopall)
        patch.object(blobs,'ROOT',fixture.root).start()
        self.policy = patch.object(blobs.sessions,'_policy',return_value=fixture.policy).start()
        self.native = patch.object(blobs.owned,'run_owned',side_effect=self.execute).start()

    def actor(self):
        return blobs.ParentBlobActor(self.entry,root=self.root,checkout_root=self.fixture.root,
                                     budget=self.budget,expected_requests=self.requests)

    def execute(self, **kwargs):
        self.assertEqual(kwargs['timeout_seconds'],10)
        self.assertEqual(kwargs['stop_probe'],self.budget.probe)
        self.assertEqual(kwargs['policy'],self.entry['policy'])
        target=kwargs['receipt_root']; target.mkdir()
        args=self.fixture.arguments(self.native.call_count-1,data=self.data[kwargs['source_path']],
                                    source_path=kwargs['source_path'])
        for name,raw in [('receipt.json',args['receipt_raw']),('stdout.bin',args['stdout_raw']),('stderr.bin',b'')]:
            blobs.io._exclusive(target/name,raw)
        return {'receipt_root':str(target),'receipt':json.loads(args['receipt_raw']),
                'receipt_pin':args['expected_receipt_pin'],'stdout':args['stdout_raw']}

    def read_phase(self, actor, phase):
        read=actor.reader(phase)
        for name in self.requests:
            self.assertEqual(read(revision=self.entry['revision'],source_path=name,
                                  expected_output_pin=blobs.observed._pin(self.data[name])),self.data[name])

    def test_owned_calls_share_budget_and_cache_only_inside_phase(self):
        actor=self.actor(); self.read_phase(actor,'preflight')
        self.assertEqual(self.native.call_count,2)
        before=actor.verify(('preflight',))
        self.assertEqual(before['call_count'],2)
        self.read_phase(actor,'postflight')
        result=actor.verify(('preflight','postflight'))
        self.assertEqual(result['call_count'],4)
        self.assertEqual(self.native.call_count,4)
        self.assertFalse(actor.inflight.exists())
        self.assertEqual(actor.state()['request_counts'],{'preflight':3,'postflight':3})
        self.assertFalse(actor.state()['formal_permission'])
        self.assertLess((self.root/'git-blobs-postflight.json').stat().st_size,blobs.MAX_INDEX)

    def test_preflight_index_remains_valid_prefix_after_postflight(self):
        actor=self.actor(); self.read_phase(actor,'preflight'); actor.verify(('preflight',))
        saved=actor.state()['indices']['preflight']
        self.read_phase(actor,'postflight'); actor.verify(('preflight','postflight'))
        result=blobs.verify_index(Path(saved['path']),saved['pin'],entry=self.entry,
            checkout_root=self.fixture.root,expected_requests=self.requests,phases=('preflight',))
        self.assertEqual(result['call_count'],2)
        self.assertEqual(self.native.call_count,4)

    def test_copied_index_or_changed_expected_inventory_is_rejected(self):
        actor=self.actor();self.read_phase(actor,'preflight');actor.verify(('preflight',))
        saved=actor.state()['indices']['preflight']
        other=self.root/'other';other.mkdir()
        path=other/'git-blobs-preflight.json';path.write_bytes(Path(saved['path']).read_bytes())
        with self.assertRaises(ValueError):
            blobs.verify_index(path,saved['pin'],entry=self.entry,checkout_root=self.fixture.root,
                               expected_requests=self.requests,phases=('preflight',))
        with self.assertRaises(ValueError):
            blobs.verify_index(Path(saved['path']),saved['pin'],entry=self.entry,checkout_root=self.fixture.root,
                               expected_requests=('src/a.py',),phases=('preflight',))

    def test_policy_pin_recheck_or_shared_stop_prevents_first_git(self):
        for stop in (False,True):
            with self.subTest(stop=stop):
                target=self.root/str(stop);target.mkdir()
                actor=blobs.ParentBlobActor(self.entry,root=target,checkout_root=self.fixture.root,
                                           budget=self.budget,expected_requests=self.requests)
                if stop:self.budget.stop='wall_seconds'
                else:self.policy.side_effect=ValueError('policy changed')
                with self.assertRaises((ValueError,tree.owner.resources.ResourceStop)):
                    actor.read(revision=self.entry['revision'],source_path='src/a.py',
                               expected_output_pin=blobs.observed._pin(b'a\n'))
                self.assertTrue(actor.failed)
                self.assertFalse(actor.inflight.exists())
                self.native.assert_not_called()
                self.policy.side_effect=None;self.budget.stop=None

    def test_post_native_stop_keeps_receipt_pin_and_all_inflight_raw(self):
        actor=self.actor();execute=self.execute
        def stop(**kwargs):
            result=execute(**kwargs);self.budget.stop='wall_seconds';return result
        self.native.side_effect=stop
        with self.assertRaises(tree.owner.resources.ResourceStop):
            actor.read(revision=self.entry['revision'],source_path='src/a.py',
                       expected_output_pin=blobs.observed._pin(b'a\n'))
        self.assertIsNotNone(actor.state()['inflight_receipt_pin'])
        self.assertEqual({p.name for p in actor.inflight.iterdir()},{'stdout.bin','stderr.bin','receipt.json'})
        self.assertEqual(actor.archive.rows,[])
        with self.assertRaises(ValueError):actor.reader('postflight')
        self.assertEqual(self.native.call_count,1)

    def test_returned_stdout_mismatch_keeps_raw_without_archiving(self):
        actor=self.actor();execute=self.execute
        self.native.side_effect=lambda **kwargs:{**execute(**kwargs),'stdout':b'wrong'}
        with self.assertRaises(ValueError):
            actor.read(revision=self.entry['revision'],source_path='src/a.py',
                       expected_output_pin=blobs.observed._pin(b'a\n'))
        self.assertEqual(actor.archive.rows,[])
        self.assertTrue(actor.inflight.exists())

    def test_unreaped_original_owner_and_extra_handles_survive(self):
        actor=self.actor();owner=tree.owner.UnreapedJob(11,22,33,{'status':'failed'},extra_handles={'stdio':55})
        self.native.side_effect=owner
        with self.assertRaises(tree.owner.UnreapedJob) as caught:
            actor.read(revision=self.entry['revision'],source_path='src/a.py',
                       expected_output_pin=blobs.observed._pin(b'a\n'))
        self.assertIs(caught.exception,owner)
        self.assertEqual(owner.extra_handles,{'stdio':55})
        with self.assertRaises(ValueError):actor.reader('preflight')
        self.assertEqual(self.native.call_count,1)

    def test_cleanup_failure_keeps_archived_record_and_inflight(self):
        actor=self.actor()
        with patch.object(actor,'_clear_inflight',side_effect=OSError('cleanup')),self.assertRaises(OSError):
            actor.read(revision=self.entry['revision'],source_path='src/a.py',
                       expected_output_pin=blobs.observed._pin(b'a\n'))
        self.assertEqual(len(actor.archive.rows),1)
        self.assertTrue(actor.inflight.exists())
        with self.assertRaises(ValueError):actor.reader('preflight')

    def test_cleanup_rejects_extra_file_and_preserves_older_roots(self):
        old=self.fixture.root/'artifacts/old';old.mkdir();(old/'stdout.bin').write_bytes(b'old')
        actor=self.actor();execute=self.execute
        def extra(**kwargs):
            result=execute(**kwargs);(kwargs['receipt_root']/'other.bin').write_bytes(b'extra');return result
        self.native.side_effect=extra
        with self.assertRaises(ValueError):
            actor.read(revision=self.entry['revision'],source_path='src/a.py',
                       expected_output_pin=blobs.observed._pin(b'a\n'))
        self.assertEqual((old/'stdout.bin').read_bytes(),b'old')
        self.assertEqual(len(list(actor.inflight.iterdir())),4)

    def test_missing_read_inventory_or_early_postflight_poison_actor(self):
        actor=self.actor()
        with self.assertRaises(ValueError):actor.reader('postflight')
        self.native.assert_not_called()
        target=self.root/'missing';target.mkdir()
        actor=blobs.ParentBlobActor(self.entry,root=target,checkout_root=self.fixture.root,
                                   budget=self.budget,expected_requests=self.requests)
        actor.read(revision=self.entry['revision'],source_path='src/a.py',expected_output_pin=blobs.observed._pin(b'a\n'))
        with self.assertRaises(ValueError):actor.verify(('preflight',))
        with self.assertRaises(ValueError):actor.reader('preflight')

    def test_changed_source_pin_or_extra_cached_request_does_not_start_git(self):
        for pin in (blobs.observed._pin(b'a\n'),blobs.observed._pin(b'changed')):
            target=self.root/pin['sha256'];target.mkdir()
            actor=blobs.ParentBlobActor(self.entry,root=target,checkout_root=self.fixture.root,
                                       budget=self.budget,expected_requests=self.requests)
            actor.read(revision=self.entry['revision'],source_path='src/a.py',expected_output_pin=blobs.observed._pin(b'a\n'))
            actor.read(revision=self.entry['revision'],source_path='src/a.py',expected_output_pin=blobs.observed._pin(b'a\n'))
            count=self.native.call_count
            with self.assertRaises(ValueError):
                actor.read(revision=self.entry['revision'],source_path='src/a.py',expected_output_pin=pin)
            self.assertEqual(self.native.call_count,count)


if __name__ == '__main__':
    unittest.main()
