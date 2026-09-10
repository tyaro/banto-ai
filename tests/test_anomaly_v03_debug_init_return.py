"""Fake-only return-probe boundaries and full owned-termination wiring."""

import ctypes as C
import hashlib
import json
import struct
import unittest
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from tests import test_anomaly_v03_debug_context as cf
from tests import test_anomaly_v03_debug_driver as df
from tests.fixtures.anomaly_v03_debug_init_return import DebugInitReturn
from tests.fixtures.anomaly_v03_debug_transport import TransportError, DBG_NOT_HANDLED


class DebugInitReturnTests(unittest.TestCase):
    BASE = 0x50000000
    WINDOWS = tuple((rva, size, hashlib.sha256(bytes([n + 1]) * size).hexdigest())
                    for n, (rva, size, digest) in enumerate(DebugInitReturn.WINDOWS))

    def configure(self, owner, k, registers):
        def get(handle, pointer):
            self.assertEqual(pointer.value % 16, 0)
            flags = struct.unpack_from("<I", owner.context, 48)[0]
            self.assertIn(flags, (owner.DEBUG_FLAGS, owner.HIT_FLAGS))
            struct.pack_into("<6Q", owner.context, 72, *registers)
            if flags == owner.HIT_FLAGS:
                struct.pack_into("<Q", owner.context, 120, 0)
                struct.pack_into("<Q", owner.context, 144, 1)
                struct.pack_into("<Q", owner.context, 248, self.BASE + owner.BREAK_RVA)
            return True
        def put(handle, pointer):
            value = bytearray(owner.context)
            self.assertEqual(struct.unpack_from("<I", value, 48)[0], owner.DEBUG_FLAGS)
            registers[:] = struct.unpack_from("<6Q", value, 72)
            value[48:52] = bytes(4)
            value[72:120] = bytes(48)
            self.assertFalse(any(value), "Only DEBUG_REGISTERS are submitted")
            return True
        def read(handle, address, output, size, length):
            if address.value == self.BASE + owner.STAGE_RVA:
                self.assertEqual(size, 2)
                data = struct.pack("<H", 100)
            else:
                index = next(i for i, (rva, count, digest) in enumerate(self.WINDOWS)
                             if address.value == self.BASE + rva and size == count)
                data = bytes([index + 1]) * size
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
            {"status": "confirmed", "event_slot": 0, "name": "\\Device\\DUMMY\\KernelBase.dll"}])
        owner = DebugInitReturn(images)
        owner.bind(stop, launch)
        launch.started, launch.creation_state, launch.transferred = True, "created", True
        raw = stop.transport.buffers[0]
        raw.kind, raw.info.load_dll.base = 6, self.BASE
        registers = [0, 0, 0, 0, 0xFFFF0FF0, 0x400]
        self.configure(owner, k, registers)
        return owner, k, stop, launch, budget, registers

    def hit(self, owner, registers):
        t = owner.transport
        t.count, t.pending, t.state = 2, 1, "pending"
        raw = t.buffers[1]
        raw.kind, raw.pid, raw.tid = 1, 17, 19
        info = raw.info.exception
        info.first_chance, info.record.code, info.record.address = 1, 0x80000004, owner.target
        registers[4] |= 1
        return raw

    def test_exact_single_set_capture_then_terminal_observation(self):
        with patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
            owner, k, stop, launch, budget, registers = self.fixture()
            owner.capture(budget)
            self.assertEqual(owner.state, "armed")
            self.assertEqual(owner.row["set_state"], "verified")
            self.hit(owner, registers)
            with self.assertRaises(TransportError) as error:
                owner.capture(budget)
            self.assertEqual(error.exception.reason, "init_return_observed_stop")
            self.assertEqual(owner.state, "completed")
            self.assertEqual(owner.row["stage_value"], 100)
            self.assertTrue(owner.row["returns_false"])
            self.assertEqual(owner.row["confirmed_bytes"], 2197)
            self.assertEqual((k.GetThreadContext.call_count, k.SetThreadContext.call_count,
                              k.ReadProcessMemory.call_count), (3, 1, 3))
            first = owner.primary
            with self.assertRaises(TransportError): owner.capture(budget)
            self.assertIs(owner.primary, first)
            for name in ("ContinueDebugEvent", "WriteProcessMemory", "SuspendThread", "ResumeThread",
                         "OpenProcess", "OpenThread", "CloseHandle"):
                getattr(k, name).assert_not_called()
            self.assertLess(len(json.dumps({"state": owner.state, "row": owner.row})), 8192)

    def test_load_gate_and_debug_slot_conflicts_never_set(self):
        for fault in ("wrong_thread", "wrong_pid", "unconfirmed", "images_stopped", "base",
                      "code", "dr0", "dr1", "dr7", "dr6", "identity", "resource"):
            with self.subTest(fault=fault), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs = self.fixture()
                if fault == "wrong_thread": o.transport.buffers[0].tid = 20
                elif fault == "wrong_pid": o.transport.buffers[0].pid = 99
                elif fault == "unconfirmed": o.images.rows[0]["status"] = "uncertain"
                elif fault == "images_stopped": o.images.resource_stop = True
                elif fault == "base": o.transport.buffers[0].info.load_dll.base = o.USER_MAX
                elif fault == "code": k.ReadProcessMemory.side_effect = lambda *a: True
                elif fault.startswith("dr"): regs[{"dr0": 0, "dr1": 1, "dr7": 5, "dr6": 4}[fault]] |= 2
                elif fault == "identity": k.GetThreadId.return_value = 20
                else: stop.resource_stop = True
                with self.assertRaises(BaseException): o.capture(budget)
                k.SetThreadContext.assert_not_called()
                self.assertNotIn("stage_value", o.row)

    def test_each_native_boundary_failure_is_terminal_and_not_retried(self):
        cases = [("ReadProcessMemory", i) for i in (1, 2, 3)] + [
            ("GetThreadContext", i) for i in (1, 2, 3)] + [("SetThreadContext", 1)]
        for name, index in cases:
            for fault in ("false", "interrupt", "oom", "resource", "event_change", "stop"):
                with self.subTest(api=name, index=index, fault=fault), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                    o, k, stop, launch, budget, regs = self.fixture()
                    function = getattr(k, name)
                    original = function.side_effect
                    def invoke(*args):
                        result = original(*args)
                        if function.call_count == index:
                            if fault == "false": return False
                            if fault == "interrupt": raise KeyboardInterrupt()
                            if fault == "oom": raise MemoryError()
                            if fault == "resource": stop.resource_stop = True
                            elif fault == "event_change": o.transport.buffers[o.transport.pending].kind = 9
                            else: stop.started = True
                        return result
                    function.side_effect = invoke
                    try:
                        o.capture(budget)
                        self.hit(o, regs)
                        o.capture(budget)
                    except BaseException:
                        pass
                    self.assertEqual(o.state, "stopped")
                    counts = [getattr(k, n).call_count for n in ("GetThreadContext", "SetThreadContext", "ReadProcessMemory")]
                    first = o.primary
                    with self.assertRaises(TransportError): o.capture(budget)
                    self.assertIs(o.primary, first)
                    self.assertEqual(counts, [getattr(k, n).call_count for n in ("GetThreadContext", "SetThreadContext", "ReadProcessMemory")])
                    self.assertEqual(function.call_count, index)
                    self.assertNotIn("stage_value", o.row)
                    if name == "GetThreadContext":
                        self.assertNotIn("debug_hex", o.row["debug_queries"][index - 1])

    def test_short_and_oversized_reads_never_confirm_stage(self):
        for index in (1, 2, 3):
            for delta in (-1, 1):
                with self.subTest(index=index, delta=delta), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                    o, k, stop, launch, budget, regs = self.fixture()
                    original = k.ReadProcessMemory.side_effect
                    def read(*args):
                        result = original(*args)
                        if k.ReadProcessMemory.call_count == index: args[-1].contents.value += delta
                        return result
                    k.ReadProcessMemory.side_effect = read
                    with self.assertRaises(TransportError):
                        o.capture(budget)
                        self.hit(o, regs)
                        o.capture(budget)
                    self.assertNotIn("stage_value", o.row)
                    self.assertEqual(k.ReadProcessMemory.call_count, index)

    def test_wrong_exception_or_context_never_reads_stage(self):
        for fault in ("code", "chance", "address", "flags", "record", "parameters", "thread",
                      "dr0", "dr6", "dr6_b0_clear", "dr7", "rip", "reason", "trap"):
            with self.subTest(fault=fault), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs = self.fixture()
                o.capture(budget)
                raw = self.hit(o, regs)
                if fault == "code": raw.info.exception.record.code = 0x80000003
                elif fault == "chance": raw.info.exception.first_chance = 0
                elif fault == "address": raw.info.exception.record.address += 1
                elif fault == "flags": raw.info.exception.record.flags = 1
                elif fault == "record": raw.info.exception.record.record = 0x10000
                elif fault == "parameters": raw.info.exception.record.parameters = 1
                elif fault == "thread": raw.tid = 20
                elif fault == "dr0": regs[0] += 1
                elif fault == "dr6": regs[4] |= 2
                elif fault == "dr6_b0_clear": regs[4] &= ~1
                elif fault == "dr7": regs[5] |= 2
                else:
                    original = k.GetThreadContext.side_effect
                    def get(*args):
                        result = original(*args)
                        off, code, value = {"rip": (248, "Q", 0x10000), "reason": (144, "Q", 0), "trap": (68, "I", 0x100)}[fault]
                        struct.pack_into("<" + code, o.context, off, value)
                        return result
                    k.GetThreadContext.side_effect = get
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertEqual(k.ReadProcessMemory.call_count, 2)
                self.assertNotIn("return_byte", o.row)

    def test_driver_terminates_before_releasing_exception_and_retains_evidence(self):
        for fault in (None, "normalized_dr6", "resource", "set_uncertain", "readback_mismatch", "terminate_false"):
            with self.subTest(fault=fault), ExitStack() as scope:
                scope.enter_context(patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS))
                driver, api, k, preflight, tokens, fixture, disk = df.DebugDriverTests().driver(scope, init_return=True)
                o = driver.context
                regs = [0, 0, 0, 0, 0xFFFF0FF0, 0x400]
                self.configure(o, k, regs)
                kinds = iter((3, 6, 1, 5))
                last = [None]
                operations = []
                def deliver(pointer, timeout):
                    raw = pointer.contents
                    raw.kind, raw.pid, raw.tid = next(kinds), 17, 19
                    last[0] = raw.kind
                    if raw.kind == 3: raw.info.create_process.file = 101
                    elif raw.kind == 6:
                        raw.info.load_dll.file, raw.info.load_dll.base = 102, self.BASE
                    elif raw.kind == 1:
                        raw.info.exception.first_chance = 1
                        raw.info.exception.record.code = 0x80000004
                        raw.info.exception.record.address = self.BASE + o.BREAK_RVA
                        regs[4] |= 1
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
                        if args[3] == 2: raise MemoryError()
                        return value
                    k.ReadProcessMemory.side_effect = read
                elif fault == "set_uncertain":
                    original = k.SetThreadContext.side_effect
                    def put(*args):
                        original(*args)
                        raise KeyboardInterrupt()
                    k.SetThreadContext.side_effect = put
                elif fault in ("readback_mismatch", "normalized_dr6"):
                    original = k.GetThreadContext.side_effect
                    def get(*args):
                        result = original(*args)
                        if k.GetThreadContext.call_count == 2:
                            struct.pack_into("<Q", o.context, 104, 2 if fault == "readback_mismatch" else 0)
                        return result
                    k.GetThreadContext.side_effect = get
                result = driver.run()
                self.assertEqual(result["status"], "failed")
                self.assertFalse(result["native_accepted"])
                self.assertEqual(k.SetThreadContext.call_count, 1)
                if fault == "terminate_false":
                    self.assertEqual(operations[-1], "terminate")
                    self.assertFalse(driver.stop.result["process_signaled"])
                    self.assertEqual(result["teardown_status"], "failed")
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
                    elif fault == "readback_mismatch":
                        query = row["debug_queries"][1]
                        self.assertEqual(query["state"], "captured")
                        self.assertEqual(struct.unpack_from("<Q", bytes.fromhex(query["debug_hex"]), 32)[0], 2)
                        self.assertFalse(row["debug_checks"]["matches"]["dr6_standard_cause_matches"])
                        self.assertEqual(saved.private_metadata["primary_reason"], "return_debug_registers")
                        self.assertNotIn("stage_value", row)
                    else:
                        self.assertEqual(row["status"], "confirmed")
                        self.assertEqual(row["stage_value"], 100)
                        self.assertEqual(saved.private_metadata["primary_reason"], "init_return_observed_stop")
                        if fault == "normalized_dr6":
                            queries = row["debug_queries"]
                            values = [struct.unpack_from("<Q", bytes.fromhex(q["debug_hex"]), 32)[0] for q in queries]
                            self.assertEqual(values[1:], [0, 0xFFFF0FF1])
                            self.assertEqual(row["debug_checks"]["dr6_compared_mask"], 0xE00F)
                k.WriteProcessMemory.assert_not_called()

    def test_opt_in_is_explicit_and_mutually_exclusive(self):
        from tests.fixtures.anomaly_v03_debug_driver import DebugDriver
        self.assertNotIsInstance(DebugDriver().context, DebugInitReturn)
        for options in ({"init_return": 1}, {"init_return": None}, {"init_return": True, "unload_entry": True}):
            with self.assertRaises(TransportError): DebugDriver(**options)

    def test_readback_mismatch_stops_before_resuming_load(self):
        for fault in ("dr0", "dr6", "dr7", "flags"):
            with self.subTest(fault=fault), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs = self.fixture()
                original = k.GetThreadContext.side_effect
                def get(*args):
                    result = original(*args)
                    if k.GetThreadContext.call_count == 2:
                        offset, code, value = {"dr0": (72, "Q", 0), "dr6": (104, "Q", 2),
                                               "dr7": (112, "Q", 0), "flags": (48, "I", 0)}[fault]
                        struct.pack_into("<" + code, o.context, offset, value)
                    return result
                k.GetThreadContext.side_effect = get
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertEqual(o.state, "stopped")
                self.assertNotEqual(o.row["set_state"], "verified")
                query = o.row["debug_queries"][1]
                self.assertEqual(query["state"], "captured")
                self.assertEqual(len(query["debug_hex"]), 96)
                if fault == "flags":
                    self.assertEqual(query["returned_flags"], 0)
                    self.assertNotIn("debug_checks", o.row)
                else:
                    key = {"dr0": "dr0_matches", "dr6": "dr6_standard_cause_matches", "dr7": "dr7_matches"}[fault]
                    self.assertFalse(o.row["debug_checks"]["matches"][key])
                k.SetThreadContext.assert_called_once()
                k.ContinueDebugEvent.assert_not_called()

    def test_successful_get_with_bad_flags_retains_raw_but_not_valid_observation(self):
        for index in (1, 3):
            with self.subTest(index=index), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs = self.fixture()
                original = k.GetThreadContext.side_effect
                def get(*args):
                    result = original(*args)
                    if k.GetThreadContext.call_count == index:
                        struct.pack_into("<I", o.context, 48, 0)
                    return result
                k.GetThreadContext.side_effect = get
                with self.assertRaises(TransportError) as error:
                    o.capture(budget)
                    self.hit(o, regs)
                    o.capture(budget)
                self.assertEqual(error.exception.reason, "return_context_flags")
                query = o.row["debug_queries"][index - 1]
                self.assertEqual(query["state"], "captured")
                self.assertEqual(query["returned_flags"], 0)
                self.assertEqual(len(query["debug_hex"]), 96)
                self.assertEqual("context_hex" in o.row, index == 3)
                self.assertEqual(o.state, "stopped")
                self.assertNotIn("return_byte", o.row)
                self.assertNotIn("stage_value", o.row)

    def test_zero_dr6_baseline_nonzero_return_and_unknown_stage_are_preserved(self):
        with patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
            o, k, stop, launch, budget, regs = self.fixture()
            regs[4] = 0
            o.capture(budget)
            self.assertEqual(regs[4], 0x10800)
            self.hit(o, regs)
            original = k.GetThreadContext.side_effect
            def get(*args):
                value = original(*args)
                struct.pack_into("<Q", o.context, 120, 0xFFFFFFFFFFFFFFFF)
                return value
            k.GetThreadContext.side_effect = get
            def read(handle, address, output, size, length):
                self.assertEqual(size, 2)
                C.memmove(output, b"\xff\xff", 2)
                length.contents.value = 2
                return True
            k.ReadProcessMemory.side_effect = read
            with self.assertRaises(TransportError): o.capture(budget)
            self.assertEqual(o.row["return_byte"], 255)
            self.assertEqual(o.row["stage_value"], 65535)
            self.assertFalse(o.row["returns_false"])
            self.assertEqual(o.state, "completed")
            self.assertLess(len(json.dumps({"state": o.state, "row": o.row})), 8192)

    def test_missed_hit_and_duplicate_module_never_rearm(self):
        for kind in (2, 4, 5, 6, 7, 9):
            with self.subTest(kind=kind), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                o, k, stop, launch, budget, regs = self.fixture()
                o.capture(budget)
                raw = self.hit(o, regs)
                raw.kind = kind
                if kind == 6:
                    o.images.rows.append({"status": "confirmed", "event_slot": 1, "name": "\\DUMMY\\KernelBase.dll"})
                    raw.info.load_dll.base = self.BASE
                with self.assertRaises(TransportError): o.capture(budget)
                self.assertEqual(o.state, "stopped")
                self.assertEqual(k.ReadProcessMemory.call_count, 2)
                k.SetThreadContext.assert_called_once()

    def test_dr6_api_representation_does_not_hide_other_reported_causes(self):
        for baseline in (0, 0x10800, 0xFFFF0FF0):
            for reported in (1, 0x10801, 0xFFFF0FF1, 0, 3, 5, 9, 0x2001, 0x4001, 0x8001):
                with self.subTest(baseline=baseline, reported=reported), patch.object(DebugInitReturn, "WINDOWS", self.WINDOWS):
                    o, k, stop, launch, budget, regs = self.fixture()
                    original = k.GetThreadContext.side_effect
                    def get(*args):
                        result = original(*args)
                        if k.GetThreadContext.call_count == 2:
                            struct.pack_into("<Q", o.context, 104, baseline)
                        elif k.GetThreadContext.call_count == 3:
                            struct.pack_into("<Q", o.context, 104, reported)
                        return result
                    k.GetThreadContext.side_effect = get
                    o.capture(budget)
                    self.hit(o, regs)
                    with self.assertRaises(TransportError) as error: o.capture(budget)
                    valid = reported in (1, 0x10801, 0xFFFF0FF1)
                    self.assertEqual(error.exception.reason,
                                     "init_return_observed_stop" if valid else "return_debug_registers")
                    self.assertEqual("stage_value" in o.row, valid)
                    self.assertEqual(k.ReadProcessMemory.call_count, 3 if valid else 2)
                    queries = o.row["debug_queries"]
                    self.assertEqual(struct.unpack_from("<Q", bytes.fromhex(queries[2]["debug_hex"]), 32)[0], reported)
                    k.SetThreadContext.assert_called_once()


if __name__ == "__main__":
    unittest.main()
