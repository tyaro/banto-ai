"""B2 adapter prototype with injected backend; never loads or calls a DLL itself.

This module belongs to tests/fixtures. It encodes two fixed Win64 requests and
records a single attempt. A real backend, fixture ownership, DACL/access checks,
source/runtime/token acceptance, and a native entrypoint are NOT implemented.
"""
from dataclasses import dataclass
import re
import struct
import sys

from . import anomaly_v03_publication_model as model

FILE_RENAME_INFO = 3
_TARGETS = {"rename_payload": ("stage", "payload", True),
            "commit_marker": ("marker-pending.json", ".complete", False)}
_MAX_HANDLE = (1 << 64) - 1
_RESOURCE_WINERRORS = frozenset((8, 14, 39, 112, 1450, 1451, 1452, 1453, 1454, 1455, 1816))


class AdapterError(ValueError):
    def __init__(self, reason, winerror=0):
        self.reason, self.winerror = reason, winerror
        super().__init__("b2_rename_adapter_failed")


class BudgetStop(MemoryError):
    """Backend resource-budget stop; never treated as an ordinary API denial."""


def _need(condition, reason="invalid_binding"):
    if not condition:
        raise AdapterError(reason)


def _handle(value):
    return type(value) is int and 0 < value < _MAX_HANDLE - 15


@dataclass(frozen=True)
class ObjectPin:
    handle: int
    volume: int
    file_id: bytes
    directory: bool
    content_sha256: str | None = None


def _pin(pin):
    _need(type(pin) is ObjectPin and _handle(pin.handle)
          and type(pin.volume) is int and 0 < pin.volume < 1 << 64
          and type(pin.file_id) is bytes and len(pin.file_id) == 16 and any(pin.file_id)
          and type(pin.directory) is bool)
    if pin.directory:
        _need(pin.content_sha256 is None)
    else:
        _need(type(pin.content_sha256) is str and re.fullmatch("[a-f0-9]{64}", pin.content_sha256) is not None)


def rename_request(parent_handle, step):
    """Fixed relative destination under a held parent, not CWD or a path input.

    Win64 FILE_RENAME_INFO: flags/BOOLEAN at 0, RootDirectory at 8,
    DWORD filename byte length at 16, UTF-16LE name at 20. Include one
    optional NUL beyond the counted name; no replace/POSIX/ignore flags.
    """
    _need(_handle(parent_handle) and type(step) is str and step in _TARGETS)
    name = _TARGETS[step][1].encode("utf-16-le")
    return struct.pack("<I4xQI", 0, parent_handle, len(name)) + name + b"\0\0"


def _resource(error):
    """Bounded pure inspection; exceeding the graph budget stops as resource."""
    if isinstance(error, MemoryError):
        return True
    try:
        pending, seen = [error], set()
        while pending:
            current = pending.pop()
            if current is None or id(current) in seen:
                continue
            if len(seen) >= 64:
                return True
            seen.add(id(current))
            if isinstance(current, MemoryError):
                return True
            winerror = getattr(current, "winerror", None)
            if isinstance(current, (AdapterError, OSError)) and type(winerror) is int and winerror in _RESOURCE_WINERRORS:
                return True
            # B1's already-loaded low-level helpers expose a fixed .error field
            # instead of OSError.winerror. Do not load a DLL or import it here.
            core = sys.modules.get("banto_ai._anomaly_v03_windows")
            if core is not None and type(current) is core._Failure:
                if current.error in _RESOURCE_WINERRORS or core._resource_stop(current):
                    return True
            edges = (current.__cause__, current.__context__)
            if isinstance(current, BaseExceptionGroup):
                if len(current.exceptions) > 64:
                    return True
                edges += current.exceptions
            if len(pending) + len(edges) > 128:
                return True
            pending.extend(edges)
        return False
    except MemoryError:
        return True


class BoundRename:
    """Single-use operation borrowing pinned handles; it never closes them.

    Backend rechecks must raise on any mismatch and return None on success.
    set_file_information_by_handle returns the signed Win32 BOOL as an int;
    get_last_error is read immediately on zero. Backend exceptions propagate
    unchanged; the journal contains no exception text or physical path.
    """

    def __init__(self, backend, *, step, parent, source):
        _need(type(step) is str and step in _TARGETS)
        _pin(parent)
        _pin(source)
        _need(parent.directory and source.directory is _TARGETS[step][2]
              and parent.volume == source.volume
              and parent.file_id != source.file_id and parent.handle != source.handle)
        self._backend, self._step = backend, step
        self._parent, self._source = parent, source
        self._request = rename_request(parent.handle, step)
        self._used = False

    def run(self, journal):
        _need(type(journal) is model.PublicationJournal, "journal_type")
        if self._used:
            journal.stop()
            raise AdapterError("attempt_already_used")
        self._used = True
        try:
            journal.begin(self._step)
            if self._step == "commit_marker":
                _need(journal.snapshot()["marker_sha256"] == self._source.content_sha256, "marker_pin_mismatch")
            backend = self._backend
            _need(backend.recheck_parent(self._parent) is None, "parent_check_result")
            self._pending(journal)
            _need(backend.recheck_source(self._source, self._parent, _TARGETS[self._step][0]) is None, "source_check_result")
            self._pending(journal)
            result = backend.set_file_information_by_handle(self._source.handle, FILE_RENAME_INFO, self._request)
            if type(result) is int and result == 0:
                error = backend.get_last_error()
                _need(type(error) is int and 0 < error < 1 << 32, "native_error_unavailable")
                raise AdapterError("native_rename_failed", error)
            _need(type(result) is int and -(1 << 31) <= result < 1 << 31 and result != 0, "native_result_shape")
            # No post-commit readback/mutation. The caller owns teardown; later
            # consumer verification is a separate operation, never an API retry.
            journal.succeed(self._step)
        except BaseException as error:
            journal.stop(resource=_resource(error))
            raise

    def _pending(self, journal):
        # A swallowed/reentrant stop inside a backend check cannot authorize
        # the next check or mutation. Snapshot construction is pure and bounded.
        state = journal.snapshot()
        _need(state["model_status"] == "in_progress"
              and next(row["state"] for row in state["steps"] if row["step"] == self._step) == "pending",
              "journal_not_pending")
