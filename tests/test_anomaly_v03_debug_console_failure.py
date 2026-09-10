"""Fake-only console failure sites, context boundaries and owned termination."""

import ctypes as C
import hashlib
import json
import struct
import unittest
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest.mock import patch

from tests import test_anomaly_v03_debug_context as cf
from tests import test_anomaly_v03_debug_driver as df
from tests.fixtures.anomaly_v03_debug_console_failure import DebugConsoleFailure as Probe
from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
from tests.fixtures.anomaly_v03_debug_transport import TransportError, DBG_NOT_HANDLED


class DebugConsoleFailureTests(unittest.TestCase):
    BASE, RSP = 0x50000000, 0x10000
    WINDOWS = tuple((r, n, hashlib.sha256(bytes([i + 1]) * n).hexdigest())
                    for i, (r, n, digest) in enumerate(Probe.WINDOWS))

    def configure(self, o, k, regs, hit):
        def get(handle, pointer):
            self.assertEqual(pointer.value % 16, 0)
            flags = struct.unpack_from("<I", o.context, 48)[0]
            self.assertIn(flags, (o.DEBUG_FLAGS, o.HIT_FLAGS))
            struct.pack_into("<6Q", o.context, 72, *regs)
            if flags == o.HIT_FLAGS:
                struct.pack_into("<Q", o.context, 120, 0xC0000022)
                struct.pack_into("<2Q", o.context, 152, self.RSP, self.RSP + 0x70)
                struct.pack_into("<Q", o.context, 248, self.BASE + o.BREAK_RVAS[hit[0]])
            return True
        def put(handle, pointer):
            value = bytearray(o.context)
            self.assertEqual(struct.unpack_from("<I", value, 48)[0], o.DEBUG_FLAGS)
            regs[:] = struct.unpack_from("<6Q", value, 72)
            self.assertEqual(tuple(regs[:4]), tuple(self.BASE + r for r in o.BREAK_RVAS))
            self.assertEqual(regs[5] & ~0x400, 0x55)
            value[48:52], value[72:120] = bytes(4), bytes(48)
            self.assertFalse(any(value), "Set only DEBUG_REGISTERS")
            return True
        def read(handle, address, output, size, length):
            if address.value == self.RSP + 0x88:
                self.assertEqual(size, 8)
                data = struct.pack("<Q", self.BASE + o.CALLER_RVA)
            elif address.value == self.BASE + o.STAGE_RVA:
                self.assertEqual(size, 2)
                data = struct.pack("<H", 600)
            else:
                i = next(i for i, (r, n, digest) in enumerate(self.WINDOWS)
                         if address.value == self.BASE + r and size == n)
                data = bytes([i + 1]) * size
            C.memmove(output, data, size)
            length.contents.value = size
            return True
        k.GetThreadContext.side_effect, k.SetThreadContext.side_effect = get, put
        k.ReadProcessMemory.side_effect = read
        k.GetThreadId.return_value, k.GetProcessIdOfThread.return_value = 19, 17

    def fixture(self):
        unused, k, stop, launch, budget = cf.DebugContextTests().fixture()
        launch.started, launch.creation_state, launch.transferred = False, "not_started", False
        images = NS(state="ready", resource_stop=False, rows=[
            {"status": "confirmed", "event_slot": 0, "name": "\\DUMMY\\KernelBase.dll"}])
        o = Probe(images)
        o.bind(stop, launch)
        launch.started, launch.creation_state, launch.transferred = True, "created", True
        raw = stop.transport.buffers[0]
        raw.kind, raw.info.load_dll.base = 6, self.BASE
        regs, hit = [0] * 6, [0]
        self.configure(o, k, regs, hit)
        return o, k, stop, launch, budget, regs, hit

    def hit(self, o, regs, hit, index=0):
        hit[0] = index
        t = o.transport
        t.count, t.pending, t.state = 2, 1, "pending"
        raw = t.buffers[1]
        raw.kind, raw.pid, raw.tid = 1, 17, 19
        info = raw.info.exception
        info.first_chance, info.record.code = 1, 0x80000004
        info.record.address = o.targets[index]
        regs[4], regs[5] = 0xFFFF0FF0 | (1 << index), 0x455
        return raw

    def test_each_site_single_set_status_and_raw_evidence_then_stop(self):
        for index in range(4):
            with self.subTest(index=index), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                o.capture(budget)
                self.hit(o, regs, hit, index)
                with self.assertRaises(TransportError) as error: o.capture(budget)
                self.assertEqual(error.exception.reason, "console_failure_observed_stop")
                self.assertEqual(o.state, "completed")
                self.assertEqual(o.row["candidate"], o.CANDIDATES[index])
                self.assertEqual(o.row["status_u32"], 0xC0000022)
                self.assertEqual(o.row["stage_value"], 600)
                self.assertEqual(o.row["stage_hex"], "5802")
                self.assertEqual(o.row["caller_hex"], struct.pack("<Q", self.BASE + o.CALLER_RVA).hex())
                self.assertEqual(o.row["connection_recovery_path_present"], index == 2)
                self.assertEqual(o.row["confirmed_bytes"], 2432)
                self.assertEqual((k.GetThreadContext.call_count, k.SetThreadContext.call_count,
                                  k.ReadProcessMemory.call_count), (3, 1, 4))
                self.assertLess(len(json.dumps({"state": o.state, "row": o.row})), 8192)
                first = o.primary
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertIs(o.primary, first)
                self.assertEqual(k.ReadProcessMemory.call_count, 4)
                for name in ("ContinueDebugEvent", "WriteProcessMemory", "SuspendThread", "ResumeThread",
                             "OpenProcess", "OpenThread", "CloseHandle"):
                    getattr(k, name).assert_not_called()

    def test_opt_in_and_mutual_exclusion(self):
        self.assertNotIsInstance(DebugDriver().context, Probe)
        for options in ({"console_failure": 1}, {"console_failure": None},
                        {"console_failure": True, "init_return": True},
                        {"console_failure": True, "unload_entry": True}):
            with self.assertRaises(TransportError): DebugDriver(**options)

    def test_load_gate_conflicts_and_code_mismatch_never_set(self):
        for fault in ("thread", "pid", "unconfirmed", "base", "dr0", "dr1", "dr2", "dr3",
                      "dr6", "dr7", "identity", "resource", "code"):
            with self.subTest(fault=fault), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                raw = o.transport.buffers[0]
                if fault == "thread": raw.tid += 1
                elif fault == "pid": raw.pid += 1
                elif fault == "unconfirmed": o.images.rows[0]["status"] = "failed"
                elif fault == "base": raw.info.load_dll.base += 1
                elif fault.startswith("dr"): regs[{"dr0": 0, "dr1": 1, "dr2": 2, "dr3": 3, "dr6": 4, "dr7": 5}[fault]] = 2
                elif fault == "identity": k.GetThreadId.return_value = 20
                elif fault == "resource": stop.resource_stop = True
                else: o.WINDOWS = ((o.WINDOWS[0][0], o.WINDOWS[0][1], "f" * 64), o.WINDOWS[1])
                with self.assertRaises(BaseException): o.capture(budget)
                k.SetThreadContext.assert_not_called()

    def test_all_native_boundaries_are_terminal_without_retry(self):
        for name, count in (("ReadProcessMemory", 4), ("GetThreadContext", 3), ("SetThreadContext", 1)):
            for index in range(1, count + 1):
                for fault in ("false", "interrupt", "oom", "resource", "event", "stop"):
                    with self.subTest(api=name, index=index, fault=fault), patch.object(Probe, "WINDOWS", self.WINDOWS):
                        o, k, stop, launch, budget, regs, hit = self.fixture()
                        function = getattr(k, name)
                        original = function.side_effect
                        def invoke(*args):
                            result = original(*args)
                            if function.call_count == index:
                                if fault == "false": return False
                                if fault == "interrupt": raise KeyboardInterrupt()
                                if fault == "oom": raise MemoryError()
                                if fault == "resource": stop.resource_stop = True
                                elif fault == "event": o.transport.buffers[o.transport.pending].kind = 9
                                else: stop.started = True
                            return result
                        function.side_effect = invoke
                        try:
                            o.capture(budget)
                            self.hit(o, regs, hit)
                            o.capture(budget)
                        except BaseException:
                            pass
                        self.assertEqual(o.state, "stopped")
                        self.assertNotIn("candidate", o.row)
                        counts = [getattr(k, n).call_count for n in ("GetThreadContext", "SetThreadContext", "ReadProcessMemory")]
                        with self.assertRaises(TransportError): o.capture(budget)
                        self.assertEqual(counts, [getattr(k, n).call_count for n in ("GetThreadContext", "SetThreadContext", "ReadProcessMemory")])
                        self.assertEqual(function.call_count, index)

    def test_short_oversized_reads_stop_before_interpretation(self):
        for index in (1, 2, 3, 4):
            for delta in (-1, 1):
                with self.subTest(index=index, delta=delta), patch.object(Probe, "WINDOWS", self.WINDOWS):
                    o, k, stop, launch, budget, regs, hit = self.fixture()
                    original = k.ReadProcessMemory.side_effect
                    def read(*args):
                        result = original(*args)
                        if k.ReadProcessMemory.call_count == index: args[-1].contents.value += delta
                        return result
                    k.ReadProcessMemory.side_effect = read
                    with self.assertRaises(TransportError):
                        o.capture(budget); self.hit(o, regs, hit); o.capture(budget)
                    self.assertEqual(k.ReadProcessMemory.call_count, index)
                    self.assertNotIn("candidate", o.row)

    def test_wrong_exception_register_or_frame_never_reads_caller(self):
        faults = ("code", "chance", "address", "flags", "record", "parameters", "thread",
                  "dr0", "dr1", "dr2", "dr3", "cause_missing", "cause_wrong", "cause_combined",
                  "bd", "bs", "bt", "dr7", "rip", "tf", "rsp", "rbp", "high_rsp", "unaligned_rsp")
        for fault in faults:
            with self.subTest(fault=fault), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                o.capture(budget)
                raw = self.hit(o, regs, hit, 2)
                record = raw.info.exception.record
                if fault == "code": record.code = 0x80000003
                elif fault == "chance": raw.info.exception.first_chance = 0
                elif fault == "address": record.address += 1
                elif fault == "flags": record.flags = 1
                elif fault == "record": record.record = 1
                elif fault == "parameters": record.parameters = 1
                elif fault == "thread": raw.tid += 1
                elif fault in ("dr0", "dr1", "dr2", "dr3"): regs[int(fault[-1])] += 1
                elif fault in ("cause_missing", "cause_wrong", "cause_combined", "bd", "bs", "bt"):
                    regs[4] = {"cause_missing": 0, "cause_wrong": 1, "cause_combined": 5,
                               "bd": 0x2004, "bs": 0x4004, "bt": 0x8004}[fault]
                elif fault == "dr7": regs[5] &= ~0x10
                else:
                    original = k.GetThreadContext.side_effect
                    def get(*args):
                        result = original(*args)
                        offset, code, value = {"rip": (248, "Q", 0), "tf": (68, "I", 0x100),
                            "rsp": (152, "Q", 0), "rbp": (160, "Q", self.RSP),
                            "high_rsp": (152, "Q", o.USER_MAX), "unaligned_rsp": (152, "Q", self.RSP + 1)}[fault]
                        struct.pack_into("<" + code, o.context, offset, value)
                        return result
                    k.GetThreadContext.side_effect = get
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertEqual(k.ReadProcessMemory.call_count, 2)
                self.assertNotIn("caller_hex", o.row)

    def test_wrong_caller_stage_or_status_is_retained_but_not_confirmed(self):
        for fault in ("caller", "stage", "status"):
            with self.subTest(fault=fault), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                o.capture(budget); self.hit(o, regs, hit)
                if fault == "status":
                    original = k.GetThreadContext.side_effect
                    def get(*args):
                        result = original(*args)
                        struct.pack_into("<I", o.context, 120, 0)
                        return result
                    k.GetThreadContext.side_effect = get
                else:
                    original = k.ReadProcessMemory.side_effect
                    def read(*args):
                        result = original(*args)
                        if args[3] == (8 if fault == "caller" else 2): C.memset(args[2], 0, args[3])
                        return result
                    k.ReadProcessMemory.side_effect = read
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertNotIn("candidate", o.row)
                self.assertEqual(k.ReadProcessMemory.call_count, 3 if fault == "caller" else 4)
                self.assertIn("caller_hex", o.row)
                if fault != "caller":
                    self.assertIn("stage_hex", o.row)
                    self.assertIn("status_u32", o.row)

    def test_each_readback_field_is_checked_before_load_continue(self):
        for offset in (72, 80, 88, 96, 104, 112, 48):
            with self.subTest(offset=offset), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                original = k.GetThreadContext.side_effect
                def get(*args):
                    result = original(*args)
                    if k.GetThreadContext.call_count == 2:
                        struct.pack_into("<I" if offset == 48 else "<Q", o.context, offset, 2)
                    return result
                k.GetThreadContext.side_effect = get
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertEqual(o.row["debug_queries"][1]["state"], "captured")
                self.assertEqual(o.row["set_state"], "query_confirmed")
                self.assertEqual(k.ReadProcessMemory.call_count, 2)
                k.ContinueDebugEvent.assert_not_called()

    def test_missed_hit_or_duplicate_module_never_rearms(self):
        for kind in (2, 4, 5, 6, 7, 9):
            with self.subTest(kind=kind), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                o.capture(budget); raw = self.hit(o, regs, hit)
                raw.kind = kind
                if kind == 6:
                    o.images.rows.append({"status": "confirmed", "event_slot": 1, "name": "\\DUMMY\\KernelBase.dll"})
                    raw.info.load_dll.base = self.BASE
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertEqual(k.ReadProcessMemory.call_count, 2)
                k.SetThreadContext.assert_called_once()

    def test_fixed_read_sequence_rejects_extra_or_other_addresses(self):
        for fault in ("address", "size", "total", "count"):
            with self.subTest(fault=fault), patch.object(Probe, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs, hit = self.fixture()
                o.capture(budget)
                o.caller_slot = self.RSP + 0x88
                address, size = o.caller_slot, 8
                if fault == "address": address += 8
                elif fault == "size": size += 8
                elif fault == "total": o.row["confirmed_bytes"] = o.BYTE_LIMIT
                else: o.row["read_attempts"] = 4
                with self.assertRaises(TransportError): o._read(address, size, budget)
                self.assertEqual(k.ReadProcessMemory.call_count, 2)

    def test_full_driver_terminates_before_exception_continue_and_retains_evidence(self):
        for fault in (None, "resource", "set_uncertain", "terminate_false"):
            for index in range(4):
                with self.subTest(fault=fault, index=index), ExitStack() as scope:
                    scope.enter_context(patch.object(Probe, "WINDOWS", self.WINDOWS))
                    driver, api, k, preflight, tokens, fixture, disk = df.DebugDriverTests().driver(scope, console_failure=True)
                    o, regs, hit = driver.context, [0] * 6, [index]
                    self.configure(o, k, regs, hit)
                    kinds, last, operations = iter((3, 6, 1, 5)), [None], []
                    def deliver(pointer, timeout):
                        raw = pointer.contents
                        raw.kind, raw.pid, raw.tid = next(kinds), 17, 19
                        last[0] = raw.kind
                        if raw.kind == 3: raw.info.create_process.file = 101
                        elif raw.kind == 6: raw.info.load_dll.file, raw.info.load_dll.base = 102, self.BASE
                        elif raw.kind == 1:
                            info = raw.info.exception
                            info.first_chance, info.record.code = 1, 0x80000004
                            info.record.address = self.BASE + o.BREAK_RVAS[index]
                            regs[4], regs[5] = 0xFFFF0FF0 | (1 << index), 0x455
                        else: raw.info.exit_code = 1
                        return True
                    def image_name(handle, buffer, size, flags):
                        buffer.value = "\\DUMMY\\" + ("python.exe" if handle == 101 else "KernelBase.dll")
                        return len(buffer.value)
                    def terminate(*args):
                        operations.append("terminate")
                        return fault != "terminate_false"
                    def resume(pid, tid, status):
                        if last[0] == 1:
                            self.assertIn("terminate", operations)
                            self.assertEqual(status, DBG_NOT_HANDLED)
                        operations.append("continue")
                        return True
                    k.WaitForDebugEventEx.side_effect = deliver
                    k.GetFinalPathNameByHandleW.side_effect = image_name
                    k.WaitForSingleObject.side_effect = lambda *a: 0 if last[0] == 5 else 258
                    k.TerminateProcess.side_effect, k.ContinueDebugEvent.side_effect = terminate, resume
                    if fault == "resource":
                        original = k.ReadProcessMemory.side_effect
                        def read(*args):
                            value = original(*args)
                            if args[3] == 8: raise MemoryError()
                            return value
                        k.ReadProcessMemory.side_effect = read
                    elif fault == "set_uncertain":
                        original = k.SetThreadContext.side_effect
                        def put(*args):
                            original(*args); raise KeyboardInterrupt()
                        k.SetThreadContext.side_effect = put
                    result = driver.run()
                    self.assertEqual(result["status"], "failed")
                    self.assertFalse(result["native_accepted"])
                    k.SetThreadContext.assert_called_once()
                    if fault == "terminate_false":
                        self.assertEqual(operations[-1], "terminate")
                        self.assertFalse(driver.stop.result["debug_ownership_resolved"])
                    else:
                        self.assertTrue(driver.stop.result["process_signaled"])
                        self.assertTrue(driver.stop.result["debug_ownership_resolved"])
                        self.assertEqual(result["teardown_status"], "pass")
                    if fault == "resource":
                        self.assertTrue(result["resource_stop"])
                        k.WriteFile.assert_not_called()
                    else:
                        self.assertEqual(result["evidence_status"], "flushed")
                        from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret
                        saved = interpret(driver.evidence.buffer.raw[:driver.evidence.size])
                        row = saved.private_metadata["context"]["row"]
                        if fault == "set_uncertain":
                            self.assertEqual(row["set_state"], "uncertain")
                            self.assertEqual(len(row["requested_debug_hex"]), 96)
                        else:
                            self.assertEqual(row["candidate"], o.CANDIDATES[index])
                            self.assertEqual(row["status_u32"], 0xC0000022)
                            self.assertEqual(saved.private_metadata["primary_reason"], "console_failure_observed_stop")
                    k.WriteProcessMemory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
