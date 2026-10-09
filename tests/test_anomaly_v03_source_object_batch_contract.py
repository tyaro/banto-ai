"""Tree object metadata candidates, independent source bodies and original owners."""
import copy
import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_reader_dependencies as objects
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader

OBSERVATIONS = []


def fixture(count=2):
    bodies = {'src/banto_ai/s'+str(i)+'.py': ('source '+str(i)+'\n').encode() for i in range(count)}
    sources = [{'name': n, 'pin': objects._batch_pin(b),
                'git_blob_oid': hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
               for n, b in bodies.items()]
    raw = objects.source_object_batch_request_candidate(revision='1'*40, root='unissued-memory-root', sources=sources)
    request = json.loads(raw)
    maxima = [{'stdout': 41 if c['operation']=='head' else (c['stdout_bytes'] or 0),
               'stderr': 32, 'receipt': 64, 'partial': 16} for c in request['calls']]
    counts = {'control':14,'parent_failure':3,'diagnostic':2,'entry_context_identity':3,
              'carrier_failure':2,'archive_new_growth':1,'partial_raw':1,'reserve':2,'snapshot':0}
    storage = {n:{'entries':c,'bytes':131072 if n=='reserve' else c*32} for n,c in counts.items()}
    return raw, sources, bodies, maxima, storage


def metadata(sources):
    return b''.join((s['git_blob_oid']+' blob '+str(s['pin']['bytes'])+'\n').encode() for s in sources)


class SourceObjectBatchContractTests(unittest.TestCase):
    def held(self, count=2):
        raw,sources,bodies,maxima,storage=fixture(count);clock=Mock()
        held=objects.SourceObjectBatchContractPreparation(owner=SimpleNamespace(),checkpoint=clock,
            request_raw=raw,expected_sources=sources,source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        return held,raw,sources,bodies,maxima,storage,clock

    def complete(self,held,raw,sources):
        request=json.loads(raw)
        for i,call in enumerate(request['calls']):
            stdout=b'1'*40+b'\n' if call['operation']=='head' else b''
            if call['operation']=='source_blob_metadata_batch':
                stdout=metadata([sources[j] for j in request['groups'][call['group']]['members']])
            held.retain_raw(i,stdout,b'',b'opaque literal receipt',exit_code=0)

    def observe(self,held):
        OBSERVATIONS.append({'test':self.id(),'records':len(held._SourceObjectBatchContractPreparation__records),
            'pending':held._SourceObjectBatchContractPreparation__pending is not None,
            'maximum_packed_raw_bytes':getattr(held,'maximum_packed_raw_bytes',None),
            'unresolved':held.unresolved(),'native_authenticated':False,'formal_permission':False})

    def test_complete_tree_path_stdin_group_membership_has_new_version_and_no_body_stdout(self):
        held,raw,sources,bodies,_,_,clock=self.held(17);request=json.loads(raw)
        self.assertEqual([len(g['members']) for g in request['groups']],[16,1])
        self.assertEqual(len(request['calls']),8)
        self.assertEqual(request['batch_argv'],list(objects.SOURCE_OBJECT_ARGV))
        stdin=objects.source_object_batch_stdin(request,0)
        self.assertEqual(stdin,b''.join(('1'*40+':'+s['name']+'\n').encode() for s in sources[:16]))
        self.assertEqual(objects._batch_pin(stdin),request['groups'][0]['stdin_pin'])
        self.assertNotEqual(request['format'],objects.SOURCE_BATCH_REQUEST)
        clock.assert_not_called();self.observe(held)

    def test_metadata_proof_binds_all_literal_headers_and_independent_body_hashes(self):
        held,raw,sources,bodies,_,_,clock=self.held()
        proof=objects.source_object_batch_stdout_candidate(request_raw=raw,expected_sources=sources,
            source_bodies=bodies,group_index=0,stdout=metadata(sources))
        value=json.loads(proof);self.assertFalse(value['git_body_returned'])
        self.assertEqual(value['source_spans'][1]['git_blob_oid'],sources[1]['git_blob_oid'])
        self.assertTrue(all(v is False for v in value['scope'].values()))
        clock.assert_not_called();self.observe(held)

    def test_wrong_order_oid_type_size_missing_newline_and_trailing_bytes_refuse(self):
        raw,sources,bodies,_,_=fixture();stdout=metadata(sources)
        variants=[metadata(sources[::-1]),stdout.replace(b'blob',b'tree',1),stdout[:-1],stdout+b'x',
                  stdout.replace(sources[0]['git_blob_oid'].encode(),b'f'*40,1),stdout.replace(b' 9\n',b' 8\n',1)]
        for bad in variants:
            with self.assertRaises(ValueError):
                objects.source_object_batch_stdout_candidate(request_raw=raw,expected_sources=sources,
                    source_bodies=bodies,group_index=0,stdout=bad)

    def test_declared_blob_oid_cannot_replace_independent_sha256_body_and_sha1_object(self):
        for change in ('body','oid','roster'):
            raw,sources,bodies,_,_=fixture()
            if change=='body':bodies[sources[0]['name']]=b'changed'
            elif change=='oid':sources[0]['git_blob_oid']='f'*40
            else:bodies['src/banto_ai/extra.py']=b'x'
            with self.assertRaises(ValueError):
                objects.source_object_batch_stdout_candidate(request_raw=raw,expected_sources=sources,
                    source_bodies=bodies,group_index=0,stdout=metadata(sources))

    def test_old_version_added_field_changed_argv_or_stdin_pin_are_closed_out(self):
        for change in ('version','extra','argv','stdin'):
            raw,sources,bodies,_,_=fixture();request=json.loads(raw)
            if change=='version':request['format']=objects.SOURCE_BATCH_REQUEST
            elif change=='extra':request['authorized']=True
            elif change=='argv':request['batch_argv'].append('--filters')
            else:request['groups'][0]['stdin_pin']['sha256']='f'*64
            with self.assertRaises(ValueError):
                objects.source_object_batch_stdout_candidate(request_raw=objects._batch_json(request),
                    expected_sources=sources,source_bodies=bodies,group_index=0,stdout=metadata(sources))

    def test_failure_keeps_four_original_raws_and_first_error_after_alias_erasure(self):
        held,_,_,_,_,_,clock=self.held();stdout=b'failure';stderr=b'original stderr';receipt=b'opaque receipt';partial=b'partial'
        with self.assertRaises(ValueError) as first:
            held.retain_raw(0,stdout,stderr,receipt,exit_code=17,partial=partial)
        original=held._SourceObjectBatchContractPreparation__pending
        self.assertEqual(original['incoming'],(0,stdout,stderr,receipt,17,partial))
        held.pending=None;held.records=();held.error=None
        with self.assertRaises(ValueError) as again:held.prepare_pack()
        self.assertIs(first.exception,again.exception);self.assertIs(original,held._SourceObjectBatchContractPreparation__pending)
        clock.assert_not_called();self.observe(held)

    def test_mutated_body_after_first_return_is_rejected_without_accepting_second_return(self):
        held,_,sources,bodies,_,_,_=self.held();held.retain_raw(0,b'1'*40+b'\n',b'',b'r',exit_code=0)
        original=held.records;bodies[sources[0]['name']]=b'changed'
        with self.assertRaises(ValueError):held.retain_raw(1,b'',b'',b'r',exit_code=0)
        self.assertIs(held.records,original);self.observe(held)

    def test_all_future_failure_maxima_still_refuse_before_raw_or_pack(self):
        raw,sources,bodies,maxima,storage=fixture(17);clock=Mock()
        for limit in maxima:limit.update(stdout=131072,stderr=16384,receipt=32768,partial=131072)
        held=objects.SourceObjectBatchContractPreparation.__new__(objects.SourceObjectBatchContractPreparation)
        with self.assertRaisesRegex(ValueError,'packed future raw byte bound'):
            held.__init__(owner=object(),checkpoint=clock,request_raw=raw,expected_sources=sources,
                source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        self.assertEqual(held._SourceObjectBatchContractPreparation__records,())
        self.assertGreater(held.maximum_packed_raw_bytes,524288);clock.assert_not_called();self.observe(held)

    def test_partial_new_growth_snapshot_and_reserve_remain_separate_future_amounts(self):
        for change in ('bytes','entries','discount'):
            raw,sources,bodies,maxima,storage=fixture()
            if change=='bytes':storage['archive_new_growth']['bytes']=524288;storage['partial_raw']['bytes']=524288
            elif change=='entries':storage['snapshot']['entries']=4
            else:storage['control']['entries']=0
            with self.assertRaises(ValueError):
                objects.SourceObjectBatchContractPreparation(owner=object(),checkpoint=Mock(),request_raw=raw,
                    expected_sources=sources,source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)

    def test_full_som1_literal_readback_and_cached_original_transport(self):
        held,raw,sources,_,_,_,clock=self.held();self.complete(held,raw,sources)
        pack=held.prepare_pack();self.assertTrue(pack[0].startswith(b'SOM1'))
        self.assertIn(metadata(sources),pack[0]);self.assertIs(held.prepare_pack(),pack)
        self.assertFalse(json.loads(pack[1])['scope']['native_authorized'])
        clock.assert_not_called();self.observe(held)

    def test_metadata_return_erasure_and_cached_pack_replacement_latch_first_error(self):
        for change in ('metadata','cached'):
            held,raw,sources,_,_,_,_=self.held();self.complete(held,raw,sources)
            original=held.prepare_pack()
            if change=='metadata':held.records[2]['metadata_proof_raw']=None
            else:held._SourceObjectBatchContractPreparation__pack=(b'changed',original[1])
            with self.assertRaises(ValueError) as first:held.prepare_pack()
            held._SourceObjectBatchContractPreparation__pack=original
            with self.assertRaises(ValueError) as again:held.prepare_pack()
            self.assertIs(first.exception,again.exception);self.observe(held)

    def test_reinitialization_does_not_redecode_or_replace_independent_bodies(self):
        held,raw,sources,bodies,maxima,storage,clock=self.held();original=held.original_inputs
        with patch.object(objects.v,'strict_json') as decode,self.assertRaises(ValueError):
            held.__init__(owner=held.owner,checkpoint=clock,request_raw=raw,expected_sources=sources,
                source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        decode.assert_not_called();self.assertIs(held.original_inputs,original);self.observe(held)

    def test_parent_getter_interrupt_holds_original_bodies_before_getter(self):
        class Interrupted(reader.ReaderGitParent):
            @property
            def inventory_checkpoint(self):raise KeyboardInterrupt('getter')
        parent=Interrupted.__new__(Interrupted);raw,sources,bodies,maxima,storage=fixture()
        with self.assertRaises(KeyboardInterrupt):
            parent.prepare_source_object_batch_contract(request_raw=raw,expected_sources=sources,
                source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        held=parent._ReaderGitParent__source_object_batch_owner
        self.assertIs(held.original_inputs[4],bodies);self.assertIs(held.error.reader_git_parent,parent);self.observe(held)

    def test_parent_alias_erasure_keeps_original_keeper_and_early_readiness_refusal(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent);parent.inventory_checkpoint=Mock()
        raw,sources,bodies,maxima,storage=fixture()
        held=parent.prepare_source_object_batch_contract(request_raw=raw,expected_sources=sources,
            source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        parent.source_object_batch_owner=None
        with self.assertRaises(ValueError):parent._inventory_ready()
        parent.original_bootstrap_inputs=(None,)*11;parent.worker=None;parent.error=None
        error=ValueError('caller');
        class Escape(BaseException):pass
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(error,parent)
        self.assertIn(held,parent.original_publication_retention.owners)
        self.assertIs(parent.original_publication_retention,error.parent_publication_retention);self.observe(held)

    def test_execute_never_calls_clock_or_authorizes_metadata_as_native_transport(self):
        held,raw,sources,_,_,_,clock=self.held();self.complete(held,raw,sources)
        with self.assertRaises(ValueError):held.execute()
        self.assertEqual(len(held.records),6);clock.assert_not_called();self.observe(held)

    def test_rejected_second_raw_is_held_before_changed_body_validation(self):
        held,_,sources,bodies,_,_,_=self.held();held.retain_raw(0,b'1'*40+b'\n',b'',b'r',exit_code=0)
        bodies[sources[0]['name']]=b'changed';raw=b'rejected stdout';partial=b'rejected partial'
        with self.assertRaises(ValueError):held.retain_raw(1,raw,b'e',b'r',exit_code=17,partial=partial)
        attempts=held._SourceObjectBatchContractPreparation__raw_attempts
        self.assertIs(attempts[-1][1],raw);self.assertIs(attempts[-1][5],partial)
        held.records=();self.assertEqual(len(attempts),2);self.observe(held)

    def test_second_parent_preparation_is_private_before_rejecting_replacement(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent);parent.inventory_checkpoint=Mock()
        raw,sources,bodies,maxima,storage=fixture()
        args=dict(request_raw=raw,expected_sources=sources,source_bodies=bodies,raw_maxima=maxima,storage_maxima=storage)
        held=parent.prepare_source_object_batch_contract(**args)
        with self.assertRaises(ValueError):parent.prepare_source_object_batch_contract(**args)
        rejected=held._SourceObjectBatchContractPreparation__rejected_preparations[0]
        held.rejected_preparation=None;parent.source_object_batch_owner=None
        self.assertIs(rejected.original_inputs[4],bodies)
        self.assertIs(parent._ReaderGitParent__source_object_batch_owner,held);self.observe(held)

    def test_oversized_or_wrong_length_body_refuses_before_digest_allocation(self):
        raw,sources,bodies,_,_=fixture();bodies[sources[0]['name']]=b'x'*131073
        with patch.object(objects.hashlib,'sha256') as digest,self.assertRaises(ValueError):
            objects.source_object_batch_stdout_candidate(request_raw=raw,expected_sources=sources,
                source_bodies=bodies,group_index=0,stdout=metadata(sources))
        digest.assert_not_called()

    def test_failed_raw_and_preparation_reentry_do_not_grow_private_attempt_ledgers(self):
        held,_,_,_,_,_,_=self.held()
        with self.assertRaises(ValueError) as first:held.retain_raw(0,b'failed',b'',b'r',exit_code=17)
        attempts=held._SourceObjectBatchContractPreparation__raw_attempts
        for i in range(4):
            with self.assertRaises(ValueError) as again:held.retain_raw(i,b'new',b'',b'r',exit_code=17)
            self.assertIs(first.exception,again.exception)
        self.assertIs(held._SourceObjectBatchContractPreparation__raw_attempts,attempts)
        original=object()
        with self.assertRaises(ValueError):held.retain_rejected_preparation(original)
        for i in range(4):
            with self.assertRaises(ValueError):held.retain_rejected_preparation(object())
        self.assertEqual(held._SourceObjectBatchContractPreparation__rejected_preparations,(original,))
        self.observe(held)
