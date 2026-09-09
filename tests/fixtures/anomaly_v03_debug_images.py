"""Preallocated image identity queries through borrowed debug-event handles.

No reopen, remote pointer read, content hash, handle close, or retry. Names are
private observations of a file handle, not proof of loaded bytes or fault cause.
"""

import ctypes as C
import json

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_evidence import _resource
from tests.fixtures.anomaly_v03_debug_transport import need


class DebugImages:
    LIMIT = 16
    NAME_UNITS = 1024
    JSON_LIMIT = 24 * 1024

    def __init__(self):
        self.names = tuple(C.create_unicode_buffer(self.NAME_UNITS) for _ in range(self.LIMIT))
        self.ids = tuple((w._FileId(), w._FileId()) for _ in range(self.LIMIT))
        self.pointers = tuple(tuple(C.pointer(value) for value in pair) for pair in self.ids)
        self.rows = [None] * self.LIMIT
        self.count = self.json_bytes = 0
        self.state = "ready"
        self.resource_stop = False
        self.primary = None
        self.secondary = None

    def __repr__(self):
        return "DebugImages(<private handle names and identities>)"

    def capture(self, transport, budget):
        try:
            need(self.state == "ready" and not self.resource_stop, "images_stopped")
            transport._thread()
            need(transport.state == "pending" and not transport.resource_stop
                 and not transport.wait_inflight and not transport.continue_inflight, "images_transport")
            index = transport.pending
            need(type(index) is int and 0 <= index < transport.count, "images_pending")
            raw = transport.buffers[index]
            if raw.kind not in (3, 6):
                return
            need(not transport.file_closed[index] and transport.file_close_state[index] == "not_started",
                 "images_file_closed")
            need(not any(row is not None and row["event_slot"] == index for row in self.rows), "images_retry")
            need(self.count < self.LIMIT, "images_capacity")
            slot = self.count
            self.count += 1
            row = {"event_slot": index, "status": "preparing"}
            self.rows[slot] = row
            info = raw.info.create_process if raw.kind == 3 else raw.info.load_dll
            handle = info.file
            if handle is None:
                row["status"] = "no_file_handle"
                return
            need(handle != C.c_void_p(-1).value, "images_handle")
            self.state = "querying"
            first, second = self.ids[slot]
            budget()
            row["status"] = "identity_uncertain"
            if not transport.kernel.GetFileInformationByHandleEx(handle, 18, self.pointers[slot][0], C.sizeof(first)):
                raise w._Failure("images_identity", C.get_last_error())
            need(any(first.identifier), "images_identity_empty")
            row.update(volume=first.volume, file_id=bytes(first.identifier).hex(), status="identity_confirmed")
            budget()
            row["status"] = "name_uncertain"
            # Normalized NT path avoids drive-letter lookup/fallback. Never use
            # the target's optional image_name pointer or open the returned path.
            length = transport.kernel.GetFinalPathNameByHandleW(handle, self.names[slot], self.NAME_UNITS, 2)
            if length == 0:
                raise w._Failure("images_name", C.get_last_error())
            need(type(length) is int and 0 < length < self.NAME_UNITS, "images_name_capacity")
            name = self.names[slot].value
            need(len(name.encode("utf-16-le", errors="strict")) // 2 == length, "images_name_length")
            row["status"] = "identity_recheck_uncertain"
            budget()
            if not transport.kernel.GetFileInformationByHandleEx(handle, 18, self.pointers[slot][1], C.sizeof(second)):
                raise w._Failure("images_identity_recheck", C.get_last_error())
            need(first.volume == second.volume and bytes(first.identifier) == bytes(second.identifier),
                 "images_identity_changed")
            candidate = dict(row, name=name, status="confirmed")
            candidate_rows = list(self.rows)
            candidate_rows[slot] = candidate
            size = len(json.dumps({"state": "querying", "rows": candidate_rows},
                                  ensure_ascii=True, separators=(",", ":")).encode("ascii"))
            # Include the envelope, separators and null slots. Reserve 256
            # bytes for each future partial row (bounded uint64/128-bit ID,
            # event slot and fixed status, with no name). A later query can
            # then fail without making the retained metadata exceed the cap.
            need(size + (self.LIMIT - slot - 1) * 256 <= self.JSON_LIMIT, "images_metadata_capacity")
            self.json_bytes = size
            self.rows[slot] = candidate
            budget()
            self.state = "ready"
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            else:
                self.secondary = error
            self.resource_stop |= _resource(error) or transport.resource_stop
            transport.resource_stop |= self.resource_stop
            self.state = "stopped"
            raise
