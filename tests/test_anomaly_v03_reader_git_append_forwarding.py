"""New pinned append context through real callers; fake native, no worker launch."""
import copy
from pathlib import Path
from unittest.mock import patch
import unittest

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_reader_git_plan_forwarding as plans
from tests import test_anomaly_v03_reader_git_parent_connection as callers
from tests import test_anomaly_v03_worker_git_pipe_actor as pipes

archive=reader.actors.archive


class ReaderGitAppendForwardingTests(unittest.TestCase):
    def setUp(self):
        self.controls={name:32768 for name in archive.ArchiveAppendAdmission.CONTROL_NAMES}
        self.limits={operation:{'receipt.json':16384,'stdout.bin':maximum,'stderr.bin':16384,
            'partial-archive.bin':65536} for operation,maximum in
            (('head',128),('status',65536),('source_blob',131072))}

    def fixture(self, kind):
        f=kind();f.setUp();self.addCleanup(f.doCleanups);return f

    def plan(self):
        f=self.fixture(plans.ReaderGitPlanForwardingTests)
        f.value.update(format=whole.READER_APPEND_PLAN_FORMAT,pipe_raw_limits=copy.deepcopy(self.limits),
                       append_control_limits=copy.deepcopy(self.controls))
        f.entry=f.save(f.value);return f

    def parent(self):
        f=self.fixture(callers.ReaderGitParentControllerTests)
        return f,f.create(pipe_raw_limits=self.limits,append_control_limits=self.controls)

    def worker(self, f, parent, entry=None, **options):
        parent.bind(f.f.process);f.f.current=f.f.child_id
        return reader.ReaderGitWorker(parent.entry if entry is None else entry,
            revision=f.f.revision,repository=f.f.root,names=f.names,
            pipe_io=options.get('pipe_io',{'kernel':object(),'stdin':object()}))

    def test_v3_external_pin_resolves_closed_controls_without_relabelling_v1_or_v2(self):
        f=self.plan();resolved=f.load()
        self.assertEqual(resolved['append_control_limits'],self.controls)
        resolved['append_control_limits'].clear();self.assertEqual(f.load()['append_control_limits'],self.controls)
        variants=[]
        for fmt in (whole.READER_PLAN_FORMAT,whole.READER_PIPE_PLAN_FORMAT):
            value=copy.deepcopy(f.value);value['format']=fmt;variants.append(value)
        for field in ('append_control_limits','pipe_raw_limits'):
            value=copy.deepcopy(f.value);value.pop(field);variants.append(value)
        for value in variants:
            with self.subTest(value=value),self.assertRaises(ValueError):f.load(f.save(value))
        self.assertFalse(f.f.outer.exists())

    def test_changed_control_raw_denies_original_external_pin_before_source_io(self):
        f=self.plan();value=copy.deepcopy(f.value);value['append_control_limits']['ack.json']=100
        Path(f.entry['path']).write_bytes(whole.generated.v.canonical_json(value))
        with patch.object(reader,'selected_source') as selected,self.assertRaises(ValueError):f.load()
        selected.assert_not_called();self.assertFalse(f.f.outer.exists())

    def test_upper_clock_reread_forwards_same_controls_and_original_linked_budget(self):
        f=self.plan();result,generated,_=f.execute()
        generated.assert_called_once();self.assertEqual(f.forwarded['reader_git_plan']['append_control_limits'],self.controls)
        self.assertEqual(result['reader_git_plan_pin'],f.entry['expected_pin'])
        self.assertEqual(f.forwarded['outer_budget'].outer.roots['outer'],f.f.outer)
        self.assertEqual(result['status'],'failed');self.assertFalse(result['formal_permission'])

    def test_real_generate_copies_controls_before_profile_io_then_forwards_to_parent(self):
        f=self.fixture(callers.ReaderGitCallerConnectionTests)
        f.plan.update(pipe_raw_limits=copy.deepcopy(self.limits),append_control_limits=copy.deepcopy(self.controls))
        snapshot=copy.deepcopy(f.plan);original=whole.generated.validate_runtime_profiles
        def profiles(*args,**kwargs):f.plan.clear();return original(*args,**kwargs)
        with patch.object(whole.generated,'validate_runtime_profiles',side_effect=profiles):result,calls=f.execute()
        self.assertEqual(calls,['producer','initial-reader']);self.assertEqual(result['status'],'verified')
        self.assertEqual(f.create.call_args.kwargs['append_control_limits'],snapshot['append_control_limits'])
        self.assertEqual(f.create.call_args.kwargs['pipe_raw_limits'],snapshot['pipe_raw_limits'])
        self.assertEqual(f.plan,{});self.assertFalse(result['execution_authenticated'])

    def test_invalid_controls_refuse_real_generate_before_both_supervisors(self):
        f=self.fixture(callers.ReaderGitCallerConnectionTests)
        f.plan.update(pipe_raw_limits=self.limits,append_control_limits=copy.deepcopy(self.controls))
        f.plan['append_control_limits']['ack.json']=True
        result,calls=f.execute();self.assertEqual(result['status'],'failed');self.assertEqual(calls,[])
        f.create.assert_not_called();self.assertFalse(result['formal_permission'])

    def test_parent_holds_controls_before_io_and_binds_new_entry_to_exact_sixty_four_calls(self):
        f=self.fixture(callers.ReaderGitParentControllerTests);expected=copy.deepcopy(self.controls)
        f.shared.require_stage.side_effect=lambda *_:self.controls.clear()
        parent=f.create(pipe_raw_limits=self.limits,append_control_limits=self.controls)
        context=parent.entry['append_plan'];value=context['value']
        self.assertEqual(parent.entry['format'],reader.APPEND_ENTRY_FORMAT)
        self.assertEqual(value['control_limits'],expected);self.assertEqual(parent.append_controls,expected)
        self.assertEqual(context['pin'],reader.observed._pin(reader.io.json_bytes(value)))
        self.assertEqual(value['request_pin'],parent.parent.request_pin)
        self.assertEqual(value['inventory_pin'],parent.entry['inventory_pin'])
        self.assertEqual(value['budget_root_identity'],parent.entry['budget_root_identity'])
        self.assertEqual(len(reader.v.strict_json(Path(parent.entry['inventory_path']).read_bytes())['calls']),64)
        self.assertFalse((f.f.measured/'worker-git.bin').exists());self.assertIs(parent.shared,f.shared)

    def test_reader_copies_entry_before_channel_io_and_binds_same_checkpoint_to_writer(self):
        f,parent=self.parent();original=reader.channel.ChildChannel;entry=parent.entry
        def mutate(*args,**kwargs):entry['append_plan']['value']['control_limits'].clear();return original(*args,**kwargs)
        with patch.object(reader.channel,'ChildChannel',side_effect=mutate):
            # The actor isinstance check needs the original class after construction.
            with patch.object(reader.actors,'WorkerGitActor',wraps=reader.actors.WorkerGitActor) as actor:
                real_actor=actor._mock_wraps
                def create(**kwargs):
                    with patch.object(reader.channel,'ChildChannel',original):return real_actor(**kwargs)
                actor.side_effect=create
                worker=self.worker(f,parent)
        gate=worker.actor.append_admission
        self.assertEqual(gate.control_limits,self.controls);self.assertIs(gate.checkpoint,worker.actor.checkpoint)
        self.assertIs(worker.actor.writer.append_admission,gate);self.assertIs(gate.writer.verifier,worker.actor.verifier)
        self.assertEqual(gate.inventory_pin,parent.entry['inventory_pin']);self.assertEqual(gate.identity,worker.identity)
        self.assertEqual(worker.child.finished,0);self.assertIsNone(worker.actor.pending)
        self.assertFalse((worker.child.root/'ack.json').exists())

    def test_new_entry_requires_borrowed_pipe_and_valid_context_pin_before_channel_io(self):
        f,parent=self.parent()
        for enabled,tamper in ((False,False),(True,True)):
            entry=copy.deepcopy(parent.entry)
            if tamper:entry['append_plan']['value']['control_limits']['ack.json']=1
            with self.subTest(enabled=enabled,tamper=tamper),patch.object(reader.channel,'ChildChannel') as child, \
                 self.assertRaises(ValueError):
                reader.ReaderGitWorker(entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                    pipe_io={'kernel':object(),'stdin':object()} if enabled else None)
            child.assert_not_called();self.assertFalse((f.f.measured/'worker-git.bin').exists())

    def test_same_pinned_context_cannot_bind_foreign_request_inventory_or_root(self):
        f,parent=self.parent();parent.bind(f.f.process);f.f.current=f.f.child_id
        for field,value in (('request_pin',reader.observed._pin(b'foreign request')),
                            ('inventory_pin',reader.observed._pin(b'foreign inventory')),
                            ('budget_root_identity',[1,2]),('formal_permission',True)):
            entry=copy.deepcopy(parent.entry);entry['append_plan']['value'][field]=value
            entry['append_plan']['pin']=reader.observed._pin(reader.io.json_bytes(entry['append_plan']['value']))
            with self.subTest(field=field),patch.object(reader.actors,'WorkerGitActor') as actor,self.assertRaises(ValueError):
                reader.ReaderGitWorker(entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                    pipe_io={'kernel':object(),'stdin':object()})
            actor.assert_not_called();self.assertFalse((f.f.measured/'worker-git.bin').exists())

    def test_invalid_parent_controls_deny_before_live_clock_channel_or_inventory_publication(self):
        f=self.fixture(callers.ReaderGitParentControllerTests)
        for field,value in (('ack.json',0),('ack.json',True),('ack.json',32769),('unknown.json',1)):
            controls=copy.deepcopy(self.controls);controls[field]=value
            with self.subTest(value=value),patch.object(reader.channel.ParentChannel,'create') as create, \
                 self.assertRaises(ValueError):f.create(pipe_raw_limits=self.limits,append_control_limits=controls)
            create.assert_not_called();f.shared.require_stage.assert_not_called();self.assertFalse(f.root.exists())

    def test_new_actor_gate_observes_pipe_raw_archive_before_exact_lease_without_authorizing_ack(self):
        g=self.fixture(pipes.WorkerGitPipeActorTests);f=g.f
        f.inventory['calls']=[dict(lease=0,phase='pre',operation='source_blob',
            source_path='src/banto_ai/anomaly_v03.py',expected_output_pin=reader.observed._pin(b'abc'),
            raw_inventory={'receipt.json':16384,'stdout.bin':32,'stderr.bin':16})]
        f.configure();st=f.measured.stat();identity=(st.st_dev,st.st_ino)
        context={'format':archive.APPEND_PLAN_FORMAT,'revision':f.revision,'request_pin':f.child.request_pin,
            'inventory_pin':f.verifier.inventory_pin,'budget_root':str(f.measured),
            'budget_root_identity':list(identity),'control_limits':self.controls,'formal_permission':False}
        actor=reader.actors.WorkerGitActor(child=f.child,inventory_raw=reader.io.json_bytes(f.inventory),
            inventory_pin=f.verifier.inventory_pin,checkpoint=g.checkpoint,
            pipe_io={'kernel':g.g.kernel,'stdin':g.g.stdin,'clock':g.g.clock,'root_identity':identity},
            append_plan={'value':context,'pin':reader.observed._pin(reader.io.json_bytes(context))})
        g.actor=actor
        with patch.object(reader.tree,'run_owned',side_effect=AssertionError('no bare fallback')):
            self.assertEqual(g.call(),b'abc')
        self.assertEqual(f.child.finished,1);self.assertEqual(actor.saved.statuses,['verified'])
        self.assertEqual(len(actor.append_admission.completed),1)
        row=actor.append_admission.completed[0];self.assertFalse(row['atomic_reservation'])
        self.assertFalse(row['parent_ack_authorized']);self.assertFalse(row['execution_authenticated'])
        self.assertFalse((f.child.root/'ack.json').exists());self.assertFalse(actor.inflight.exists())


if __name__=='__main__':unittest.main()
