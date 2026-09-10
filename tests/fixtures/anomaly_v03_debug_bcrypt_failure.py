"""Observe the first of four fixed bcrypt initialization failure branches."""
import hashlib
import json
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_init_failure import DebugInitFailure
from tests.fixtures.anomaly_v03_debug_console_failure import DebugConsoleFailure
from tests.fixtures.anomaly_v03_debug_unload_entry import DebugUnloadEntry
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class DebugBcryptFailure(DebugInitFailure):
    RECIPE = "bcrypt-26200.9445-failure-v1"
    IMAGE_SIZE = 172032
    BREAK_RVAS = (0xB270, 0xB24D, 0xB22D, 0x1128D)
    CANDIDATES = ("call_b3b8", "call_b348", "call_59e0", "module_handle_last_error")
    CALLER_RVA = 0x111CF
    WINDOWS = (
        (0x11140, 475, "7ad0379a750d6a424bdae27d8d4800b5562e59bc73a59547915a86806990e75a"),
        (0xB1C0, 247, "4deae110e20cec3932557987e6fcc1814cad99931cc2d02ac0499cf192f3260b"),
    )

    def __init__(self, images, bootstrap):
        super().__init__(images, bootstrap)
        self.targets = self.hit_index = self.hit_raw = None

    def __repr__(self):
        return "DebugBcryptFailure(<private registers and caller>)"

    # Use the existing four-address, DEBUG_REGISTERS-only single Set protocol.
    _programmed = DebugConsoleFailure._programmed
    _program_registers = DebugConsoleFailure._program_registers

    def _active_bcrypt(self):
        need(self.images.state == "ready" and not self.images.resource_stop, "bcrypt_images")
        need(DebugUnloadEntry._active_image(self, self.images, self.base) is self.image_row,
             "bcrypt_image_lifetime")

    def _guard(self):
        super()._guard()
        if self.image_row is not None and self.slot is not None:
            self._active_bcrypt()
        if self.hit_raw is not None:
            need(bytes(self.transport.buffers[self.slot]) == self.hit_raw, "bcrypt_hit_changed")

    def _arm_bootstrap(self, budget):
        b = self.bootstrap
        need(self.state == "ready" and b is not None and b.state == "verified"
             and b.transport is self.transport and b.launch is self.launch
             and b.slot == self.transport.pending, "bcrypt_bootstrap")
        b._guard()
        self.state, self.slot, self.selected_kind = "querying", self.transport.pending, 1
        rows = [row for row in self.images.rows if row is not None and row.get("status") == "confirmed"
                and row.get("name", "").casefold().endswith("\\bcrypt.dll")]
        need(len(rows) == 1, "bcrypt_image_unique")
        row = rows[0]
        index = row["event_slot"]
        need(type(index) is int and 0 <= index < self.slot, "bcrypt_load_slot")
        load = self.transport.buffers[index]
        need(load.kind == 6 and load.pid == self.transport.pid, "bcrypt_load_event")
        self.base = load.info.load_dll.base
        DebugUnloadEntry._address(self.base, self.IMAGE_SIZE, 0x10000)
        self.image_row = row
        self._active_bcrypt()
        self.targets = tuple(self.base+rva for rva in self.BREAK_RVAS)
        self.row.update(status="arming", arm_slot=self.slot, load_slot=index)
        self._identity(budget)
        for rva, size, digest in self.WINDOWS:
            need(hashlib.sha256(self._read(self.base+rva, size, budget)).hexdigest() == digest,
                 "bcrypt_code_mismatch")
            self.row["code_windows_confirmed"] += 1
        self._program_registers(budget)

    def _caller(self, rsp, budget):
        DebugUnloadEntry._address(rsp, 0x50, 16)
        self._budget(budget)
        need(self.row["read_attempts"] == 2 and self.row["confirmed_bytes"] == 722,
             "bcrypt_caller_retry")
        self.row["read_attempts"] += 1
        self.row["read_state"] = "caller_uncertain"
        self.bytes_read.value = 0
        ok = self.kernel.ReadProcessMemory(self.stop.handles[0], w.H(rsp+0x48),
                                          self.stack_pointer, 8, self.bytes_read_pointer)
        self.row["last_read_bytes"] = self.bytes_read.value
        self.row["caller_hex"] = self.stack.raw[:min(8, self.bytes_read.value)].hex()
        if not ok:
            raise w._Failure("bcrypt_caller_read", self.transport.last_error())
        self._budget(budget)
        need(self.bytes_read.value == 8, "bcrypt_caller_length")
        self.row["confirmed_bytes"] += 8
        self.row["read_state"] = "caller_confirmed"
        need(struct.unpack("<Q", self.stack.raw[:8])[0] == self.base+self.CALLER_RVA,
             "bcrypt_caller_mismatch")
        self.row["caller_rva"] = self.CALLER_RVA

    def _hit(self, raw, budget):
        self.state, self.slot, self.selected_kind = "querying", self.transport.pending, 1
        self.hit_raw = bytes(raw)
        self.row.update(status="hit_uncertain", event_slot=self.slot)
        self._active_bcrypt()
        info = raw.info.exception
        need(info.first_chance == 1 and info.record.code == 0x80000004
             and info.record.flags == 0 and info.record.record is None
             and info.record.parameters == 0 and info.record.address in self.targets,
             "bcrypt_exception")
        self.hit_index = self.targets.index(info.record.address)
        self.row.update(hit_index=self.hit_index, hit_rva=self.BREAK_RVAS[self.hit_index])
        self._identity(budget)
        registers = self._get(self.HIT_FLAGS, budget)
        self._programmed(registers, hit=True)
        need(struct.unpack_from("<Q", self.context, 248)[0] == self.targets[self.hit_index]
             and struct.unpack_from("<I", self.context, 68)[0] & 0x100 == 0, "bcrypt_callsite")
        value = struct.unpack_from("<I", self.context, 120)[0]
        self.row.update(status_u32=value, candidate=self.CANDIDATES[self.hit_index],
                        status_domain="unclassified_nonzero" if self.hit_index < 3 else "win32_candidate")
        if self.hit_index < 3:
            need(value != 0 and struct.unpack_from("<I", self.context, 144)[0] == value,
                 "bcrypt_result")
            self._caller(struct.unpack_from("<Q", self.context, 152)[0], budget)
        else:
            # The entry path preserves hInstance in RDI and zero in ESI.
            # Keep GetLastError zero as an observed value, without interpretation.
            need(struct.unpack_from("<Q", self.context, 176)[0] == self.base
                 and struct.unpack_from("<I", self.context, 168)[0] == 0, "bcrypt_entry_frame")
        self._budget(budget)
        self.row.update(status="confirmed", intended_termination=True)
        need(len(json.dumps({"state": "completed", "row": self.row}, ensure_ascii=True)) <= self.JSON_LIMIT,
             "bcrypt_json_size")
        self.state = "completed"
        raise TransportError("bcrypt_failure_observed_stop")
