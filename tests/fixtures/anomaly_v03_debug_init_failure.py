"""Observe one initial-thread loader failure branch after verified bootstrap.

Reuse the tested one-shot debug-register protocol. Capture the fixed entry,
then terminate; never continue the hit normally, repair, or follow pointers.
"""
import hashlib
import json
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_evidence import _resource
from tests.fixtures.anomaly_v03_debug_init_return import DebugInitReturn
from tests.fixtures.anomaly_v03_debug_unload_entry import DebugUnloadEntry
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class DebugInitFailure(DebugInitReturn):
    RECIPE = "ntdll-26200.9445-init-failure-v1"
    BREAK_RVA, IMAGE_SIZE = 0xE86E, 2519040
    WINDOWS = ((0xE5D0, 845, "f86272015b824466fa57a03405df5fd1728e1bed86ffe3aab15b61faf419789c"),)
    ENTRY_SIZE = 112

    def __init__(self, images, bootstrap):
        super().__init__(images)
        self.bootstrap = bootstrap
        self.image_row = None

    def __repr__(self):
        return "DebugInitFailure(<private registers and loader entry>)"

    def _guard(self):
        super()._guard()
        if self.bootstrap.state == "verified":
            self.bootstrap._guard()

    def _active_ntdll(self):
        need(self.images.state == "ready" and not self.images.resource_stop, "init_failure_images")
        need(DebugUnloadEntry._active_image(self, self.images, self.base) is self.image_row,
             "init_failure_ntdll_lifetime")

    def _arm_bootstrap(self, budget):
        b = self.bootstrap
        need(self.state == "ready" and b is not None and b.state == "verified"
             and b.transport is self.transport and b.launch is self.launch
             and b.slot == self.transport.pending, "init_failure_bootstrap")
        b._guard()
        self.state, self.slot, self.selected_kind = "querying", self.transport.pending, 1
        self.base, self.image_row = b.image_base, b.image_row
        self.target = self.base+self.BREAK_RVA
        self.row.update(status="arming", arm_slot=self.slot, load_slot=b.row["load_slot"])
        self._active_ntdll()
        self._identity(budget)
        for rva, size, digest in self.WINDOWS:
            need(hashlib.sha256(self._read(self.base+rva,size,budget)).hexdigest()==digest,
                 "init_failure_code_mismatch")
            self.row["code_windows_confirmed"] += 1
        self._program_registers(budget)

    def _entry(self, pointer, budget):
        DebugUnloadEntry._address(pointer, self.ENTRY_SIZE, 8)
        self._budget(budget)
        need(self.row["read_attempts"] == 1, "init_failure_entry_retry")
        self.row["read_attempts"] += 1
        self.row["read_state"] = "entry_uncertain"
        self.bytes_read.value = 0
        ok = self.kernel.ReadProcessMemory(self.stop.handles[0], w.H(pointer),
                                          self.stack_pointer, self.ENTRY_SIZE, self.bytes_read_pointer)
        self.row["last_read_bytes"] = self.bytes_read.value
        self.row["entry_read_hex"] = self.stack.raw[:min(self.ENTRY_SIZE,self.bytes_read.value)].hex()
        if not ok:
            raise w._Failure("init_failure_entry_read", self.transport.last_error())
        self._budget(budget)
        need(self.bytes_read.value == self.ENTRY_SIZE, "init_failure_entry_length")
        self.row["confirmed_bytes"] += self.ENTRY_SIZE
        self.row["read_state"] = "entry_confirmed"
        return self.stack.raw[:self.ENTRY_SIZE]

    def _hit(self, raw, budget):
        self.state, self.slot, self.selected_kind = "querying", self.transport.pending, 1
        self.row.update(status="hit_uncertain", event_slot=self.slot)
        self._active_ntdll()
        info = raw.info.exception
        need(info.first_chance == 1 and info.record.code == 0x80000004
             and info.record.flags == 0 and info.record.record is None
             and info.record.parameters == 0 and info.record.address == self.target,
             "init_failure_exception")
        self._identity(budget)
        registers = self._get(self.HIT_FLAGS,budget)
        self._programmed(registers,hit=True)
        rip = struct.unpack_from("<Q",self.context,248)[0]
        status = struct.unpack_from("<I",self.context,232)[0]
        returned = struct.unpack_from("<Q",self.context,216)[0] & 255
        need(rip == self.target and struct.unpack_from("<I",self.context,68)[0] & 0x100 == 0
             and status == 0xC0000142 and returned == 0, "init_failure_branch")
        pointer = struct.unpack_from("<Q",self.context,176)[0]
        callback = struct.unpack_from("<Q",self.context,240)[0]
        entry = self._entry(pointer,budget)
        base, entrypoint = struct.unpack_from("<QQ",entry,0x30)
        size = struct.unpack_from("<I",entry,0x40)[0]
        flags = struct.unpack_from("<I",entry,0x68)[0]
        need(0 < size <= 128*1024*1024, "init_failure_image_size")
        DebugUnloadEntry._address(base,size,0x10000)
        need(entrypoint == callback and (callback == 0 or base <= callback < base+size),
             "init_failure_entrypoint")
        module = DebugUnloadEntry._active_image(self,self.images,base)
        self._budget(budget)
        self.row.update(status="confirmed", module_load_slot=module["event_slot"],
                        image_size=size, flags=flags, callback_rva=callback-base if callback else None,
                        r14_status=status, r12_low_byte=returned, intended_termination=True)
        need(len(json.dumps({"state":"completed","row":self.row},ensure_ascii=True)) <= self.JSON_LIMIT,
             "init_failure_json_size")
        self.state = "completed"
        raise TransportError("init_failure_observed_stop")

    def capture(self, budget):
        try:
            self._guard()
            raw = self.transport.buffers[self.transport.pending]
            if self.state == "ready":
                if self.bootstrap.state == "verified":
                    self._arm_bootstrap(budget)
                elif raw.kind == 5:
                    raise TransportError("init_failure_bootstrap_not_observed")
            elif self.state == "armed":
                if raw.kind == 1:
                    self._hit(raw,budget)
                elif raw.kind == 5:
                    raise TransportError("init_failure_not_observed")
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            else:
                self.secondary = error
            self.resource_stop |= _resource(error)
            if self.stop is not None:
                self.resource_stop |= self.stop.resource_stop or self.stop.drain.resource_stop or self.transport.resource_stop
                self.transport.resource_stop |= self.resource_stop
            if self.state != "completed":
                self.state = "stopped"
            raise
