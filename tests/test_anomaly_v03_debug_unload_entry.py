"""Fake-only bounded entry capture; never opens images or reads a child."""

import ctypes as C
import hashlib
import json
import struct
import unittest
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest.mock import patch

from tests import test_anomaly_v03_debug_context as context_fixtures
from tests import test_anomaly_v03_debug_driver as driver_fixtures
from tests.fixtures.anomaly_v03_debug_unload_entry import DebugUnloadEntry
from tests.fixtures.anomaly_v03_debug_transport import TransportError


class DebugUnloadEntryTests(unittest.TestCase):
    def fixture(self, *, failed=True):
        context, kernel, stop, launch, budget = context_fixtures.DebugContextTests().fixture()
        entry = DebugUnloadEntry()
        context.entry = entry
        context.row["module_entry"] = entry.row
        context.images = NS(state="ready", resource_stop=False, rows=[
            {"event_slot": 0, "status": "confirmed", "name": "\\DUMMY\\ntdll.dll"},
            {"event_slot": 1, "status": "confirmed", "name": "\\DUMMY\\target.dll"}])
        t = stop.transport
        t.count, t.pending = 3, 2
        for index in range(3):
            t.buffers[index].pid, t.buffers[index].tid = 17, 19
            t.buffers[index].kind = 6 if index < 2 else 7
        t.buffers[0].info.load_dll.base = 0x40000000
        t.buffers[1].info.load_dll.base = t.buffers[2].info.unload_base = 0x50000000
        original_context = kernel.GetThreadContext.side_effect
        def fill_context(*args):
            original_context(*args)
            struct.pack_into("<Q", context.context, 248, 0x40000000 + entry.RIP_RVA)
            struct.pack_into("<Q", context.context, 136, 0x50000000)
            struct.pack_into("<Q", context.context, 144, 0x20000)
            return True
        kernel.GetThreadContext.side_effect = fill_context
        stack = bytearray(2048)
        struct.pack_into("<Q", stack, 0, 0x40000000 + entry.RETURN_RVA)
        module = bytearray(112)
        struct.pack_into("<Q", module, 0x30, 0x50000000)
        struct.pack_into("<I", module, 0x40, 0x100000)
        struct.pack_into("<I", module, 0x68, 0xFFFFFFFF if failed else 0)
        memory = {0x10000: stack, 0x20000: module}
        windows = []
        for index, (rva, size, digest) in enumerate(entry.WINDOWS):
            data = bytes([index + 1]) * size
            memory[0x40000000 + rva] = data
            windows.append((rva, size, hashlib.sha256(data).hexdigest()))
        def read(handle, remote, local, size, length):
            self.assertEqual(handle, 101)
            self.assertFalse(stop.started)
            self.assertEqual(t.state, "pending")
            data = memory[remote.value]
            self.assertEqual(len(data), size)
            C.memmove(local, bytes(data), size)
            length.contents.value = size
            return True
        kernel.ReadProcessMemory.side_effect = read
        return context, kernel, stop, budget, memory, tuple(windows)

    def test_exact_bounds_private_payload_once_and_bit_clear_is_not_success(self):
        for failed in (True, False):
            with self.subTest(failed=failed):
                c, k, stop, budget, memory, windows = self.fixture(failed=failed)
                with patch.object(DebugUnloadEntry, "WINDOWS", windows):
                    c.capture(budget)
                    c.capture(budget)
                self.assertEqual(c.state, "completed")
                self.assertEqual(c.entry.state, "completed")
                row = c.entry.row
                self.assertEqual((row["status"], row["code_windows_confirmed"], row["confirmed_bytes"]),
                                 ("confirmed", 3, 1059))
                self.assertEqual(row["init_failure_bit"], failed)
                self.assertEqual(row["entry_hex"], bytes(memory[0x20000]).hex())
                self.assertNotIn("native_accepted", row)
                self.assertEqual([call.args[3] for call in k.ReadProcessMemory.call_args_list],
                                 [2048, 78, 24, 845, 112])
                self.assertLessEqual(len(json.dumps({"state": c.state, "row": c.row})), c.JSON_LIMIT)
                self.assertNotIn(row["entry_hex"], repr(c.entry))
                for name in ("OpenProcess", "OpenThread", "SuspendThread", "ResumeThread",
                             "SetThreadContext", "WriteProcessMemory", "CloseHandle"):
                    getattr(k, name).assert_not_called()

    def test_gate_mismatches_do_not_read_code_or_entry(self):
        for fault in ("rip", "return", "rdx", "unaligned", "out_of_range", "module_identity",
                      "ntdll_identity", "unloaded", "event_pid", "missing_image"):
            with self.subTest(fault=fault):
                c, k, stop, budget, memory, windows = self.fixture()
                original = k.GetThreadContext.side_effect
                def fill(*args):
                    original(*args)
                    if fault == "rip": struct.pack_into("<Q", c.context, 248, 0x40000000)
                    elif fault == "rdx": struct.pack_into("<Q", c.context, 136, 0x60000000)
                    elif fault == "unaligned": struct.pack_into("<Q", c.context, 144, 0x20001)
                    elif fault == "out_of_range": struct.pack_into("<Q", c.context, 144, 2**64 - 1)
                    return True
                k.GetThreadContext.side_effect = fill
                if fault == "return": memory[0x10000][:8] = b"\x00" * 8
                elif fault == "module_identity": c.images.rows[1]["status"] = "name_uncertain"
                elif fault == "ntdll_identity": c.images.rows[0]["status"] = "name_uncertain"
                elif fault == "unloaded":
                    stop.transport.buffers[0].kind = 7
                    stop.transport.buffers[0].info.unload_base = 0x40000000
                elif fault == "event_pid": stop.transport.buffers[0].pid = 18
                elif fault == "missing_image": c.images.rows[1]["event_slot"] = 15
                with patch.object(DebugUnloadEntry, "WINDOWS", windows):
                    with self.assertRaises(TransportError): c.capture(budget)
                k.ReadProcessMemory.assert_called_once()
                self.assertEqual(c.state, "stopped")
                self.assertNotIn("entry_hex", c.entry.row)

    def test_code_hash_mismatch_stops_before_candidate_read(self):
        for bad_index in range(3):
            c, k, stop, budget, memory, windows = self.fixture()
            rva, size, digest = windows[bad_index]
            memory[0x40000000 + rva] = b"X" * size
            with patch.object(DebugUnloadEntry, "WINDOWS", windows):
                with self.assertRaises(TransportError) as error:
                    c.capture(budget)
            self.assertEqual(error.exception.reason, "entry_code_mismatch")
            self.assertEqual(k.ReadProcessMemory.call_count, bad_index + 2)
            self.assertNotIn("entry_hex", c.entry.row)

    def test_false_short_oversize_interrupt_and_resource_stop_never_retry(self):
        for read_index in range(2, 6):
            for fault in ("false", "short", "oversize", "interrupt", "resource", "event_change", "stop"):
                with self.subTest(read=read_index, fault=fault):
                    c, k, stop, budget, memory, windows = self.fixture()
                    original = k.ReadProcessMemory.side_effect
                    def read(*args):
                        value = original(*args)
                        if k.ReadProcessMemory.call_count == read_index:
                            if fault == "false": return False
                            if fault == "short": args[-1].contents.value = args[3] - 1
                            elif fault == "oversize": args[-1].contents.value = args[3] + 1
                            elif fault == "interrupt": raise KeyboardInterrupt()
                            elif fault == "resource": stop.transport.resource_stop = True
                            elif fault == "event_change": stop.transport.pending = 1
                            elif fault == "stop": stop.started = True
                        return value
                    k.ReadProcessMemory.side_effect = read
                    with patch.object(DebugUnloadEntry, "WINDOWS", windows):
                        expected = (KeyboardInterrupt if fault == "interrupt" else
                                    context_fixtures.w._Failure if fault == "false" else TransportError)
                        with self.assertRaises(expected): c.capture(budget)
                        with self.assertRaises(TransportError): c.capture(budget)
                    self.assertEqual(k.ReadProcessMemory.call_count, read_index)
                    self.assertNotIn("entry_hex", c.entry.row)
                    self.assertEqual(c.state, "stopped")

    def test_cleared_size_retains_flag_without_another_read(self):
        c, k, stop, budget, memory, windows = self.fixture()
        struct.pack_into("<I", memory[0x20000], 0x40, 0)
        with patch.object(DebugUnloadEntry, "WINDOWS", windows):
            c.capture(budget)
        self.assertEqual(c.entry.row["status"], "confirmed")
        self.assertEqual(c.entry.row["image_size"], 0)
        self.assertTrue(c.entry.row["init_failure_bit"])
        self.assertEqual(k.ReadProcessMemory.call_count, 5)
        self.assertEqual(c.entry.row["confirmed_bytes"], 1059)

    def test_entry_shape_mismatch_retains_exact_read_without_confirming_fields(self):
        for offset, code, value in ((0x30, "Q", 0x60000000), (0x40, "I", 2**32 - 1)):
            c, k, stop, budget, memory, windows = self.fixture()
            struct.pack_into("<" + code, memory[0x20000], offset, value)
            with patch.object(DebugUnloadEntry, "WINDOWS", windows):
                with self.assertRaises(TransportError): c.capture(budget)
            self.assertEqual(k.ReadProcessMemory.call_count, 5)
            self.assertEqual(c.entry.row["entry_hex"], bytes(memory[0x20000]).hex())
            self.assertEqual(c.entry.row["status"], "entry_uncertain")
            self.assertNotIn("flags", c.entry.row)
            self.assertNotIn("init_failure_bit", c.entry.row)
            self.assertEqual(c.entry.state, "stopped")

    def test_outer_driver_opt_in_evidence_and_owned_stop_do_not_capture_during_drain(self):
        for detached, fault in ((detached, fault) for detached in (False, True)
                                for fault in (None, "code_mismatch", "resource", "entry_size")):
            with ExitStack() as scope, self.subTest(detached=detached, fault=fault):
                driver, api, k, preflight, tokens, fixture, disk = (
                    driver_fixtures.DebugDriverTests().driver(scope, unload_entry=True,
                                                           detached_console=detached))
                c, unused, stop, budget, memory, windows = self.fixture()
                if fault is None or fault == "entry_size":
                    struct.pack_into("<I", memory[0x20000], 0x40, 0 if fault is None else 0xFFFFFFFF)
                scope.enter_context(patch.object(DebugUnloadEntry, "WINDOWS", windows))
                events = iter((3, 6, 6, 7, 7, 5))
                last = [None]
                def deliver(pointer, timeout):
                    raw = pointer.contents
                    raw.kind, raw.pid, raw.tid = next(events), 17, 19
                    last[0] = raw.kind
                    if raw.kind == 3:
                        raw.info.create_process.file = 101
                    elif raw.kind == 6:
                        first = driver.images.count == 1
                        raw.info.load_dll.file = 102 if first else 103
                        raw.info.load_dll.base = 0x40000000 if first else 0x50000000
                    elif raw.kind == 7: raw.info.unload_base = 0x50000000
                    else: raw.info.exit_code = 0xC0000142
                    return True
                def name(handle, buffer, size, flags):
                    buffer.value = {101: "\\DUMMY\\python.exe", 102: "\\DUMMY\\ntdll.dll",
                                    103: "\\DUMMY\\target.dll"}[handle]
                    return len(buffer.value)
                def fill(handle, pointer):
                    self.assertEqual(handle, 502)
                    for offset, value in ((136, 0x50000000), (144, 0x20000), (152, 0x10000),
                                          (248, 0x40000000 + DebugUnloadEntry.RIP_RVA)):
                        struct.pack_into("<Q", driver.context.context, offset, value)
                    return True
                def read(handle, address, output, size, length):
                    self.assertFalse(driver.stop.started)
                    self.assertEqual(handle, 501)
                    if fault == "resource" and k.ReadProcessMemory.call_count == 3:
                        raise MemoryError()
                    data = bytes(memory[address.value])
                    if fault == "code_mismatch" and k.ReadProcessMemory.call_count == 2:
                        data = b"X" * size
                    self.assertEqual(len(data), size)
                    C.memmove(output, data, size)
                    length.contents.value = size
                    return True
                k.WaitForDebugEventEx.side_effect = deliver
                k.GetFinalPathNameByHandleW.side_effect = name
                k.GetThreadId.return_value = 19
                k.GetProcessIdOfThread.return_value = 17
                k.GetThreadContext.side_effect = fill
                k.ReadProcessMemory.side_effect = read
                k.WaitForSingleObject.side_effect = lambda handle, timeout: 0 if last[0] == 5 else 258
                result = driver.run()
                expected_flags = 0x40E if detached else 0x08000406
                api.a.CreateProcessAsUserW.assert_called_once()
                self.assertEqual(api.a.CreateProcessAsUserW.call_args.args[6], expected_flags)
                self.assertFalse(api.a.CreateProcessAsUserW.call_args.args[5])
                k.ResumeThread.assert_called_once_with(502)
                k.SetThreadContext.assert_not_called()
                fixture.cleanup.assert_not_called()
                self.assertEqual(driver.stop.handles, [None, None])
                k.GetThreadContext.assert_called_once()
                self.assertEqual(k.ReadProcessMemory.call_count,
                                 5 if fault in (None, "entry_size") else 2 if fault == "code_mismatch" else 3)
                self.assertEqual(result["teardown_status"], "pass")
                self.assertFalse(result["native_accepted"])
                self.assertFalse(result["formal_permission"])
                self.assertEqual(result["status"], "observed" if fault is None else "failed")
                if fault == "resource":
                    self.assertTrue(result["resource_stop"])
                    self.assertEqual(driver.evidence.capture_state, "resource_skipped")
                    k.WriteFile.assert_not_called()
                else:
                    from tests.fixtures.anomaly_v03_debug_evidence_reader import interpret
                    saved = interpret(driver.evidence.buffer.raw[:driver.evidence.size])
                    self.assertEqual(saved.private_metadata["launch"]["requested_creation_flags"], expected_flags)
                    self.assertEqual(saved.private_metadata["launch"]["creation_state"], "created")
                    row = saved.private_metadata["context"]["row"]["module_entry"]
                    if fault is None:
                        self.assertTrue(row["init_failure_bit"])
                        self.assertEqual(row["image_size"], 0)
                        self.assertEqual(row["module_load_slot"], 2)
                        self.assertEqual(row["entry_hex"], bytes(memory[0x20000]).hex())
                    elif fault == "entry_size":
                        self.assertEqual(row["entry_hex"], bytes(memory[0x20000]).hex())
                        self.assertEqual(row["image_size"], 0xFFFFFFFF)
                        self.assertEqual(row["status"], "entry_uncertain")
                        self.assertNotIn("flags", row)
                        self.assertNotIn("init_failure_bit", row)
                        self.assertEqual(driver.primary.reason, "entry_image_size")
                    else:
                        self.assertNotIn("entry_hex", row)
                        self.assertEqual(driver.primary.reason, "entry_code_mismatch")

    def test_budget_failure_after_code_read_prevents_entry_read(self):
        c, k, stop, budget, memory, windows = self.fixture()
        def budget_stop():
            if k.ReadProcessMemory.call_count == 4:
                raise MemoryError()
        with patch.object(DebugUnloadEntry, "WINDOWS", windows):
            with self.assertRaises(MemoryError): c.capture(budget_stop)
        self.assertTrue(c.resource_stop)
        self.assertEqual(k.ReadProcessMemory.call_count, 4)
        self.assertNotIn("entry_hex", c.entry.row)


if __name__ == "__main__":
    unittest.main()
