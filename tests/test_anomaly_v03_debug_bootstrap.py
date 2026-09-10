"""Fake Win32 only: bootstrap proof, one consumption, and subsequent observation."""
import ctypes as C
import hashlib
import json
import struct
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from tests import test_anomaly_v03_debug_driver as wiring
from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
from tests.fixtures.anomaly_v03_debug_bootstrap import DebugBootstrap as Probe
from tests.fixtures.anomaly_v03_debug_transport import BREAKPOINT, DBG_CONTINUE, DBG_NOT_HANDLED, TransportError
from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret


class BootstrapTests(unittest.TestCase):
    BASE, RSP = 0x40000000, 0x10000
    CODE = bytes.fromhex("4883ec38c64424400048836424200041b9010000004c8d442440418d511048c7c1feffffffe822f0030085c0780a807c2440007503cceb004883c438c3cc")

    def fixture(self, scope, *, caller=0x8DBE1, second_break=False, init_failure=False, bcrypt_failure=False):
        o, api, k, preflight, tokens, fixture, disk = wiring.DebugDriverTests().driver(
            scope, unload_entry=not (init_failure or bcrypt_failure), detached_console=True, bootstrap=True,
            init_failure=init_failure, bcrypt_failure=bcrypt_failure)
        b = o.bootstrap
        events = iter((3, 6, 1, 1, 5) if second_break else (3, 6, 1, 5))
        last = [None]
        def deliver(pointer, timeout):
            raw = pointer.contents
            raw.kind, raw.pid, raw.tid = next(events), 17, 19
            last[0] = raw.kind
            if raw.kind == 3:
                raw.info.create_process.file = 101
            elif raw.kind == 6:
                raw.info.load_dll.file, raw.info.load_dll.base = 102, self.BASE
            elif raw.kind == 1:
                raw.info.exception.record.code = BREAKPOINT
                raw.info.exception.record.address = self.BASE+b.BREAK_RVA
                raw.info.exception.record.parameters = 1
                raw.info.exception.first_chance = 1
            elif raw.kind == 5:
                raw.info.exit_code = 0xC0000142
            return True
        def name(handle, buffer, size, flags):
            buffer.value = "\\DUMMY\\ntdll.dll" if handle == 102 else "\\DUMMY\\python.exe"
            return len(buffer.value)
        def get(handle, pointer):
            self.assertEqual(handle, 502)
            self.assertFalse(o.stop.started)
            struct.pack_into("<Q", b.context, 152, self.RSP)
            struct.pack_into("<Q", b.context, 248, self.BASE+b.BREAK_RVA+1)
            return True
        memory = {self.BASE+b.CODE_RVA: self.CODE,
                  self.RSP+0x38: struct.pack("<Q", self.BASE+caller),
                  self.BASE+caller-5: b"\xe8"+struct.pack("<i", b.CODE_RVA-caller)}
        def read(handle, address, output, size, length):
            self.assertEqual(handle, 501)
            self.assertFalse(o.stop.started)
            data = bytes(memory[address.value])
            self.assertEqual(len(data), size)
            C.memmove(output, data, size)
            length.contents.value = size
            return True
        k.WaitForDebugEventEx.side_effect = deliver
        k.GetFinalPathNameByHandleW.side_effect = name
        k.GetThreadId.return_value = 19
        k.GetProcessIdOfThread.return_value = 17
        k.GetThreadContext.side_effect = get
        k.ReadProcessMemory.side_effect = read
        k.WaitForSingleObject.side_effect = lambda handle, timeout: 0 if last[0] == 5 else 258
        return o, api, k, fixture, memory

    def assert_stopped(self, o, k):
        self.assertEqual(o.result["status"], "failed")
        self.assertEqual(o.result["teardown_status"], "pass")
        self.assertEqual(o.stop.handles, [None, None])
        k.SetThreadContext.assert_not_called()
        # Any release of the rejected pending exception belongs to owned stop.
        statuses = [call.args[2] for call in k.ContinueDebugEvent.call_args_list]
        self.assertEqual(statuses[:2], [DBG_CONTINUE, DBG_CONTINUE])
        if len(statuses) > 2:
            self.assertEqual(statuses[2], DBG_NOT_HANDLED)
        k.TerminateProcess.assert_called_once()

    def test_verified_callers_are_consumed_once_before_natural_exit(self):
        for caller in Probe.CALLERS:
            with ExitStack() as scope, self.subTest(caller=caller):
                o, api, k, fixture, memory = self.fixture(scope, caller=caller)
                result = o.run()
                self.assertEqual(result["status"], "observed")
                self.assertEqual(o.observer.result["exit_code_observed"], 0xC0000142)
                self.assertEqual(o.bootstrap.state, "continued")
                row = o.bootstrap.row
                self.assertEqual(row["continue_state"], "confirmed")
                self.assertEqual((row["get_attempts"], row["read_attempts"], row["confirmed_bytes"]), (1, 3, 75))
                self.assertEqual(row["caller_rva"], caller)
                self.assertEqual([c.args[3] for c in k.ReadProcessMemory.call_args_list], [62, 8, 5])
                self.assertEqual(k.ContinueDebugEvent.call_args_list[2].args, (17, 19, DBG_CONTINUE))
                k.GetThreadContext.assert_called_once()
                k.SetThreadContext.assert_not_called()
                k.TerminateProcess.assert_not_called()
                fixture.cleanup.assert_not_called()
                self.assertIsNone(o.stop.drain.bootstrap)
                saved = interpret(o.evidence.buffer.raw[:o.evidence.size])
                self.assertEqual(saved.private_metadata["bootstrap"]["row"], row)
                self.assertEqual(saved.private_metadata["launch"]["requested_creation_flags"], 0x40E)
                self.assertEqual(o.context.row["status"], "not_observed")
                self.assertFalse(result["native_accepted"])
                self.assertFalse(result["formal_permission"])
                self.assertLess(len(json.dumps({"state":o.bootstrap.state,"row":row})), Probe.JSON_LIMIT)
                self.assertNotIn(row["context_hex"], repr(o.bootstrap))

    def test_exception_shape_and_parameter_mismatch_never_queries(self):
        for fault in ("tid", "code", "chance", "flags", "record", "parameters", "parameter", "address"):
            with ExitStack() as scope, self.subTest(fault=fault):
                o, api, k, fixture, memory = self.fixture(scope)
                deliver = k.WaitForDebugEventEx.side_effect
                def changed(pointer, timeout):
                    ok = deliver(pointer, timeout)
                    raw = pointer.contents
                    if raw.kind == 1:
                        info = raw.info.exception
                        if fault == "tid": raw.tid = 23
                        elif fault == "code": info.record.code = 0x80000004
                        elif fault == "chance": info.first_chance = 0
                        elif fault == "flags": info.record.flags = 1
                        elif fault == "record": info.record.record = 0x20000
                        elif fault == "parameters": info.record.parameters = 0
                        elif fault == "parameter": info.record.information[0] = 1
                        else: info.record.address += 1
                    return ok
                k.WaitForDebugEventEx.side_effect = changed
                o.run()
                self.assert_stopped(o, k)
                k.GetThreadContext.assert_not_called()
                k.ReadProcessMemory.assert_not_called()
                self.assertEqual(o.bootstrap.slot, 2)

    def test_context_faults_keep_captured_bytes_and_never_read_caller(self):
        for fault in ("false", "flags", "rip", "tf", "rsp"):
            with ExitStack() as scope, self.subTest(fault=fault):
                o, api, k, fixture, memory = self.fixture(scope)
                original = k.GetThreadContext.side_effect
                def get(*args):
                    original(*args)
                    if fault == "false": return False
                    offset, code, value = {"flags": (48,"I",0), "rip": (248,"Q",self.BASE+Probe.BREAK_RVA),
                        "tf": (68,"I",0x100), "rsp": (152,"Q",self.RSP+1)}[fault]
                    struct.pack_into("<"+code, o.bootstrap.context, offset, value)
                    return True
                k.GetThreadContext.side_effect = get
                o.run()
                self.assert_stopped(o, k)
                self.assertEqual(k.ReadProcessMemory.call_count, 1)
                self.assertEqual("context_hex" in o.bootstrap.row, fault != "false")

    def test_each_read_fault_stops_without_later_reads_or_permission(self):
        for index in (1,2,3):
            for fault in ("false", "short", "oversize", "mismatch", "memory"):
                with ExitStack() as scope, self.subTest(index=index,fault=fault):
                    o, api, k, fixture, memory = self.fixture(scope)
                    original = k.ReadProcessMemory.side_effect
                    def read(handle,address,output,size,length):
                        if k.ReadProcessMemory.call_count == index and fault == "memory":
                            raise MemoryError()
                        ok = original(handle,address,output,size,length)
                        if k.ReadProcessMemory.call_count == index:
                            if fault == "false": return False
                            if fault == "short": length.contents.value = size-1
                            if fault == "oversize": length.contents.value = size+1
                            if fault == "mismatch": C.memset(output, 0, size)
                        return ok
                    k.ReadProcessMemory.side_effect = read
                    o.run()
                    self.assert_stopped(o,k)
                    self.assertEqual(k.ReadProcessMemory.call_count,index)
                    if fault == "memory":
                        self.assertTrue(o.resource_stop)
                        self.assertEqual(o.evidence.capture_state,"resource_skipped")
                        k.WriteFile.assert_not_called()

    def test_pending_record_or_module_lifetime_change_prevents_consumption(self):
        for fault in ("tid", "address", "parameter_tail", "slot", "load_base", "load_state"):
            with ExitStack() as scope, self.subTest(fault=fault):
                o, api, k, fixture, memory = self.fixture(scope)
                consume = o.bootstrap.consume
                def changed(transport):
                    raw = transport.buffers[transport.pending]
                    if fault == "tid": raw.tid += 1
                    elif fault == "address": raw.info.exception.record.address += 1
                    elif fault == "parameter_tail": raw.info.exception.record.information[14] = 1
                    elif fault == "slot": transport.pending = 1
                    elif fault == "load_base": transport.buffers[1].info.load_dll.base += 0x10000
                    else: o.images.rows[1]["status"] = "not_confirmed"
                    consume(transport)
                scope.enter_context(patch.object(o.bootstrap,"consume",side_effect=changed))
                o.run()
                self.assertEqual(o.result["status"],"failed")
                self.assertEqual(o.bootstrap.row["continue_state"],"not_started")
                self.assertEqual(k.GetThreadContext.call_count,1)
                self.assertEqual(k.ReadProcessMemory.call_count,3)
                # No normal handled Continue was sent for the breakpoint.
                self.assertEqual([c.args for c in k.ContinueDebugEvent.call_args_list[:2]],
                                 [(17,19,DBG_CONTINUE)]*2)

    def test_continue_failure_and_post_success_interruption_never_retry(self):
        for fault in ("false","memory","post_success"):
            with ExitStack() as scope, self.subTest(fault=fault):
                o, api, k, fixture, memory = self.fixture(scope)
                if fault == "post_success":
                    scope.enter_context(patch.object(o.bootstrap,"continued",side_effect=RuntimeError("private")))
                else:
                    def cont(pid,tid,status):
                        if k.ContinueDebugEvent.call_count==3:
                            if fault=="memory": raise MemoryError()
                            return False
                        return True
                    k.ContinueDebugEvent.side_effect=cont
                o.run()
                self.assertEqual(o.result["status"],"failed")
                self.assertEqual(o.bootstrap.state,"consumed")
                self.assertEqual(o.bootstrap.row["continue_state"],"uncertain")
                self.assertEqual(k.GetThreadContext.call_count,1)
                self.assertEqual(k.ReadProcessMemory.call_count,3)
                if fault=="memory":
                    self.assertTrue(o.resource_stop)
                    k.WriteFile.assert_not_called()

    def test_second_breakpoint_is_rejected_without_requery(self):
        with ExitStack() as scope:
            o,api,k,fixture,memory=self.fixture(scope,second_break=True)
            o.run()
            self.assertEqual(o.primary.reason,"bootstrap_retry")
            self.assertEqual(o.bootstrap.row["continue_state"],"confirmed")
            self.assertEqual(k.GetThreadContext.call_count,1)
            self.assertEqual(k.ReadProcessMemory.call_count,3)
            self.assertEqual(k.ContinueDebugEvent.call_args_list[2].args[2],DBG_CONTINUE)
            self.assertEqual(k.ContinueDebugEvent.call_args_list[3].args[2],DBG_NOT_HANDLED)
            self.assertEqual(o.result["teardown_status"],"pass")

    def test_options_and_forged_permission_are_rejected(self):
        self.assertIsNone(DebugDriver().bootstrap)
        for options in ({"bootstrap":True}, {"bootstrap":1},
                        {"bootstrap":True,"init_return":True,"detached_console":True},
                        {"bootstrap":True,"unload_entry":True},
                        {"bootstrap":None,"unload_entry":True,"detached_console":True}):
            with self.subTest(options=options),self.assertRaises(TransportError):
                DebugDriver(**options)
        with ExitStack() as scope:
            o,api,k,fixture,memory=self.fixture(scope)
            def replace_permission(transport):
                transport.bootstrap=Mock()
            scope.enter_context(patch.object(o.bootstrap,"consume",side_effect=replace_permission))
            # A foreign object present before transport's type check is rejected.
            capture=o.bootstrap.capture
            def swapped(budget):
                capture(budget)
                if o.bootstrap.state=="verified": o.transport.bootstrap=Mock()
            scope.enter_context(patch.object(o.bootstrap,"capture",side_effect=swapped))
            o.run()
            self.assertEqual(o.primary.reason,"bootstrap_unverified")
            self.assert_stopped(o,k)


    def test_budget_resource_stop_at_each_read_boundary_keeps_owned_teardown(self):
        for boundary in (7,8,9,10,11,12,13,14,15):
            with ExitStack() as scope,self.subTest(boundary=boundary):
                o,api,k,fixture,memory=self.fixture(scope)
                original=o.bootstrap._budget
                count=[0]
                def budget(callback):
                    count[0]+=1
                    if count[0]==boundary: raise MemoryError()
                    original(callback)
                scope.enter_context(patch.object(o.bootstrap,"_budget",side_effect=budget))
                o.run()
                self.assertTrue(o.resource_stop)
                self.assert_stopped(o,k)
                self.assertEqual(count[0],boundary)
                k.WriteFile.assert_not_called()

    def test_verified_bootstrap_then_unload_entry_uses_both_fixed_budgets(self):
        from tests.test_anomaly_v03_debug_unload_entry import DebugUnloadEntryTests
        from tests.fixtures.anomaly_v03_debug_unload_entry import DebugUnloadEntry
        with ExitStack() as scope:
            o,api,k,fixture,memory=self.fixture(scope)
            unused,unusedk,unusedstop,unusedbudget,unload_memory,windows=DebugUnloadEntryTests().fixture()
            memory.update(unload_memory)
            scope.enter_context(patch.object(DebugUnloadEntry,"WINDOWS",windows))
            events=iter((3,6,6,1,7,5)); last=[None]
            def deliver(pointer,timeout):
                raw=pointer.contents
                raw.kind,raw.pid,raw.tid=next(events),17,19
                last[0]=raw.kind
                if raw.kind==3: raw.info.create_process.file=101
                elif raw.kind==6:
                    is_ntdll=o.images.count==1
                    raw.info.load_dll.file=102 if is_ntdll else 103
                    raw.info.load_dll.base=self.BASE if is_ntdll else 0x50000000
                elif raw.kind==1:
                    raw.info.exception.record.code=BREAKPOINT
                    raw.info.exception.record.address=self.BASE+Probe.BREAK_RVA
                    raw.info.exception.record.parameters=1
                    raw.info.exception.first_chance=1
                elif raw.kind==7: raw.info.unload_base=0x50000000
                else: raw.info.exit_code=0xC0000142
                return True
            def name(handle,buffer,size,flags):
                buffer.value={101:"\\DUMMY\\python.exe",102:"\\DUMMY\\ntdll.dll",103:"\\DUMMY\\target.dll"}[handle]
                return len(buffer.value)
            initial_get=k.GetThreadContext.side_effect
            def get(handle,pointer):
                if k.GetThreadContext.call_count==1: return initial_get(handle,pointer)
                for offset,value in ((136,0x50000000),(144,0x20000),(152,0x10000),
                                      (248,self.BASE+DebugUnloadEntry.RIP_RVA)):
                    struct.pack_into("<Q",o.context.context,offset,value)
                return True
            k.WaitForDebugEventEx.side_effect=deliver
            k.GetFinalPathNameByHandleW.side_effect=name
            k.GetThreadContext.side_effect=get
            k.WaitForSingleObject.side_effect=lambda handle,timeout: 0 if last[0]==5 else 258
            o.run()
            self.assertEqual(o.result["status"],"observed", repr(o.primary))
            self.assertEqual(o.bootstrap.state,"continued")
            self.assertEqual(o.context.entry.row["status"],"confirmed")
            self.assertTrue(o.context.entry.row["init_failure_bit"])
            self.assertEqual(k.GetThreadContext.call_count,2)
            self.assertEqual(k.ReadProcessMemory.call_count,8)
            self.assertEqual(sum(c.args[3] for c in k.ReadProcessMemory.call_args_list),3182)
            self.assertEqual(o.observer.result["continued_events"],6)
            self.assertEqual(o.observer.result["exit_code_observed"],0xC0000142)
            k.SetThreadContext.assert_not_called()
            k.TerminateProcess.assert_not_called()
            fixture.cleanup.assert_not_called()
            saved=interpret(o.evidence.buffer.raw[:o.evidence.size])
            self.assertEqual(saved.private_metadata["bootstrap"]["row"]["continue_state"],"confirmed")
            self.assertEqual(saved.private_metadata["context"]["row"]["module_entry"]["status"],"confirmed")


if __name__=="__main__":
    unittest.main()
