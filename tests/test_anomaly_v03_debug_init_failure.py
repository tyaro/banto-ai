"""Fake-only integration of verified bootstrap and one loader failure trap."""
import ctypes as C
import hashlib
import struct
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from tests import test_anomaly_v03_debug_bootstrap as bootstrap_fixtures
from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
from tests.fixtures.anomaly_v03_debug_init_failure import DebugInitFailure as Probe
from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret
from tests.fixtures.anomaly_v03_debug_transport import DBG_CONTINUE, DBG_NOT_HANDLED, TransportError


class InitFailureTests(unittest.TestCase):
    BASE, MODULE, ENTRY = 0x40000000, 0x50000000, 0x30000

    def fixture(self, scope, *, hit=True):
        o,api,k,fixture,memory=bootstrap_fixtures.BootstrapTests().fixture(scope,init_failure=True)
        p=o.context; regs=[0]*6
        code=b"X"*845
        scope.enter_context(patch.object(Probe,"WINDOWS",((0xE5D0,845,hashlib.sha256(code).hexdigest()),)))
        memory[self.BASE+0xE5D0]=code
        entry=bytearray(112)
        struct.pack_into("<QQI",entry,0x30,self.MODULE,self.MODULE+0x2000,0x100000)
        struct.pack_into("<I",entry,0x68,0x80000)
        memory[self.ENTRY]=entry
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
                info.record.address=self.BASE+(o.bootstrap.BREAK_RVA if exceptions[0]==1 else Probe.BREAK_RVA)
                info.record.parameters=1 if exceptions[0]==1 else 0
                if exceptions[0]==2: regs[4],regs[5]=0xFFFF0FF1,0x401
            else:raw.info.exit_code=1 if hit else 0xC0000142
            return True
        def name(handle,buffer,size,flags):
            buffer.value={101:"\\DUMMY\\python.exe",102:"\\DUMMY\\ntdll.dll",103:"\\DUMMY\\target.dll"}[handle]
            return len(buffer.value)
        bootstrap_get=k.GetThreadContext.side_effect
        def get(handle,pointer):
            if pointer.value==o.bootstrap.context_pointer.value:return bootstrap_get(handle,pointer)
            struct.pack_into("<6Q",p.context,72,*regs)
            if struct.unpack_from("<I",p.context,48)[0]==p.HIT_FLAGS:
                for offset,value in ((248,self.BASE+Probe.BREAK_RVA),(176,self.ENTRY),(216,0),
                                     (232,0xC0000142),(240,self.MODULE+0x2000)):
                    struct.pack_into("<Q",p.context,offset,value)
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
        return o,api,k,fixture,memory,regs

    def test_failure_branch_retains_module_before_flag_write_and_never_continues_hit(self):
        for flags,callback in ((0x80000,0x50002000),(0x180000,0x50002000),(0x80000,0)):
            with ExitStack() as scope,self.subTest(flags=flags,callback=callback):
                o,api,k,fixture,memory,regs=self.fixture(scope)
                struct.pack_into("<I",memory[self.ENTRY],0x68,flags)
                struct.pack_into("<Q",memory[self.ENTRY],0x38,callback)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        struct.pack_into("<Q",o.context.context,240,callback)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertEqual(o.primary.reason,"init_failure_observed_stop")
                self.assertEqual(o.context.state,"completed")
                row=o.context.row
                self.assertEqual((row["get_attempts"],row["read_attempts"],row["confirmed_bytes"]),(3,2,957))
                self.assertEqual(row["flags"],flags)
                self.assertEqual(row["module_load_slot"],2)
                self.assertEqual(row["callback_rva"],0x2000 if callback else None)
                self.assertEqual(row["r14_status"],0xC0000142)
                self.assertEqual(row["r12_low_byte"],0)
                self.assertEqual(k.GetThreadContext.call_count,4)
                k.SetThreadContext.assert_called_once()
                self.assertEqual(k.ReadProcessMemory.call_count,5)
                self.assertEqual(sum(c.args[3] for c in k.ReadProcessMemory.call_args_list),1032)
                statuses=[c.args[2] for c in k.ContinueDebugEvent.call_args_list]
                self.assertEqual(statuses,[DBG_CONTINUE]*4+[DBG_NOT_HANDLED,DBG_CONTINUE])
                self.assertEqual(o.bootstrap.row["continue_state"],"confirmed")
                self.assertEqual(o.result["teardown_status"],"pass")
                self.assertEqual(o.stop.handles,[None,None])
                fixture.cleanup.assert_not_called()
                saved=interpret(o.evidence.buffer.raw[:o.evidence.size])
                self.assertEqual(saved.private_metadata["context"]["row"]["entry_read_hex"],bytes(memory[self.ENTRY]).hex())
                self.assertFalse(o.result["native_accepted"])

    def test_arm_failures_never_handle_bootstrap(self):
        for fault in ("code","set_false","set_memory","readback","pending"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,api,k,fixture,memory,regs=self.fixture(scope,hit=False)
                if fault=="code":memory[self.BASE+0xE5D0]=b"Y"*845
                elif fault in ("set_false","set_memory"):
                    k.SetThreadContext.side_effect=MemoryError() if fault=="set_memory" else None
                    k.SetThreadContext.return_value=False
                elif fault=="readback":
                    original=k.SetThreadContext.side_effect
                    def set_bad(*args):
                        ok=original(*args);regs[0]+=1;return ok
                    k.SetThreadContext.side_effect=set_bad
                else:
                    original=k.ReadProcessMemory.side_effect
                    def mutate(*args):
                        ok=original(*args)
                        if k.ReadProcessMemory.call_count==4:
                            o.transport.buffers[o.transport.pending].info.exception.record.information[0]=1
                        return ok
                    k.ReadProcessMemory.side_effect=mutate
                o.run()
                self.assertEqual(o.result["status"],"failed")
                self.assertEqual(o.result["teardown_status"],"pass")
                self.assertEqual(o.bootstrap.row["continue_state"],"not_started")
                self.assertEqual(k.ContinueDebugEvent.call_args_list[3].args[2],DBG_NOT_HANDLED)
                if fault in ("code","pending"):k.SetThreadContext.assert_not_called()
                if fault=="set_memory":
                    self.assertTrue(o.resource_stop)
                    k.WriteFile.assert_not_called()

    def test_hit_context_mismatch_does_not_read_entry(self):
        for fault in ("rip","status","return_byte","tf","dr0","dr6","dr7"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,api,k,fixture,memory,regs=self.fixture(scope)
                original=k.GetThreadContext.side_effect
                def get(*args):
                    ok=original(*args)
                    if args[1].value==o.context.context_pointer.value and o.context.row["get_attempts"]==3:
                        offset,kind,value={"rip":(248,"Q",self.BASE+Probe.BREAK_RVA+1),
                            "status":(232,"I",0),"return_byte":(216,"Q",1),"tf":(68,"I",0x100),
                            "dr0":(72,"Q",0),"dr6":(104,"Q",0xFFFF0FF3),"dr7":(112,"Q",0x405)}[fault]
                        struct.pack_into("<"+kind,o.context.context,offset,value)
                    return ok
                k.GetThreadContext.side_effect=get
                o.run()
                self.assertEqual(o.result["status"],"failed")
                self.assertEqual(k.ReadProcessMemory.call_count,4)
                self.assertIn("context_hex",o.context.row)
                self.assertNotIn("module_load_slot",o.context.row)
                k.SetThreadContext.assert_called_once()
                self.assertEqual(o.result["teardown_status"],"pass")

    def test_entry_partial_resource_and_field_failures_never_interpret_unconfirmed_module(self):
        for fault in ("false","short","oversize","memory","size","base","callback","lifetime"):
            with ExitStack() as scope,self.subTest(fault=fault):
                o,api,k,fixture,memory,regs=self.fixture(scope)
                if fault=="size":struct.pack_into("<I",memory[self.ENTRY],0x40,0)
                elif fault=="base":struct.pack_into("<Q",memory[self.ENTRY],0x30,self.MODULE+1)
                elif fault=="callback":struct.pack_into("<Q",memory[self.ENTRY],0x38,self.MODULE+0x3000)
                else:
                    original=k.ReadProcessMemory.side_effect
                    def read(*args):
                        if k.ReadProcessMemory.call_count==5 and fault=="memory":raise MemoryError()
                        ok=original(*args)
                        if k.ReadProcessMemory.call_count==5:
                            if fault=="false":return False
                            if fault=="short":args[4].contents.value=111
                            if fault=="oversize":args[4].contents.value=113
                            if fault=="lifetime":o.images.rows[2]["status"]="unconfirmed"
                        return ok
                    k.ReadProcessMemory.side_effect=read
                o.run()
                self.assertEqual(o.result["status"],"failed")
                self.assertNotIn("module_load_slot",o.context.row)
                self.assertEqual(k.ReadProcessMemory.call_count,5)
                self.assertEqual(o.result["teardown_status"],"pass")
                if fault!="memory":self.assertIn("entry_read_hex",o.context.row)
                else:
                    self.assertTrue(o.resource_stop)
                    k.WriteFile.assert_not_called()

    def test_unrelated_first_exception_stops_without_reselection(self):
        with ExitStack() as scope:
            o,api,k,fixture,memory,regs=self.fixture(scope)
            original=k.WaitForDebugEventEx.side_effect
            def deliver(pointer,timeout):
                ok=original(pointer,timeout)
                raw=pointer.contents
                if raw.kind==1 and raw.info.exception.record.code==0x80000004:
                    raw.info.exception.record.address+=1
                return ok
            k.WaitForDebugEventEx.side_effect=deliver
            o.run()
            self.assertEqual(o.primary.reason,"init_failure_exception")
            self.assertEqual(o.context.row["event_slot"],4)
            self.assertEqual(o.context.row["get_attempts"],2)
            k.SetThreadContext.assert_called_once()
            self.assertEqual(o.result["teardown_status"],"pass")

    def test_natural_exit_without_hit_is_not_converted_to_observation(self):
        with ExitStack() as scope:
            o,api,k,fixture,memory,regs=self.fixture(scope,hit=False)
            o.run()
            self.assertEqual(o.primary.reason,"init_failure_not_observed")
            self.assertEqual(o.observer.result["exit_code_observed"],0xC0000142)
            self.assertNotIn("module_load_slot",o.context.row)
            self.assertEqual(k.GetThreadContext.call_count,3)
            k.SetThreadContext.assert_called_once()

    def test_options_require_exclusive_bootstrap_and_detached(self):
        self.assertNotIsInstance(DebugDriver().context,Probe)
        for kwargs in ({"init_failure":True},{"init_failure":1},{"init_failure":None},
                       {"init_failure":True,"detached_console":True},
                       {"init_failure":True,"bootstrap":True},
                       {"init_failure":True,"bootstrap":True,"detached_console":True,"unload_entry":True},
                       {"init_failure":True,"bootstrap":True,"detached_console":True,"init_return":True},
                       {"init_failure":True,"bootstrap":True,"detached_console":True,"console_failure":True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(TransportError):DebugDriver(**kwargs)


if __name__=="__main__":
    unittest.main()
