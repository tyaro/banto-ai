"""Small ordinary temp publications; invented metadata, no numerical payloads."""
import copy
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_checkpoints as journal
from banto_ai import anomaly_v03_checkpoint_store as store
from banto_ai import anomaly_v03_attempt_descriptor as descriptor
from banto_ai import anomaly_v03_consumer_checkpoints as adapter
from banto_ai import anomaly_v03_consumer_publication as reader
from banto_ai import anomaly_v03_chunk_contract as contract
from banto_ai import _anomaly_v03_io as storage
from tests import test_anomaly_v03_consumer_checkpoints as fixtures


def sha(raw): return hashlib.sha256(raw).hexdigest()
def raw(value): return v.canonical_json(value) + b'\n'


class PublicationReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ConsumerCheckpointTests.setUpClass()
        cls.fixture = fixtures.ConsumerCheckpointTests.baseline
        cls.normal = cls.blueprint()

    @classmethod
    def blueprint(cls, *, marker_change=None, producer_change=None, monitor_change=None):
        f, entries = copy.deepcopy(cls.fixture)
        manifest = entries[-1]['manifest']
        manifest_raw = raw(manifest)
        inventory = [storage.payload_entry('manifest.json',manifest_raw)]
        files = [entry for dataset in manifest['datasets'] for entry in dataset['files']]
        files += [row['evaluation'] for row in manifest['slots']]
        inventory += [{'path':entry['path'],'raw_sha256':entry['sha256'],
                       'canonical_sha256':fixtures.digest(entry['path']), 'row_count':1} for entry in files]
        inventory.sort(key=lambda x:x['path'])
        marker = {'schema_version':'0.3','marker_type':'anomaly-v03-local-complete','payload_inventory':inventory,
                  'inventory_sha256':v.canonical_sha256(inventory),'native_acceptance':'not_completed','performance_status':'not_evaluated'}
        if marker_change: marker_change(marker)
        marker['inventory_sha256'] = v.canonical_sha256(marker['payload_inventory'])
        runtime = copy.deepcopy(f.context['runtime'])
        producer = {'format':'anomaly-v03-chunk-supervision-v1','policy_id':'anomaly-v03-single-writer-v1',
            'scope':contract.SCOPE,'attempt_id':'result','binding':manifest['plan']['binding'],
            'status':'complete','exit_code':0,'worker_exit_confirmed':True,'stop_reason':None,'observation_errors':[],
            'formal_permission':False,'performance_status':'not_evaluated',
            'resource_measurement_scope':'whole_worker_including_replays_and_exit','runtime':runtime,
            'runtime_after':copy.deepcopy(runtime),'elapsed_seconds':1.0,'peak_worker_private_bytes':1024}
        if producer_change: producer_change(producer)
        monitor = {'format':'anomaly-v03-owned-process-monitor-v1','status':'complete','exit_code':0,
            'worker_exit_confirmed':True,'stop_reason':None,'observation_errors':[],'formal_permission':False,
            'performance_status':'not_evaluated','runtime_before':runtime,'runtime_after':copy.deepcopy(runtime),
            'output':{'bytes':1,'sha256':f.records[-1]['evidence']['audit_sha256']},
            'stderr':{'bytes':0,'sha256':sha(b'')},'limits':{'wall_seconds':600,'private_bytes':1024**3,'output_bytes':8*1024**2},
            'elapsed_seconds':1.0,'peak_worker_private_bytes':1024}
        if monitor_change: monitor_change(monitor)
        role_raw = {'marker':raw(marker),'producer_supervision':raw(producer),'audit_supervision':raw(monitor)}
        for record in f.records[-2:]: record['evidence']['marker_sha256'] = sha(role_raw['marker'])
        f.records[-1]['evidence']['supervision_sha256'] = sha(role_raw['producer_supervision'])
        f.rechain()
        layout = descriptor._layout(f.records[-1])
        artifacts = {role:{'path':layout['files'][role],'bytes':len(data),'sha256':sha(data)} for role,data in role_raw.items()}
        artifacts['audit_report'] = {'path':layout['files']['audit_report'],'bytes':1,
                                    'sha256':f.records[-1]['evidence']['audit_sha256']}
        desc = descriptor.new_descriptor(f.plan,f.records,artifacts,audit_runtime={'before':runtime,'after':runtime},
            expected_plan_sha256=f.plan_hash,expected_record_count=len(f.records),expected_head_sha256=f.head)
        adapted = adapter.adapt_completed_journal(f.plan,f.records,entries,expected_mode=adapter.MODE,
            expected_plan_sha256=f.plan_hash,expected_record_count=len(f.records),expected_head_sha256=f.head,
            expected_manifests_sha256=v.canonical_sha256(entries))
        paths = {'metadata/journal/000362.json':journal.encode_record(f.records[-1]),
                 'attempts/'+layout['descriptor_path']:raw(desc),
                 'attempts/'+layout['result_root']+'/payload/manifest.json':manifest_raw}
        paths.update({'attempts/'+layout['files'][role]:data for role,data in role_raw.items()})
        return f, adapted, paths, desc

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-consumer-reader-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.install(self.normal)

    def install(self, blueprint):
        self.f,self.adapted,files,self.desc = copy.deepcopy(blueprint)
        self.stem = 'attempts/chunks/119/attempt-0002/'
        complete = self.root/self.stem/'result/.complete'
        if complete.exists(): complete.unlink()
        pending = self.root/self.stem/'result/marker-pending.json'
        for name,data in files.items():
            path = self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        pending.write_bytes(complete.read_bytes());complete.unlink();os.link(pending,complete)
        descriptor_pins = {str(row['attempts'][-1]['record_sequences'][-1]):fixtures.digest(str(row['chunk_index']))
                           for row in self.adapted['chunks']}
        descriptor_pins['362'] = sha(files[self.stem+'descriptors/000362.json'])
        self.closed = {'format':'anomaly-v03-closed-invocation-v1','sequence':10,'status':'completed','stop_reason':None,
            'request_sha256':'a'*64,'previous_state_sha256':'b'*64,'elapsed_seconds_total':1.0,'formal_permission':False,
            'checkpoint':{'descriptor_pins':descriptor_pins,
                          'receipt':store._receipt(self.root/'metadata',self.f.plan_hash,362,self.f.head)}}
        self.save_closed()

    def save_closed(self):
        path = self.root/'control/000010/closed.json';path.parent.mkdir(parents=True,exist_ok=True)
        data=raw(self.closed);path.write_bytes(data);self.closed_hash=sha(data)

    def call(self, **overrides):
        args={'expected_mode':adapter.MODE,'expected_adapter_sha256':v.canonical_sha256(self.adapted),
              'chunk_index':119,'closed_sequence':10,'expected_closed_sha256':self.closed_hash} | overrides
        return reader.read_chunk_publication(self.root,self.f.plan,self.adapted,**args)

    def test_eight_metadata_reads_bind_retry_without_claiming_payload_or_process_exit(self):
        before=v.canonical_sha256([self.f.plan,self.adapted])
        allowed={self.root/name for name in self.normal[2]} | {self.root/self.stem/'result/marker-pending.json',self.root/'control/000010/closed.json'}
        opened=[];original=Path.open
        def guarded(path,*args,**kwargs):
            self.assertIn(path,allowed);self.assertEqual(args,('rb',));opened.append(path)
            return original(path,*args,**kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path,'open',guarded))
            for target in ('subprocess.Popen','banto_ai.anomaly_v03_materializer.materialize_pair',
                           'banto_ai.anomaly_v03_chunk_contract.audit_chunk_payloads','banto_ai._anomaly_v03_io.read_tree'):
                stack.enter_context(patch(target,side_effect=AssertionError('forbidden')))
            out=self.call()
        self.assertEqual(len(opened),8);self.assertEqual(len(set(opened)),8)
        self.assertEqual((out['chunk_index'],out['attempt'],out['evaluations']),(119,2,6))
        for key in ('publication_metadata_verified','manifest_bytes_verified','worker_exit_records_verified','controller_closure_record_verified'):
            self.assertIs(out[key],True)
        for key in ('controller_process_exit_verified','full_payload_bytes_verified','audit_report_bytes_verified','publication_verified',
                    'source_runtime_accepted','result_trusted','analysis_authorized','execution_authorized','formal_permission'):
            self.assertIs(out[key],False)
        self.assertEqual(v.canonical_sha256([self.f.plan,self.adapted]),before)
        self.assertEqual(len(self.adapted['failed_attempt_history']),1)

    def test_formal_and_invalid_selection_fail_before_filesystem_access(self):
        with patch.object(reader.paths,'regular_path',side_effect=AssertionError('IO')):
            for bad in ({'expected_mode':'formal'},{'expected_mode':'fixture'},{'chunk_index':True},
                        {'chunk_index':120},{'closed_sequence':True},{'closed_sequence':0}):
                with self.subTest(bad=bad),self.assertRaises(ValueError):self.call(**bad)

    def test_external_adapter_and_closed_hash_required(self):
        for bad in ({'expected_adapter_sha256':'0'*64},{'expected_closed_sha256':'0'*64}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.call(**bad)

    def test_plan_binding_is_not_inferred_from_manifest(self):
        self.f.plan['source_bindings']['producer_revision']='f'*40
        with self.assertRaises(ValueError):self.call()

    def test_closed_status_root_journal_and_descriptor_inventory_are_bound(self):
        original=copy.deepcopy(self.closed)
        changes=[lambda c:c.update(status='stopped'),lambda c:c['checkpoint']['receipt'].update(root=str(self.root/'other')),
            lambda c:c['checkpoint']['receipt']['journal'].update(expected_record_count=361),
            lambda c:c['checkpoint']['descriptor_pins'].pop('3')]
        for change in changes:
            self.closed=copy.deepcopy(original);change(self.closed);self.save_closed()
            with self.subTest(change=change),self.assertRaises(ValueError):self.call()

    def test_descriptor_cannot_redirect_to_another_attempt_even_when_pinned(self):
        self.desc['layout']['files']['marker']='chunks/119/attempt-0001/result/.complete'
        data=raw(self.desc);(self.root/self.stem/'descriptors/000362.json').write_bytes(data)
        self.closed['checkpoint']['descriptor_pins']['362']=sha(data);self.save_closed()
        with self.assertRaises(ValueError):self.call()

    def test_changed_marker_or_manifest_bytes_rejected(self):
        for relative in ('result/.complete','result/payload/manifest.json'):
            with self.subTest(relative=relative):
                path=self.root/self.stem/relative;data=path.read_bytes();path.write_bytes(data+b' ')
                with self.assertRaises(ValueError):self.call()
                path.write_bytes(data)

    def test_marker_scope_duplicate_inventory_and_file_reference_mismatch_rejected(self):
        changes=[lambda m:m.update(marker_type='anomaly-v03-fixture-complete'),
                 lambda m:m['payload_inventory'].append(copy.deepcopy(m['payload_inventory'][0])),
                 lambda m:m['payload_inventory'][0].update(raw_sha256='0'*64)]
        for change in changes:
            self.install(self.blueprint(marker_change=change))
            with self.subTest(change=change),self.assertRaises(ValueError):self.call()

    def test_separate_equal_marker_files_are_not_the_commit_hardlink(self):
        complete=self.root/self.stem/'result/.complete';data=complete.read_bytes();complete.unlink();complete.write_bytes(data)
        os.link(complete,self.root/'extra-complete');os.link(self.root/self.stem/'result/marker-pending.json',self.root/'extra-pending')
        with self.assertRaisesRegex(ValueError,'hardlink identity'):self.call()

    def test_missing_marker_extra_control_and_multilink_manifest_rejected(self):
        extra=self.root/self.stem/'result/extra';extra.write_bytes(b'x')
        with self.assertRaises(ValueError):self.call()
        extra.unlink()
        os.link(self.root/self.stem/'result/payload/manifest.json',self.root/'alias')
        with self.assertRaises(ValueError):self.call()
        (self.root/'alias').unlink();(self.root/self.stem/'result/.complete').unlink()
        with self.assertRaises(ValueError):self.call()

    def test_producer_exit_false_nonzero_or_different_runtime_rejected(self):
        for change in (lambda x:x.update(worker_exit_confirmed=False),lambda x:x.update(exit_code=1),
                       lambda x:x['runtime_after'].update(os_ubr=9457)):
            self.install(self.blueprint(producer_change=change))
            with self.subTest(change=change),self.assertRaises(ValueError):self.call()

    def test_audit_exit_output_runtime_and_limits_rejected(self):
        for change in (lambda x:x.update(worker_exit_confirmed=1),lambda x:x['output'].update(sha256='0'*64),
                       lambda x:x['runtime_after'].update(os_ubr=9457),lambda x:x.update(elapsed_seconds=601)):
            self.install(self.blueprint(monitor_change=change))
            with self.subTest(change=change),self.assertRaises(ValueError):self.call()

    def test_oversize_control_rejected_before_open(self):
        path=self.root/'oversized';data=b'x'*(reader.MAX_CONTROL+1);path.write_bytes(data)
        with patch.object(Path,'open',side_effect=AssertionError('oversize opened')),self.assertRaises(ValueError):
            reader._read(path,sha(data),reader.MAX_CONTROL)

    def test_parent_traversal_root_rejected(self):
        self.root=self.root/'unused'/'..'
        with self.assertRaises(ValueError):self.call()


if __name__=='__main__':unittest.main()
