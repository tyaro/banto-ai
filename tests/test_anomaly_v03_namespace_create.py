"""Parent-share and path creation faults with fake native/ownership surfaces."""
import ctypes as C
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_namespace_create as ns
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_held_launch as launch
from tests import test_anomaly_v03_delete_matrix as deletes
from tests import test_anomaly_v03_directory_peer as peers
from tests import test_anomaly_v03_directory_acquisition as acquisition


class Child(deletes.Backend):
    def __init__(self,calls,hooks):
        super().__init__(False,calls,hooks)
        self._returned=False
        self.create_value=302
        self.create_code=0

    def create(self,cell):
        self.called=True
        self.hit("created")
        cell.handle=self.create_value
        self._returned=self.returned=True
        if not ns.rename._handle(cell.handle):
            self.hit("create_error")
            raise owned.OwnershipError("directory_create_failed",self.create_code)
        self.live=True


def setup(index=0,guard=None):
    calls,hooks=[],{}
    root=deletes.Backend(True,calls,hooks)
    child=Child(calls,hooks)
    peer=peers.Backend(root.observed,calls)
    if index==0:peer.results=[601,602,603,604]
    case=ns.CreationCase(ns.PLANS[index],root,child,peer,guard=guard or (lambda:None))
    return case,root,child,peer,calls,hooks


class CaseTests(unittest.TestCase):
    def test_peer_denial_and_successful_path_creation_are_independent_observations(self):
        case,root,child,peer,calls,hooks=setup(1)
        case.run()
        state=case.snapshot()
        self.assertEqual(state["child_create"],"accepted")
        self.assertEqual(state["peers"]["cases"][1]["state"],"denied")
        self.assertTrue(root.live)
        self.assertFalse(child.live or peer.live)
        self.assertLess(calls.index("peer_close"),calls.index("file_created"))
        self.assertLess(calls.index("file_close"),len(calls))
        case.finish_root()
        self.assertFalse(root.live)
        self.assertFalse(state["namespace_isolation_proven"])
        self.assertEqual(calls.count("file_created"),1)

    def test_classified_creating_denial_keeps_parent_and_does_not_inspect_failed_child(self):
        for code in (5,32):
            case,root,child,peer,calls,hooks=setup(1)
            child.create_value,child.create_code=ns.peer.INVALID,code
            with self.assertRaises(owned.OwnershipError):case.run()
            self.assertEqual(case.snapshot()["child_create"],"denied")
            self.assertEqual(case.snapshot()["create_winerror"],code)
            self.assertTrue(case.children_require_exit())
            self.assertTrue(root.live)
            self.assertNotIn("file_inspect",calls)
            self.assertNotIn("file_close",calls)
            with self.assertRaises(owned.OwnershipError):case.finish_root()
            self.assertNotIn("root_close",calls)

    def test_other_creating_failures_are_unknown_and_resource_errors_escalate(self):
        for value,code in ((None,0),(ns.peer.INVALID,80),(ns.peer.INVALID,8),(True,0)):
            case,root,child,peer,calls,hooks=setup()
            child.create_value,child.create_code=value,code
            with self.assertRaises(owned.OwnershipError):case.run()
            self.assertEqual(case._creation,"unknown")
            self.assertTrue(case.children_require_exit())
            self.assertEqual(case._resource,code==8)

    def test_create_response_loss_retains_input_and_parent_without_retry(self):
        case,root,child,peer,calls,hooks=setup()
        primary=MemoryError("create lost")
        hooks["file_created"]=acquisition.failing(primary)
        for operation in (case.run,case.finish_children,case.finish_children):
            with self.assertRaises(MemoryError) as caught:operation()
            self.assertIs(caught.exception,primary)
        self.assertEqual(calls.count("file_created"),1)
        self.assertTrue(root.live)
        self.assertEqual(child.descriptor,"retained_unknown")

    def test_child_inspection_failure_is_primary_and_closes_known_child_only(self):
        for phase in ("file_access","file_inspect"):
            case,root,child,peer,calls,hooks=setup()
            primary=ValueError(phase)
            hooks[phase]=acquisition.failing(primary)
            with self.assertRaises(ValueError) as caught:case.run()
            self.assertIs(caught.exception,primary)
            self.assertFalse(child.live)
            self.assertTrue(root.live)
            with self.assertRaises(ValueError):case.finish_root()
            self.assertFalse(root.live)
            self.assertEqual(calls.count("file_close"),1)

    def test_child_close_or_descriptor_free_unknown_blocks_root_close(self):
        for phase in ("file_close","file_free"):
            case,root,child,peer,calls,hooks=setup()
            hooks[phase]=acquisition.failing(ValueError(phase))
            with self.assertRaises(ValueError):case.run()
            self.assertTrue(case.children_require_exit())
            with self.assertRaises(owned.OwnershipError):case.finish_root()
            self.assertTrue(root.live)
            self.assertEqual(calls.count(phase),1)

    def test_peer_unknown_stops_before_any_child_create_and_keeps_root(self):
        for phase in ("peer_return","peer_close"):
            case,root,child,peer,calls,hooks=setup()
            peer.hooks[phase]=acquisition.failing(ValueError(phase))
            with self.assertRaises(ValueError):case.run()
            self.assertNotIn("file_created",calls)
            self.assertTrue(case.children_require_exit())
            self.assertTrue(root.live)

    def test_parent_identity_change_after_peers_prevents_creation(self):
        case,root,child,peer,calls,hooks=setup()
        original=root.observed
        peer.hooks["peer_closed"]=lambda:setattr(root,"observed",replace(original,descriptor=b"changed"))
        with self.assertRaises(owned.OwnershipError):case.run()
        self.assertNotIn("file_created",calls)

    def test_swallowed_case_reentry_latches_stop_at_native_and_cleanup_boundaries(self):
        for boundary in ("root_prepare","root_created","root_inspect","file_prepare","file_created","file_access","file_close","file_free"):
            for method in ("run","finish_children","finish_root"):
                case,root,child,peer,calls,hooks=setup()
                def reenter():
                    try:getattr(case,method)()
                    except BaseException:pass
                hooks[boundary]=reenter
                with self.subTest(boundary=boundary,method=method),self.assertRaises(BaseException):case.run()
                self.assertIsNotNone(case._error)
                self.assertLessEqual(calls.count("file_created"),1)
                self.assertLessEqual(calls.count("file_close"),1)

    def test_primary_and_later_resource_close_failure_keep_first_exception(self):
        case,root,child,peer,calls,hooks=setup()
        primary=ValueError("inspect")
        hooks["file_inspect"]=acquisition.failing(primary)
        hooks["file_close"]=acquisition.failing(MemoryError("close"))
        with self.assertRaises(ValueError) as caught:case.run()
        self.assertIs(caught.exception,primary)
        self.assertTrue(case._resource)
        self.assertTrue(case.children_require_exit())


class Context(ns.NamespaceContext):
    def __init__(self):
        super().__init__(Path.cwd()/"namespace-fake-unused","a"*40)
        self.events=[]
        self.parts=None
        self.hooks={}
        self.sink.token_basis={"type":1,"elevated":0}

    def hit(self,phase):
        self.events.append(phase)
        if phase in self.hooks:return self.hooks[phase]()

    def connect(self):
        self.sink._started=self.sink._connected=True
        self.hit("connect")

    def prepare(self,guard):
        self.parts=[setup(i,guard) for i in range(2)]
        self.reader=ns.CreationMatrix(tuple(p[0] for p in self.parts),guard)
        self.hit("prepare")

    def guard(self):
        return self.hit("guard")

    def persist_collection(self,state):
        self.saved=json.loads(json.dumps(state))
        return self.hit("persist")

    def close_ancestors(self,*,primary=None):
        self.hit("ancestors")
        return super().close_ancestors(primary=primary)


class DriverTests(unittest.TestCase):
    def test_parent_create_error_reaches_single_worker_report_without_child_calls(self):
        ctx=Context();writes=[]
        primary=owned.OwnershipError("directory_create_failed",87)
        ctx.hooks["prepare"]=lambda:ctx.parts[0][5].update(root_created=acquisition.failing(primary))
        with patch.object(launch,"_LIVE_WORKER",None):
            code=launch.execute(ctx,"a"*40,"b"*64,10,lambda fd,raw:writes.append(raw) or len(raw))
        self.assertEqual(code,81)
        self.assertEqual(len(writes),1)
        state=json.loads(writes[0])
        first,second=state["context"]["reader"]["cases"]
        self.assertEqual(first["parent_create_winerror"],87)
        self.assertIsNone(second["parent_create_winerror"])
        self.assertEqual(first["child_create"],"not_started")
        self.assertTrue(state["retained_for_worker_exit"])
        self.assertNotIn("persist",ctx.events)
        self.assertNotIn("ancestors",ctx.events)
        self.assertFalse(ctx.parts[1][1].called)

    def test_two_cases_keep_both_roots_until_persist_and_confirm_terminal_closes(self):
        ctx=Context()
        ctx.hooks["persist"]=lambda:self.assertTrue(all(p[1].live for p in ctx.parts))
        driver=ns.terminal.HeldDriver(ctx)
        driver.run()
        self.assertEqual(driver.exit_code(),0)
        self.assertFalse(any(p[1].live or p[2].live or p[3].live for p in ctx.parts))
        self.assertEqual(ctx.saved["collection"],"complete")
        self.assertFalse(ctx.saved["consumer_payload_released"])
        report=json.loads(driver.report_bytes())
        self.assertEqual(len(report["context"]["reader"]["cases"]),2)

    def test_first_case_failure_prevents_second_case_native_calls(self):
        ctx=Context()
        ctx.hooks["prepare"]=lambda:ctx.parts[0][5].update(file_created=acquisition.failing(ValueError("create")))
        driver=ns.terminal.HeldDriver(ctx)
        with self.assertRaises(ValueError):driver.run()
        self.assertEqual(driver.exit_code(),81)
        self.assertFalse(ctx.parts[1][1].called)
        self.assertNotIn("persist",ctx.events)
        self.assertNotIn("ancestors",ctx.events)

    def test_matrix_reentry_cannot_be_swallowed_into_success(self):
        for mode in ("run","finish"):
            ctx=Context()
            def install():
                def reenter():
                    try:
                        if mode=="run":ctx.reader.run()
                        else:ctx.reader._finish("finish_children",None)
                    except BaseException:pass
                ctx.parts[0][5]["file_created"]=reenter
            ctx.hooks["prepare"]=install
            driver=ns.terminal.HeldDriver(ctx)
            with self.assertRaises(owned.OwnershipError):driver.run()
            self.assertNotEqual(driver.exit_code(),0)

    def test_lifetime_query_error_retains_roots_and_promotes_secondary_resource(self):
        ctx=Context()
        primary=ValueError("save")
        def persist():
            ctx.reader.children_require_exit=acquisition.failing(MemoryError("state"))
            raise primary
        ctx.hooks["persist"]=persist
        driver=ns.terminal.HeldDriver(ctx)
        with self.assertRaises(ValueError) as caught:driver.run()
        self.assertIs(caught.exception,primary)
        self.assertEqual(driver.exit_code(),80)
        self.assertTrue(all(p[1].live for p in ctx.parts))
        self.assertNotIn("ancestors",ctx.events)

    def test_root_close_failure_stops_ancestor_release(self):
        ctx=Context()
        ctx.hooks["prepare"]=lambda:ctx.parts[1][5].update(root_close=acquisition.failing(ValueError("root close")))
        driver=ns.terminal.HeldDriver(ctx)
        with self.assertRaises(ValueError):driver.run()
        self.assertEqual(driver.exit_code(),81)
        self.assertNotIn("ancestors",ctx.events)

    def test_actual_context_persists_only_case_metadata_and_profile(self):
        ctx=Context();driver=ns.terminal.HeldDriver(ctx)
        stored=[]
        ctx.sink.persist_evidence=lambda *args:stored.append(args)
        ctx.persist_collection=lambda state:ns.NamespaceContext.persist_collection(ctx,state)
        driver.run()
        self.assertEqual(driver.exit_code(),0)
        self.assertEqual(stored[0][0],"prepare")
        report=json.loads(stored[0][1])
        self.assertEqual(report["initial_token_basis"],ctx.sink.token_basis)
        self.assertNotIn("bytes_b64",stored[0][1].decode())

    def test_existing_launcher_carries_namespace_scope_and_single_report(self):
        ctx=Context();writes=[]
        with patch.object(launch,"_LIVE_WORKER",None):
            code=launch.execute(ctx,"a"*40,"b"*64,10,lambda fd,raw:writes.append(raw) or len(raw),
                                scope="namespace path creation engineering attempt")
        self.assertEqual(code,0)
        self.assertEqual(len(writes),1)
        self.assertEqual(json.loads(writes[0])["scope"],"namespace path creation engineering attempt")


class BackendTests(unittest.TestCase):
    def test_captured_parent_native_error_is_preserved_without_a_new_error_query(self):
        for code in (5,32,87,183):
            api=acquisition.FakeApi();api.value=ns.peer.INVALID
            surface=SimpleNamespace(_SA=acquisition.win._SA,D=acquisition.win.D,_dacl=acquisition.win._dacl,
                _verify_sd=acquisition.win._verify_sd,_Bound=acquisition.BorrowedView)
            with patch.object(ns.acq.os,"name","nt"),patch.object(ns.acq.sys,"version_info",(3,14,0)), \
                 patch.object(ns.acq,"Path",lambda p:p),patch.object(C,"get_last_error",return_value=code,create=True) as last_error:
                parent=ns.ParentBackend(surface,api,path=acquisition.PATH,user=acquisition.USER,share=3)
                _,_,child,_,calls,_=setup()
                case=ns.CreationCase(ns.PLANS[0],parent,child,ns.ParentPeers(parent),guard=lambda:None)
                with self.assertRaises(owned.OwnershipError):case.run()
                self.assertEqual(case.snapshot()["parent_create_winerror"],code)
                self.assertTrue(case.root_requires_exit())
                self.assertNotIn("file_created",calls)
                last_error.assert_called_once()
                self.assertEqual(api.calls.count("create"),1)
                self.assertNotIn("observe",api.calls)

    def test_parent_share_changes_only_the_share_argument(self):
        for share in (1,3):
            api=acquisition.FakeApi()
            surface=SimpleNamespace(_SA=acquisition.win._SA,D=acquisition.win.D,_dacl=acquisition.win._dacl,
                _verify_sd=acquisition.win._verify_sd,_Bound=acquisition.BorrowedView)
            with patch.object(ns.acq.os,"name","nt"),patch.object(ns.acq.sys,"version_info",(3,14,0)), \
                 patch.object(ns.acq,"Path",lambda p:p):
                backend=ns.ParentBackend(surface,api,path=acquisition.PATH,user=acquisition.USER,share=share)
                holder=ns.acq.DirectoryAcquisition(backend,guard=lambda:None)
                holder.acquire()
                self.assertEqual(api.arguments[:4],(acquisition.PATH,ns.acq.ROOT_ACCESS,share,1))
                holder.finish()
                self.assertFalse(api.live)

    def test_peer_adapter_requests_existing_parent_and_full_share_noninheritance(self):
        calls=[]
        parent=SimpleNamespace(_path=Path("fresh-case"),_api=SimpleNamespace(k=SimpleNamespace(
            CreateFileW=lambda *args:calls.append(args) or 601)))
        backend=ns.ParentPeers(parent)
        backend.open_existing(0x120082)
        self.assertEqual(calls[0],("fresh-case",0x120082,7,None,3,0x02200000,None))

    def test_profiled_sink_keeps_deferred_finish(self):
        sink=ns.RetainedProfiledSink()
        calls=[];sink._leases=[SimpleNamespace(close=lambda:calls.append(1))]
        sink.finish()
        self.assertFalse(calls)


if __name__=="__main__":unittest.main()
