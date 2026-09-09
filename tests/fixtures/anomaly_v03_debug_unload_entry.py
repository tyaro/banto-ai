"""Opt-in, bounded read of the first unload's candidate loader entry.

No new handles, callbacks, writes, symbols, stack walk or pointer traversal.
Three exact code-window hashes gate one 112-byte read through borrowed ownership.
All data and partial buffers remain on the private context/evidence owner.
"""

import ctypes as C
import hashlib
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_transport import need


class DebugUnloadEntry:
    RECIPE = "ntdll-26200.9445-unload-v2"
    RIP_RVA, RETURN_RVA = 0x161304, 0xA7956
    ENTRY_SIZE = 112
    USER_MAX = 0x00007FFFFFFFFFFF
    WINDOWS = (
        (0xA7914, 78, "e0a563e3a45030256777f689a5762c637e3f286542eab1a002adb9a55fd6593b"),
        (0x1612F0, 24, "14116fd0c31066a6d45243a44f006cc6725bb451c1e7fed5a57e074e5f3ad058"),
        (0xE5D0, 845, "f86272015b824466fa57a03405df5fd1728e1bed86ffe3aab15b61faf419789c"),
    )

    def __init__(self):
        self.scratch = C.create_string_buffer(845)
        self.pointer = C.cast(self.scratch, w.H)
        self.bytes_read = C.c_size_t()
        self.length_pointer = C.pointer(self.bytes_read)
        self.state = "ready"
        self.row = {"status": "not_started", "recipe": self.RECIPE,
                    "code_windows_confirmed": 0, "confirmed_bytes": 0}

    def __repr__(self):
        return "DebugUnloadEntry(<private partial memory>)"

    @classmethod
    def _address(cls, address, size, alignment=1):
        need(type(address) is int and 0x10000 <= address <= cls.USER_MAX - size + 1
             and address % alignment == 0, "entry_address")

    @staticmethod
    def _active_image(context, images, base):
        t, slot = context.transport, context.slot
        active = None
        for index in range(slot):
            event = t.buffers[index]
            need(event.pid == t.pid, "entry_event_pid")
            if event.kind == 6 and event.info.load_dll.base == base:
                need(active is None, "entry_image_overlap")
                active = index
            elif event.kind == 7 and event.info.unload_base == base:
                active = None
        matches = [row for row in images.rows if row is not None
                   and row.get("event_slot") == active and row.get("status") == "confirmed"]
        need(active is not None and len(matches) == 1, "entry_image_unconfirmed")
        return matches[0]

    def _read(self, context, budget, address, size, stage):
        self._address(address, size)
        need(0 < size <= C.sizeof(self.scratch), "entry_read_size")
        context._budget(budget)
        self.bytes_read.value = 0
        self.row["status"] = stage + "_uncertain"
        ok = context.kernel.ReadProcessMemory(context.stop.handles[0], w.H(address),
                                              self.pointer, size, self.length_pointer)
        self.row["last_read_bytes"] = self.bytes_read.value
        if not ok:
            self.row["status"] = stage + "_failed"
            raise w._Failure("entry_memory_read", context.transport.last_error())
        context._budget(budget)
        need(self.bytes_read.value == size, "entry_read_length")
        self.row["confirmed_bytes"] += size
        return self.scratch.raw[:size]

    def capture(self, context, images, budget):
        need(self.state == "ready", "entry_retry")
        self.state = "querying"
        try:
            context._budget(budget)
            need(context.row["status"] == "confirmed" and context.slot is not None
                 and context.row["context_state"] == context.row["stack_state"] == "confirmed",
                 "entry_context_unconfirmed")
            need(images is not None and images.state == "ready" and not images.resource_stop,
                 "entry_images_unconfirmed")
            t, slot = context.transport, context.slot
            raw = t.buffers[slot]
            unload_base = raw.info.unload_base
            self._address(unload_base, 1, 0x10000)
            target = self._active_image(context, images, unload_base)
            candidates = [row for row in images.rows if row is not None
                          and row.get("status") == "confirmed"
                          and row.get("name", "").casefold().endswith("\\ntdll.dll")]
            need(len(candidates) == 1, "entry_ntdll_unique")
            image_slot = candidates[0]["event_slot"]
            need(type(image_slot) is int and 0 <= image_slot < slot
                 and t.buffers[image_slot].kind == 6, "entry_ntdll_event")
            ntdll_base = t.buffers[image_slot].info.load_dll.base
            self._address(ntdll_base, 0x161308, 0x10000)
            need(self._active_image(context, images, ntdll_base) is candidates[0]
                 and unload_base != ntdll_base, "entry_ntdll_inactive")
            rip = struct.unpack_from("<Q", context.context, 248)[0]
            rdx = struct.unpack_from("<Q", context.context, 136)[0]
            rbx = struct.unpack_from("<Q", context.context, 144)[0]
            return_address = struct.unpack_from("<Q", context.stack, 0)[0]
            need(rip == ntdll_base + self.RIP_RVA and return_address == ntdll_base + self.RETURN_RVA
                 and rdx == unload_base, "entry_callsite_mismatch")
            self._address(rbx, self.ENTRY_SIZE, 8)
            self.row.update(ntdll_load_slot=image_slot, module_load_slot=target["event_slot"])
            for rva, size, digest in self.WINDOWS:
                data = self._read(context, budget, ntdll_base + rva, size, "code")
                need(hashlib.sha256(data).hexdigest() == digest, "entry_code_mismatch")
                self.row["code_windows_confirmed"] += 1
            data = self._read(context, budget, rbx, self.ENTRY_SIZE, "entry")
            size = struct.unpack_from("<I", data, 0x40)[0]
            # Exact read completion is distinct from interpreting its fields.
            # Retain these bounded private bytes even when a later check fails.
            self.row.update(entry_hex=data.hex(), image_size=size)
            need(struct.unpack_from("<Q", data, 0x30)[0] == unload_base, "entry_base_mismatch")
            # LdrpUnloadNode can clear +0x40 before LdrpUnmapModule is called.
            # Size does not control any read length or additional pointer walk.
            need(size <= 128 * 1024 * 1024, "entry_image_size")
            self._address(unload_base, max(1, size), 0x10000)
            flags = struct.unpack_from("<I", data, 0x68)[0]
            context._budget(budget)
            self.row.update(status="confirmed", flags=flags,
                            init_failure_bit=bool(flags & 0x100000))
            self.state = "completed"
        except BaseException:
            self.state = "stopped"
            raise
