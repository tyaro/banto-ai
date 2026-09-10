"""Fake-only four-site bcrypt failure observation and owned termination."""
import ctypes as C
import hashlib
import struct
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from tests import test_anomaly_v03_debug_bootstrap as bootstrap_fixtures
from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
from tests.fixtures.anomaly_v03_debug_bcrypt_failure import DebugBcryptFailure as Probe
from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret
from tests.fixtures.anomaly_v03_debug_transport import DBG_CONTINUE, DBG_NOT_HANDLED, TransportError


class BcryptFailureTests(unittest.TestCase):
    BASE, MODULE, RSP = 0x40000000, 0x50000000, 0x30000

    def fixture(self, scope, *, site=0, value=5, hit=True):
        o,api,k,fixture,memory=bootstrap_fixtures.BootstrapTests().fixture(scope,bcrypt_failure=True)
        p=o.context; regs=[0]*6
        windows=[]
        for rva,size,digest in Probe.WINDOWS:
            code=b"X"*size
            memory[self.MODULE+rva]=code
            windows.append((rva,size,hashlib.sha256(code).hexdigest()))
        scope.enter_context(patch.object(Probe,"WINDOWS",tuple(windows)))
        memory[self.RSP+0x48]=struct.pack("<Q",self.MODULE+Probe.CALLER_RVA)
        events=iter((3,6,6,1,1,5) if hit else (3,6,6,1,5))
        last=[None]; exceptions=[0]
        def deliver(pointer,timeout):
            raw=pointer.contents
            raw.kind,raw.pid,raw.tid=next(events),17,19
            last[0]=raw.kind
            if raw.kind==3:raw.info.create_process.file=101
            elif raw.kind==6:
                first=o.images.count==1
                raw.info.load_dll.file=102 if first else 103
                raw.info.load_dll.base=self.BASE if first else self.MODULE
            elif raw.kind==1:
                exceptions[0]+=1
                info=raw.info.exception
                info.first_chance=1
                info.record.code=0x80000003 if exceptions[0]==1 else 0x80000004
                info.record.address=(self.BASE+o.bootstrap.BREAK_RVA if exceptions[0]==1
                                     else self.MODULE+Probe.BREAK_RVAS[site])
                info.record.parameters=1 if exceptions[0]==1 else 0
                if exceptions[0]==2:regs[4],regs[5]=0xFFFF0FF0|(1<<site),0x455
            else:raw.info.exit_code=1 if hit else 0xC0000142
            return True
        def name(handle,buffer,size,flags):
            buffer.value={101:"\\DUMMY\\python.exe",102:"\\DUMMY\\ntdll.dll",103:"\\DUMMY\\bcrypt.dll"}[handle]
            return len(buffer.value)
        bootstrap_get=k.GetThreadContext.side_effect
        def get(handle,pointer):
            if pointer.value==o.bootstrap.context_pointer.value:return bootstrap_get(handle,pointer)
            struct.pack_into("<6Q",p.context,72,*regs)
            if struct.unpack_from("<I",p.context,48)[0]==p.HIT_FLAGS:
                for offset,number in ((248,self.MODULE+Probe.BREAK_RVAS[site]),(120,value),(144,value),
                                      (152,self.RSP),(176,self.MODULE)):
                    struct.pack_into("<Q",p.context,offset,number)
            return True
        def set_context(handle,pointer):
            self.assertEqual(handle,502)
            self.assertEqual(o.bootstrap.state,"verified")
            self.assertEqual(struct.unpack_from("<I",p.context,48)[0],p.DEBUG_FLAGS)
            regs[:]=struct.unpack_from("<6Q",p.context,72)
            regs[4]=0
            return True
        k.WaitForDebugEventEx.side_effect=deliver
        k.GetFinalPathNameByHandleW.side_effect=name
        k.GetThreadContext.side_effect=get
        k.SetThreadContext.side_effect=set_context
        k.WaitForSingleObject.side_effect=lambda handle,timeout:0 if last[0]==5 else 258
        return o,k,fixture,memory,regs

    def test_each_site_and_last_error_zero_preserve_value_and_stop(self):
        for site,value in ((0,5),(1,0xC0000022),(2,7),(3,5),(3,0)):
            with ExitStack() as scope,self.subTest(site=site,value=value):
                o,k,fixture,memory,regs=self.fixture(scope,site=site,value=value)
                o.run()
                self.assertEqual(o.primary.reason,"bcrypt_failure_observed_stop")
                self.assertEqual(o.context.state,"completed")
                row=o.context.row
                self.assertEqual((row["status_u32"],row["hit_index"]),(value,site))
                self.assertEqual(row["status_domain"],"unclassified_nonzero" if site<3 else "win32_candidate")
                self.assertEqual(row["load_slot"],2)
                self.assertEqual((row["get_attempts"],row["read_attempts"],row["confirmed_bytes"]),
                                 (3,3,730) if site<3 else (3,2,722))
                self.assertEqual(k.GetThreadContext.call_count,4)
                k.SetThreadContext.assert_called_once()
                self.assertEqual(k.ReadProcessMemory.call_count,6 if site<3 else 5)
                self.assertEqual(sum(c.args[3] for c in k.ReadProcessMemory.call_args_list),805 if site<3 else 797)
                self.assertEqual([c.args[2] for c in k.ContinueDebugEvent.call_args_list],
                                 [DBG_CONTINUE]*4+[DBG_NOT_HANDLED,DBG_CONTINUE])
                self.assertEqual(o.result["teardown_status"],"pass")
                self.assertEqual(o.stop.handles,[None,None])
                fixture.cleanup.assert_not_called()
                saved=interpret(o.evidence.buffer.raw[:o.evidence.size])
                self.assertEqual(saved.private_metadata["context"]["row"]["status_u32"],value)
                self.assertFalse(o.result["native_accepted"])

    def test_arm_failure_never_handles_bootstrap(self):
        for fault in ("code","set_false","set_memory","readback","pending","load"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,k,fixture,memory,regs=self.fixture(scope,hit=False)
                if fault=="code":memory[self.MODULE+Probe.WINDOWS[0][0]]=b"Y"*475
                elif fault in ("set_false","set_memory"):
                    k.SetThreadContext.side_effect=MemoryError() if fault=="set_memory" else None
                    k.SetThreadContext.return_value=False
                elif fault=="readback":
                    original=k.SetThreadContext.side_effect
                    def mutate(*args):
                        ok=original(*args);regs[2]+=1;return ok
                    k.SetThreadContext.side_effect=mutate
                else:
                    original=k.ReadProcessMemory.side_effect
                    def mutate(*args):
                        ok=original(*args)
                        if k.ReadProcessMemory.call_count==4:
                            if fault=="pending":o.transport.buffers[o.transport.pending].info.exception.record.information[14]=1
                            else:o.images.rows[2]["status"]="unconfirmed"
                        return ok
                    k.ReadProcessMemory.side_effect=mutate
                o.run()
                self.assertNotEqual(o.context.state,"completed")
                self.assertEqual(o.bootstrap.row["continue_state"],"not_started")
                self.assertEqual(o.result["teardown_status"],"pass")
                self.assertEqual(k.ContinueDebugEvent.call_args_list[3].args[2],DBG_NOT_HANDLED)
                if fault in ("code","pending","load"):k.SetThreadContext.assert_not_called()
                if fault=="set_memory":
                    self.assertTrue(o.resource_stop)
                    k.WriteFile.assert_not_called()

    def test_hit_context_mismatch_prevents_caller_read(self):
        faults={"rip":(248,"Q",0),"tf":(68,"I",0x100),"status":(120,"I",0),"ebx":(144,"I",1),
                "rsp":(152,"Q",self.RSP+1),"dr2":(88,"Q",0),"dr6":(104,"Q",3),"dr7":(112,"Q",0x5D)}
        for fault,(offset,kind,value) in faults.items():
            with ExitStack() as scope,self.subTest(fault=fault):
                o,k,fixture,memory,regs=self.fixture(scope)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        struct.pack_into("<"+kind,o.context.context,offset,value)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertNotEqual(o.context.state,"completed")
                self.assertEqual(k.ReadProcessMemory.call_count,5)
                self.assertIn("context_hex",o.context.row)
                self.assertEqual(o.result["teardown_status"],"pass")

    def test_caller_partial_or_changed_hit_retains_bytes_and_stops(self):
        for fault in ("false","short","oversize","memory","caller","pending","lifetime"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,k,fixture,memory,regs=self.fixture(scope)
                original=k.ReadProcessMemory.side_effect
                def read(*args):
                    if k.ReadProcessMemory.call_count==6 and fault=="memory":raise MemoryError()
                    ok=original(*args)
                    if k.ReadProcessMemory.call_count==6:
                        if fault=="false":return False
                        if fault=="short":args[4].contents.value=7
                        if fault=="oversize":args[4].contents.value=9
                        if fault=="caller":C.memset(args[2],0,8)
                        if fault=="pending":o.transport.buffers[o.transport.pending].info.exception.record.address+=1
                        if fault=="lifetime":o.images.rows[2]["status"]="unconfirmed"
                    return ok
                k.ReadProcessMemory.side_effect=read
                o.run()
                self.assertNotEqual(o.context.state,"completed")
                self.assertEqual(k.ReadProcessMemory.call_count,6)
                self.assertNotIn("caller_rva",o.context.row)
                if fault=="memory":
                    self.assertTrue(o.resource_stop)
                    k.WriteFile.assert_not_called()
                else:self.assertIn("caller_hex",o.context.row)
                self.assertEqual(o.result["teardown_status"],"pass")

    def test_module_handle_site_frame_mismatch_preserves_status(self):
        for offset,value in ((176,self.MODULE+1),(168,1)):
            with ExitStack() as scope,self.subTest(offset=offset):
                o,k,fixture,memory,regs=self.fixture(scope,site=3)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        struct.pack_into("<Q",o.context.context,offset,value)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertEqual(o.primary.reason,"bcrypt_entry_frame")
                self.assertEqual(o.context.row["status_u32"],5)
                self.assertEqual(k.ReadProcessMemory.call_count,5)

    def test_unrelated_first_exception_is_consumed_without_reselection(self):
        with ExitStack() as scope:
            o,k,fixture,memory,regs=self.fixture(scope)
            deliver=k.WaitForDebugEventEx.side_effect
            def wrong(pointer,timeout):
                ok=deliver(pointer,timeout)
                if pointer.contents.kind==1 and o.context.state=="armed":
                    pointer.contents.info.exception.record.code=0xC0000005
                return ok
            k.WaitForDebugEventEx.side_effect=wrong
            o.run()
            self.assertEqual(o.primary.reason,"bcrypt_exception")
            self.assertEqual(o.context.state,"stopped")
            self.assertEqual(k.GetThreadContext.call_count,3)
            with self.assertRaises(TransportError):o.context.capture(lambda:None)
            self.assertEqual(k.GetThreadContext.call_count,3)

    def test_no_hit_is_not_observed_and_options_are_exclusive(self):
        with ExitStack() as scope:
            o,k,fixture,memory,regs=self.fixture(scope,hit=False)
            o.run()
            self.assertEqual(o.primary.reason,"init_failure_not_observed")
            self.assertNotIn("status_u32",o.context.row)
            self.assertEqual(o.observer.result["exit_code_observed"],0xC0000142)
        self.assertNotIsInstance(DebugDriver().context,Probe)
        invalid=[{"bcrypt_failure":x} for x in (True,1,None)]
        invalid += [{"bcrypt_failure":True,"bootstrap":True},{"bcrypt_failure":True,"detached_console":True}]
        invalid += [dict(bcrypt_failure=True,bootstrap=True,detached_console=True,**{k:True})
                    for k in ("unload_entry","init_return","console_failure","init_failure")]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs),self.assertRaises(TransportError):DebugDriver(**kwargs)


if __name__=="__main__":
    unittest.main()
