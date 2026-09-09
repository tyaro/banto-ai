"""Bounded read-only token default ACL and kernel-object SD observations.

Borrowed handles only. No access decision, ACL mutation, reopen, close or retry.
All pointer interpretation is restricted to the owned GetTokenInformation buffer.
"""

import ctypes as C
import struct
import threading

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_evidence import _resource
from tests.fixtures.anomaly_v03_debug_transport import need


def _sid_end(raw, offset, limit):
    need(0 <= offset <= limit - 8 and raw[offset] == 1 and raw[offset + 1] <= 15, "security_sid")
    end = offset + 8 + 4 * raw[offset + 1]
    need(end <= limit, "security_sid_size")
    return end


def _acl(raw, offset):
    need(0 <= offset <= len(raw) - 8, "security_acl_header")
    revision, unused, size, count, unused2 = struct.unpack_from("<BBHHH", raw, offset)
    need(revision in (2, 4) and 8 <= size <= len(raw) - offset and size % 4 == 0,
         "security_acl_size")
    cursor, end, unknown = offset + 8, offset + size, 0
    need(count <= (size - 8) // 4, "security_ace_count")
    for _ in range(count):
        need(cursor <= end - 4, "security_ace_header")
        kind, flags, length = struct.unpack_from("<BBH", raw, cursor)
        need(length >= 4 and length % 4 == 0 and cursor + length <= end, "security_ace_size")
        if kind in (0, 1, 17):
            need(length >= 16, "security_basic_ace")
            need(_sid_end(raw, cursor + 8, cursor + length) == cursor + length, "security_ace_sid")
        else:
            unknown += 1  # Preserve opaque ACE bytes; never infer permissions.
        cursor += length
    return {"state": "empty" if count == 0 else "present", "ace_count": count,
            "opaque_ace_count": unknown}, end


def _descriptor(raw):
    need(len(raw) >= 20, "security_sd_header")
    revision, unused, control, owner, group, sacl, dacl = struct.unpack_from("<BBHIIII", raw)
    need(revision == 1 and control & 0x8000, "security_sd_relative")
    result = {"control": control}
    for name, offset in (("owner", owner), ("group", group)):
        if offset:
            need(offset >= 20 and offset % 4 == 0, "security_sid_offset")
            _sid_end(raw, offset, len(raw))
        result[name] = "present" if offset else "absent"
    for name, offset, flag in (("dacl", dacl, 4), ("sacl", sacl, 16)):
        if not control & flag:
            need(offset == 0, "security_acl_absent_offset")
            result[name] = {"state": "absent"}
        elif offset == 0:
            result[name] = {"state": "null"}
        else:
            need(offset >= 20 and offset % 4 == 0, "security_acl_offset")
            result[name], unused_end = _acl(raw, offset)
    return result


class DebugSecurity:
    CAPACITY = 1024
    TARGETS = ("parent_token", "restricted_token", "child_token", "child_process", "initial_thread")

    def __init__(self):
        need(C.sizeof(w.H) == 8, "security_abi")
        self.buffers = tuple(C.create_string_buffer(self.CAPACITY) for _ in self.TARGETS)
        self.pointers = tuple(C.cast(buffer, w.H) for buffer in self.buffers)
        self.lengths = tuple(w.D() for _ in self.TARGETS)
        self.length_pointers = tuple(C.pointer(length) for length in self.lengths)
        self.rows = [{"target": target, "status": "not_started"} for target in self.TARGETS]
        for index, row in enumerate(self.rows):
            if index < 3:
                row["information_class"] = 6
            else:
                row.update(requested_information=0x17, sacl_scope="mandatory_label_only")
        self.api = None
        self.state = "ready"
        self.resource_stop = False
        self.primary = self.secondary = None
        self.creator_thread = threading.get_ident()

    def __repr__(self):
        return "DebugSecurity(<private descriptor buffers>)"

    def bind(self, api):
        need(self.api is None and self.state == "ready", "security_rebind")
        self.api = api
        if isinstance(api.a, C.CDLL):
            function = api.a.GetKernelObjectSecurity
            function.restype, function.argtypes = w.B, (w.H, w.D, w.H, w.D, C.POINTER(w.D))

    def capture(self, index, handle, budget):
        try:
            need(threading.get_ident() == self.creator_thread, "security_thread")
            need(self.state == "ready" and not self.resource_stop and self.api is not None, "security_stopped")
            need(type(index) is int and 0 <= index < 5 and self.rows[index]["status"] == "not_started",
                 "security_retry")
            need(type(handle) is int and 0 < handle < w.H(-1).value, "security_handle")
            self.state = "querying"
            row = self.rows[index]
            row["status"] = "preparing"
            budget()
            row["status"] = "uncertain"
            if index < 3:
                ok = self.api.a.GetTokenInformation(handle, 6, self.pointers[index], self.CAPACITY,
                                                     self.length_pointers[index])
            else:
                # OWNER | GROUP | DACL | LABEL, not an audit-SACL request.
                ok = self.api.a.GetKernelObjectSecurity(handle, 0x17, self.pointers[index], self.CAPACITY,
                                                        self.length_pointers[index])
            if not ok:
                row["status"] = "failed"
                raise w._Failure("security_query", C.get_last_error())
            row["status"] = "query_confirmed"
            size = self.lengths[index].value
            need(0 < size <= self.CAPACITY, "security_return_length")
            budget()
            raw = self.buffers[index].raw[:size]
            if index < 3:
                need(size >= 8, "security_token_header")
                address = int.from_bytes(raw[:8], "little")
                if address == 0:
                    value, content = {"state": "null"}, b""
                else:
                    offset = address - self.pointers[index].value
                    need(offset >= 8 and offset % 4 == 0, "security_token_pointer")
                    value, end = _acl(raw, offset)
                    content = raw[offset:end]
                row.update(acl=value, acl_hex=content.hex())
            else:
                row.update(descriptor=_descriptor(raw), descriptor_hex=raw.hex())
            budget()
            row["status"] = "confirmed"
            self.state = "ready"
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            else:
                self.secondary = error
            self.resource_stop |= _resource(error)
            self.state = "stopped"
            raise
