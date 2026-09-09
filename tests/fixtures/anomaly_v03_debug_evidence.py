"""Bounded private evidence capture and single write to a borrowed handle.

The file owner creates and validates a private empty synchronous file before
launch. Capture/write uses only existing local buffers and that borrowed handle.
There are no remote reads, launch, or import-time native calls. The driver owns
the prepared file and this buffer separately and closes the file after writing.
"""

import ctypes as C
import json
import struct
import threading

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_transport import DebugEvent, DebugEventTransport, need


def _resource(error):
    return (w._resource_stop(error) or type(error) is w._Failure
            and error.error in (8, 14, 39, 112, 1450, 1455, 1816))


class DebugEvidence:
    MAGIC = b"B1DBG001"
    HEADER = struct.Struct("<8sIIII")
    METADATA_LIMIT = 64 * 1024
    SLOTS = DebugEventTransport.LIMIT
    EVENT_SIZE = 176
    REGION_SIZE = SLOTS * EVENT_SIZE
    CAPACITY = HEADER.size + METADATA_LIMIT + 2 * REGION_SIZE

    def __init__(self):
        need(C.sizeof(DebugEvent) == self.EVENT_SIZE and self.CAPACITY <= 1024 * 1024,
             "evidence_abi")
        self.buffer = C.create_string_buffer(self.CAPACITY)
        self.pointer = C.cast(self.buffer, C.c_void_p)
        self.written = w.D()
        self.written_pointer = C.pointer(self.written)
        self.size = 0
        self.capture_state = self.write_state = self.flush_state = "not_started"
        self.resource_stop = False
        self.primary = None
        self.secondary = None
        self.owner = None
        self.creator_thread = threading.get_ident()

    def __repr__(self):
        return "DebugEvidence(<private local buffers>)"

    def _failure(self, error):
        if self.primary is None:
            self.primary = error
        else:
            self.secondary = error
        self.resource_stop |= _resource(error)

    @staticmethod
    def _source(source):
        need(type(source) is DebugEventTransport, "evidence_transport")
        need(type(source.count) is int and 0 <= source.count <= DebugEvidence.SLOTS,
             "evidence_count")
        need(source.pending is None or type(source.pending) is int
             and 0 <= source.pending < DebugEvidence.SLOTS, "evidence_pending")
        need(source.state == "stopped", "evidence_running")
        need(len(source.buffers) == DebugEvidence.SLOTS
             and all(type(raw) is DebugEvent for raw in source.buffers), "evidence_buffers")
        return {"confirmed_buffers": source.count, "pending": source.pending,
                "wait_inflight": source.wait_inflight, "continue_inflight": source.continue_inflight,
                "file_close_state": source.file_close_state, "file_closed": source.file_closed}

    def capture(self, driver):
        need(self.capture_state == "not_started", "evidence_capture_retry")
        self.owner = driver  # Keep original evidence even if serialization fails.
        self.capture_state = "capturing"
        try:
            need(threading.get_ident() == self.creator_thread, "evidence_thread")
            need(driver.started and driver.transport is not None and driver.stop is not None,
                 "evidence_driver")
            if (driver.resource_stop or driver.preflight.resource_stop or driver.transport.resource_stop
                    or driver.stop.resource_stop or driver.stop.drain.resource_stop):
                self.resource_stop = True
                self.capture_state = "resource_skipped"
                return
            sources = (driver.transport, driver.stop.drain)
            metadata = {"version": 1, "byte_order": "little", "pointer_bits": 64,
                        "slots_per_region": self.SLOTS, "event_size": self.EVENT_SIZE,
                        "raw_scope": "all_preallocated_slots_including_unconfirmed",
                        "result_scope": "before_evidence_write_flush_and_file_close",
                        "normal": self._source(sources[0]), "drain": self._source(sources[1]),
                        "driver": dict(driver.result), "stop": dict(driver.stop.result),
                        "observation": dict(driver.observer.result),
                        "runtime": driver.preflight.runtime, "sources": driver.preflight.rows,
                        "nonce": driver.nonce,
                        "images": ({"state": driver.images.state, "rows": driver.images.rows}
                                   if getattr(driver, "images", None) is not None else None),
                        "security": ({"state": driver.security.state, "rows": driver.security.rows}
                                     if getattr(driver, "security", None) is not None else None),
                        "primary_reason": getattr(driver.primary, "reason", None)}
            offset = self.HEADER.size
            # Bound accumulated metadata before copying; never serialize raw
            # exception text, traceback, object repr, or target pointer contents.
            for part in json.JSONEncoder(ensure_ascii=True, allow_nan=False,
                                         separators=(",", ":")).iterencode(metadata):
                need(len(part) <= self.METADATA_LIMIT, "evidence_metadata_size")
                raw = part.encode("ascii")
                need(offset + len(raw) <= self.HEADER.size + self.METADATA_LIMIT,
                     "evidence_metadata_size")
                C.memmove(self.pointer.value + offset, raw, len(raw))
                offset += len(raw)
            metadata_size = offset - self.HEADER.size
            for source in sources:
                for raw in source.buffers:
                    C.memmove(self.pointer.value + offset, C.addressof(raw), self.EVENT_SIZE)
                    offset += self.EVENT_SIZE
            header = self.HEADER.pack(self.MAGIC, metadata_size, self.EVENT_SIZE,
                                      self.SLOTS, len(sources))
            C.memmove(self.pointer, header, len(header))
            self.size = offset
            self.capture_state = "captured"
        except BaseException as error:
            self.capture_state = "failed"
            self._failure(error)

    def write(self, kernel, handle):
        """One synchronous write/flush; borrowed handle is never closed here.

        'flushed' means API confirmations, not readback or durable verification.
        Failed or uncertain IO cannot be retried with this owner.
        """
        need(self.write_state == "not_started", "evidence_write_retry")
        self.write_state = "preparing"
        try:
            need(threading.get_ident() == self.creator_thread, "evidence_thread")
            need(self.capture_state == "captured" and not self.resource_stop,
                 "evidence_not_captured")
            if (self.owner.resource_stop or self.owner.preflight.resource_stop
                      or self.owner.transport.resource_stop or self.owner.stop.resource_stop
                      or self.owner.stop.drain.resource_stop):
                self.resource_stop = True
                need(False, "evidence_resource_latched")
            need(type(handle) is int and 0 < handle < C.c_void_p(-1).value, "evidence_handle")
            self.write_state = "uncertain"
            if not kernel.WriteFile(handle, self.pointer, self.size, self.written_pointer, None):
                self.write_state = "failed"
                raise w._Failure("evidence_write", C.get_last_error())
            need(self.written.value == self.size, "evidence_partial_write")
            self.write_state = "confirmed"
            self.flush_state = "uncertain"
            if not kernel.FlushFileBuffers(handle):
                self.flush_state = "failed"
                raise w._Failure("evidence_flush", C.get_last_error())
            self.flush_state = "confirmed"
        except BaseException as error:
            if self.write_state == "preparing":
                self.write_state = "rejected"
            self._failure(error)


class EvidenceFile:
    """Prelaunch private file owner; no path operations after preparation.

    An uncertain CreateFile/CloseHandle result remains unresolved, never retried.
    A retained file is not immutable against its owner or administrators.
    """
    NAME = "control/startup-evidence.bin"

    def __init__(self, api):
        self.api = api
        self.handle = None
        self.bound = None
        self.open_state = self.close_state = "not_started"
        self.primary = None
        self.resource_stop = False
        self.creator_thread = threading.get_ident()

    def __repr__(self):
        return "EvidenceFile(<private handle and identity>)"

    def prepare(self, fixture):
        need(self.open_state == "not_started" and self.close_state == "not_started",
             "evidence_file_retry")
        self.open_state = "preparing"
        try:
            need(threading.get_ident() == self.creator_thread, "evidence_thread")
            fixture.file(self.NAME, b"", "private")
            path = fixture.path(self.NAME)
            # Validation borrows the preowned handle; never lets _Bound close
            # it or hides an open result behind a helper return boundary.
            self.bound = w._Bound.__new__(w._Bound)
            self.bound.api, self.bound.path, self.bound.directory = self.api, path, False
            self.bound.handle = None
            self.open_state = "uncertain"
            # GENERIC_WRITE is required by FlushFileBuffers; also borrow read
            # data/attributes and READ_CONTROL for prelaunch validation.
            self.handle = self.api.k.CreateFileW(str(path), 0x40020081, 1, None, 3, 0x00200000, None)
            if self.handle == C.c_void_p(-1).value:
                self.open_state = "failed"
                self.handle = None
                raise w._Failure("evidence_file_open", C.get_last_error())
            self.open_state = "opened"
            need(type(self.handle) is int and self.handle > 0, "evidence_file_handle")
            self.bound.handle = self.handle
            self.bound.identity = self.bound.observe()
            need(self.bound.identity == fixture.ledger[self.NAME]["identity"], "evidence_file_identity")
            self.bound.check()
            self.bound.streams()
            w._verify_sd(self.api.security(self.handle), fixture.user, "private", False)
            size = C.c_int64()
            self.api.call(self.api.k.GetFileSizeEx(self.handle, C.byref(size)), "evidence_file_size")
            need(size.value == 0, "evidence_file_nonempty")
            self.open_state = "prepared"
        except BaseException as error:
            self.primary = error
            self.resource_stop |= _resource(error)
            raise

    def close(self):
        need(self.close_state == "not_started", "evidence_file_close_retry")
        self.close_state = "uncertain"
        try:
            need(threading.get_ident() == self.creator_thread, "evidence_thread")
            if self.open_state in ("opened", "prepared") and self.handle is not None:
                if not self.api.k.CloseHandle(self.handle):
                    self.close_state = "failed"
                    raise w._Failure("evidence_file_close", C.get_last_error())
                self.handle = None
                self.bound.handle = None
            elif self.open_state == "uncertain":
                need(False, "evidence_file_open_uncertain")
            self.close_state = "closed"
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            self.resource_stop |= _resource(error)
            raise

    def resolved(self):
        return self.close_state == "closed" and self.handle is None and self.open_state != "uncertain"
