"""New batch candidate protocol and private raw-prefix risks; no native execution."""
import copy
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import _anomaly_v03_reader_dependencies as batch
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader

OBSERVATIONS=[]


def row(name, body):
    return {'name':'src/banto_ai/'+name+'.py','pin':batch._batch_pin(body),
            'git_blob_oid':hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()}


def storage():
    counts={'control':14,'parent_failure':3,'diagnostic':2,'entry_context_identity':3,
            'carrier_failure':2,'archive_new_growth':1,'partial_raw':1,'reserve':2,'snapshot':0}
    return {name:{'entries':count,'bytes':131072 if name=='reserve' else count*32}
            for name,count in counts.items()}


class SourceBatchContractTests(unittest.TestCase):
    def fixture(self, sources=None):
        bodies=[b'first\n',b'second\n'] if sources is None else [b'x']*len(sources)
        sources=[row('first',bodies[0]),row('second',bodies[1])] if sources is None else sources
        raw=batch.source_batch_request_candidate(revision='1'*40,root='engineering-memory-root',sources=sources)
        plan=json.loads(raw)
        limits=[{'stdout':41 if c['operation']=='head' else (c['stdout_bytes'] or 0),
                 'stderr':16,'receipt':64,'partial':16} for c in plan['calls']]
        owner=SimpleNamespace();clock=Mock()
        held=batch.SourceBatchContractPreparation(owner=owner,checkpoint=clock,request_raw=raw,
            expected_sources=sources,raw_maxima=limits,storage_maxima=storage())
        return held,raw,sources,limits,clock,bodies

    def controls(self, held, indices=(0,1)):
        for index in indices:
            held.retain_raw(index,b'1'*40+b'\n' if index%3==0 else b'',b'',b'opaque receipt',exit_code=0)

    def stdout(self,sources,bodies):
        return b''.join((s['git_blob_oid']+' blob '+str(len(body))+'\n').encode()+body+b'\n'
                        for s,body in zip(sources,bodies))

    def observe(self,held):
        OBSERVATIONS.append({'test':self.id(),'original_raw_records':len(held._SourceBatchContractPreparation__records),
            'pending':held._SourceBatchContractPreparation__pending is not None,
            'first_error':type(held.error).__name__ if held.error is not None else None,
            'maximum_packed_raw_bytes':getattr(held,'maximum_packed_raw_bytes',None),
            'native_authorized':False,'formal_permission':False})

    def test_new_request_has_complete_pre_post_groups_without_v1_fields_or_authority(self):
        held,raw,sources,limits,clock,_=self.fixture()
        plan=json.loads(raw)
        self.assertEqual([c['operation'] for c in plan['calls']],
                         ['head','status','source_blob_batch']*2)
        self.assertEqual(plan['sources'],sources);self.assertEqual(held.projection['entries'],29)
        self.assertTrue(held.unresolved());self.assertTrue(all(v is False for v in plan['scope'].values()))
        clock.assert_not_called();self.observe(held)

    def test_literal_packed_readback_covers_control_and_source_raw_and_cached_returns(self):
        held,raw,sources,limits,clock,bodies=self.fixture();stdout=self.stdout(sources,bodies)
        self.controls(held);proof=held.retain_raw(2,stdout,b'warning',b'opaque receipt',exit_code=0)
        self.controls(held,(3,4));held.retain_raw(5,stdout,b'',b'opaque receipt',exit_code=0)
        pack=held.prepare_pack();self.assertTrue(pack[0].startswith(b'SBR1'));self.assertIn(stdout,pack[0])
        self.assertEqual(json.loads(proof)['source_spans'][1]['pin'],sources[1]['pin'])
        self.assertIs(held.prepare_pack(),pack);clock.assert_not_called();self.observe(held)

    def test_header_order_missing_body_and_extra_stdout_refuse_and_keep_literal_candidates(self):
        for kind in ('order','missing','extra'):
            held,_,sources,_,_,bodies=self.fixture();self.controls(held)
            raw=self.stdout(sources[::-1],bodies[::-1]) if kind=='order' else self.stdout(sources,bodies)
            raw=raw[:-1] if kind=='missing' else raw+b'x' if kind=='extra' else raw
            with self.assertRaises(ValueError):held.retain_raw(2,raw,b'',b'receipt',exit_code=0)
            self.assertIs(held._SourceBatchContractPreparation__pending['incoming'][1],raw)
            self.observe(held)

    def test_blob_object_pin_is_independent_of_sha256_body_pin(self):
        held,_,sources,_,_,bodies=self.fixture()
        sources[0]['git_blob_oid']='f'*40
        # A new internally consistent declaration still cannot match the actual blob object.
        held,_,sources,_,_,_=self.fixture(sources)
        self.controls(held);stdout=self.stdout(sources,bodies)
        with self.assertRaisesRegex(ValueError,'object pin'):held.retain_raw(2,stdout,b'',b'receipt',exit_code=0)
        self.observe(held)

    def test_failed_exit_keeps_stdout_stderr_receipt_partial_and_rejects_second_call(self):
        held,_,_,_,clock,_=self.fixture();stdout=b'failed prefix';stderr=b'original error';receipt=b'literal receipt';partial=b'partial'
        with self.assertRaises(ValueError) as stopped:
            held.retain_raw(0,stdout,stderr,receipt,exit_code=17,partial=partial)
        original=held._SourceBatchContractPreparation__pending
        self.assertEqual(original['incoming'],(0,stdout,stderr,receipt,17,partial))
        self.assertEqual(json.loads(original['proof_raw'])['exit_code'],17)
        held.pending=None;held.error=None
        with self.assertRaises(ValueError) as again:held.retain_raw(1,b'',b'',b'r',exit_code=0)
        self.assertIs(again.exception,stopped.exception);self.assertIs(held._SourceBatchContractPreparation__pending,original)
        clock.assert_not_called();self.observe(held)

    def test_all_future_failure_maxima_refuse_before_any_pack_or_raw_return(self):
        held,raw,sources,limits,clock,_=self.fixture()
        limits=copy.deepcopy(limits)
        for item in limits:item.update(stdout=131072,stderr=16384,receipt=32768,partial=131072)
        candidate=batch.SourceBatchContractPreparation.__new__(batch.SourceBatchContractPreparation)
        with self.assertRaisesRegex(ValueError,'packed future raw byte bound'):
            candidate.__init__(owner=object(),checkpoint=clock,request_raw=raw,
                expected_sources=sources,raw_maxima=limits,storage_maxima=storage())
        self.assertEqual(candidate._SourceBatchContractPreparation__records,())
        self.assertIsNone(candidate._SourceBatchContractPreparation__pack);clock.assert_not_called()
        self.assertGreater(candidate.projection['packed_raw_bytes'],524288);self.observe(candidate)

    def test_partial_raw_and_new_growth_and_existing_snapshot_have_no_completed_discount(self):
        held,raw,sources,limits,clock,_=self.fixture();s=storage()
        s['archive_new_growth']['bytes']=524288;s['partial_raw']['bytes']=524288
        candidate=batch.SourceBatchContractPreparation.__new__(batch.SourceBatchContractPreparation)
        with self.assertRaisesRegex(ValueError,'full future storage bound'):
            candidate.__init__(owner=object(),checkpoint=clock,request_raw=raw,
                expected_sources=sources,raw_maxima=limits,storage_maxima=s)
        self.assertGreater(candidate.projection['bytes'],1048576)
        s=storage();s['snapshot']['entries']=4
        with self.assertRaisesRegex(ValueError,'full future storage bound'):
            batch.SourceBatchContractPreparation(owner=object(),checkpoint=clock,request_raw=raw,
                expected_sources=sources,raw_maxima=limits,storage_maxima=s)
        self.observe(candidate)

    def test_changed_source_roster_and_unplanned_extra_source_are_not_accepted(self):
        for mutation in ('changed','extra'):
            held,raw,sources,limits,clock,_=self.fixture();sources=copy.deepcopy(sources)
            if mutation=='changed':sources[0]['pin']['sha256']='f'*64
            else:sources.append(row('extra',b'x'))
            with self.assertRaisesRegex(ValueError,'exact source coverage'):
                batch.SourceBatchContractPreparation(owner=object(),checkpoint=clock,request_raw=raw,
                    expected_sources=sources,raw_maxima=limits,storage_maxima=storage())

    def test_git_batch_path_and_header_capacity_are_unambiguous(self):
        for name in ('src/banto_ai/../bad.py','src/banto_ai/a\nbad.py','src/banto_ai/a\\bad.py'):
            source=row('x',b'x');source['name']=name
            with self.assertRaises(ValueError):
                batch.source_batch_request_candidate(revision='1'*40,root='memory',sources=[source])
        source=row('big',b'x');source['pin']['bytes']=131072
        with self.assertRaisesRegex(ValueError,'header byte bound'):
            batch.source_batch_request_candidate(revision='1'*40,root='memory',sources=[source])
        sources=[row('s'+str(i),b'x') for i in range(17)]
        plan=json.loads(batch.source_batch_request_candidate(revision='1'*40,root='memory',sources=sources))
        self.assertEqual([len(g['members']) for g in plan['groups']],[16,1])

    def test_erased_record_alias_or_modified_private_candidate_never_replays_packing(self):
        for field in ('incoming','proof_raw','authority','request'):
            held,_,sources,_,_,bodies=self.fixture();self.controls(held)
            held.retain_raw(2,self.stdout(sources,bodies),b'',b'receipt',exit_code=0)
            record=held.records[-1]
            if field=='incoming':record['incoming']=None
            elif field=='proof_raw':record['proof_raw']=None
            elif field=='authority':record['native_authorized']=True
            else:held._SourceBatchContractPreparation__request['scope']['native_authorized']=True
            with self.assertRaises(ValueError):held.prepare_pack()
            self.assertIsNone(held._SourceBatchContractPreparation__pack);self.observe(held)

    def parent(self):
        return reader.ReaderGitParent.__new__(reader.ReaderGitParent)

    def attach(self,parent,clock):
        held,raw,sources,limits,_,_=self.fixture()
        parent.inventory_checkpoint=clock
        return parent.prepare_source_batch_contract(request_raw=raw,expected_sources=sources,
            raw_maxima=limits,storage_maxima=storage())

    def test_parent_cached_alias_erasure_cannot_replace_or_release_original_preparation(self):
        parent=self.parent();clock=Mock();held=self.attach(parent,clock)
        parent.source_batch_owner=None
        with self.assertRaises(ValueError):self.attach(parent,clock)
        self.assertIs(parent._ReaderGitParent__source_batch_owner,held)
        self.assertIs(held.rejected_preparation.owner,parent)
        with self.assertRaises(ValueError):parent._inventory_ready()
        clock.assert_not_called();self.observe(held)

    def test_parent_clock_getter_interruption_retains_original_inputs_before_getter(self):
        class Interrupted(reader.ReaderGitParent):
            @property
            def inventory_checkpoint(self):raise KeyboardInterrupt('clock getter')
        parent=Interrupted.__new__(Interrupted);_,raw,sources,limits,_,_=self.fixture()
        with self.assertRaises(KeyboardInterrupt):
            parent.prepare_source_batch_contract(request_raw=raw,expected_sources=sources,
                raw_maxima=limits,storage_maxima=storage())
        held=parent._ReaderGitParent__source_batch_owner
        self.assertIs(held.original_inputs[0],parent);self.assertIs(held.original_inputs[2],raw)
        self.assertIs(held.error.reader_git_parent,parent);self.observe(held)

    def test_same_parent_keeper_retains_batch_even_after_public_alias_erasure(self):
        parent=self.parent();held=self.attach(parent,Mock());parent.source_batch_owner=None
        parent.original_bootstrap_inputs=(None,)*11;parent.worker=None;parent.error=None
        error=ValueError('original caller failure')
        class Escape(BaseException):pass
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(error,parent)
        keeper=parent.original_publication_retention
        self.assertIs(keeper.parent,parent);self.assertIn(held,keeper.owners)
        self.assertIs(error.parent_publication_retention,keeper);self.observe(held)

    def test_execute_rejects_before_clock_and_without_clearing_private_raw(self):
        held,_,_,_,clock,_=self.fixture();self.controls(held)
        with self.assertRaises(ValueError):held.execute()
        self.assertEqual(len(held._SourceBatchContractPreparation__records),2)
        clock.assert_not_called();self.observe(held)

    def test_second_initialization_keeps_first_input_tuple_and_stops_redecoding(self):
        held,raw,sources,limits,clock,_=self.fixture();original=held.original_inputs
        with patch.object(batch.v,'strict_json') as decode,self.assertRaises(ValueError):
            held.__init__(owner=held.owner,checkpoint=clock,request_raw=raw,
                expected_sources=sources,raw_maxima=limits,storage_maxima=original[5])
        decode.assert_not_called();self.assertIs(held.original_inputs,original);self.observe(held)

    def test_changed_cached_packed_return_latches_first_error_without_repacking(self):
        held,_,sources,_,_,bodies=self.fixture();self.controls(held)
        raw=self.stdout(sources,bodies);held.retain_raw(2,raw,b'',b'receipt',exit_code=0)
        self.controls(held,(3,4));held.retain_raw(5,raw,b'',b'receipt',exit_code=0)
        original=held.prepare_pack();parts=held._SourceBatchContractPreparation__pack_parts
        held._SourceBatchContractPreparation__pack=(b'changed',original[1])
        with self.assertRaises(ValueError) as stopped:held.prepare_pack()
        held._SourceBatchContractPreparation__pack=original
        with self.assertRaises(ValueError) as again:held.prepare_pack()
        self.assertIs(again.exception,stopped.exception)
        self.assertIs(held._SourceBatchContractPreparation__pack_anchor,original)
        self.assertIs(held._SourceBatchContractPreparation__pack_parts,parts);self.observe(held)
