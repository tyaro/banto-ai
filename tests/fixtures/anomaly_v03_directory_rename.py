"""Held root/stage directory sealing and a single relative rename experiment.

Local operation states only: never fabricate preceding publication phases.
Uses the existing fixed FILE_RENAME_INFO encoder, not a campaign entrypoint.
"""
import ctypes as C
import json

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_observed_evidence as bridge
from . import anomaly_v03_rename_adapter as rename
from . import anomaly_v03_sealed_files as seal
from .anomaly_v03_private_sink import WindowsPrivateSink

ROOT_ACCESS = 0x1600A7  # LIST/ADD_FILE/ADD_SUBDIR/TRAVERSE/ATTR/RC/WDAC/SYNC.
STAGE_ACCESS = 0x1700A1  # LIST/TRAVERSE/ATTR/RC/WDAC/DELETE/SYNC.


class DirectoryRename:
    """Caller retains group and child generation; this borrows, never closes."""
    def __init__(self, backend, *, group, previous, files, parent_policy="frozen"):
        owned._need(type(parent_policy) is str and parent_policy in ("private", "frozen"), "directory_parent_policy")
        owned._need(type(group) is bridge.AcquiredOwner and group.active, "directory_owner")
        owner = group.owner
        owner._usable()
        owned._need(type(previous) is tuple and len(previous) == 2 and len(owner._slots) >= 3
                    and all(previous[i].pin == owner._slots[i].pin and previous[i].pin.directory for i in (0, 1))
                    and owner._slots[0].parent is None and owner._slots[1].parent == 0,
                    "directory_bindings")
        owned._need(type(files) is seal.SealedFiles and files._group is group
                    and files._root_index == 1 and files._marker_index is None
                    and {p.writer_index for p in files._plans} == set(range(2, len(owner._slots)))
                    and all(slot.parent == 1 and not slot.pin.directory for slot in owner._slots[2:]),
                    "directory_child_inventory")
        self._backend, self._group, self._previous, self._files = backend, group, previous, files
        self._parent_policy = parent_policy
        self._request = rename.rename_request(previous[0].pin.handle, "rename_payload")
        self._states = ["not_started", "not_started"]
        self._sealed = [None, None]
        self._rights_before, self._rights_after = [None, None], [None, None]
        self._used = self._resource = False
        self._error = None
        self._evidence = self._rename = "not_started"

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)
        self._group.reject(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        for lease in self._group._leases[:2]:
            bridge._observation_ready(lease)
        # Include stops latched by the completed child generation, even when
        # a callback swallowed an exception or finalization returned earlier.
        if self._files._error is not None:
            raise self._files._error
        owned._need(self._files._done and not self._files._busy
                    and self._files._continuation == "returned"
                    and all(state == "verified" for state in self._files._seal_states)
                    and all(cell.close_state == "closed" and cell._error is None for cell in self._files._leases),
                    "directory_children_not_closed")
        for index in range(2, len(self._group._leases)):
            cell = self._group._leases[index]
            owned._need(self._group.owner._states[index] == "closed"
                        and cell.close_state == "closed" and cell._error is None, "directory_writer_not_closed")

    def _observe(self, index, mode):
        return bridge.inspect_native(self._group._leases[index], private_user=self._files._user,
                                     guard=self._guard, security_mode=mode)

    def run(self, persist):
        try:
            owned._need(not self._used and callable(persist), "directory_attempt_reused")
            self._used = True
            def operation(pins):
                self._guard()
                for index, access in enumerate((ROOT_ACCESS, STAGE_ACCESS)):
                    owned._need(self._observe(index, "private") == self._previous[index], "directory_precondition_changed")
                    granted = self._backend.granted_access(pins[index].handle)
                    self._guard()
                    owned._need(type(granted) is int and granted == access, "directory_granted_access")
                    self._rights_before[index] = granted
                # Comparative private-parent mode leaves only the parent ACL
                # unchanged. Both arms still seal the stage and all children.
                for index in (1, 0):
                    before = self._observe(index, "private")
                    owned._need(before == self._previous[index], "directory_precondition_changed")
                    mode = self._parent_policy if index == 0 else "frozen"
                    if mode == "frozen":
                        self._states[index] = "set_pending"
                        result = self._backend.seal_directory(pins[index].handle, guard=self._guard, reject=self._record)
                        self._guard()
                        owned._need(result is None, "directory_seal_response")
                    self._states[index] = "readback_pending"
                    after = self._observe(index, mode)
                    old_sd, new_sd = json.loads(before.descriptor), json.loads(after.descriptor)
                    old_sd.pop("aces")
                    new_sd.pop("aces")
                    owned._need(before.pin == after.pin and old_sd == new_sd, "sealed_directory_changed")
                    if mode == "private":
                        owned._need(after == before, "private_parent_changed")
                    granted = self._backend.granted_access(pins[index].handle)
                    self._guard()
                    owned._need(type(granted) is int and granted == self._rights_before[index], "directory_retained_access")
                    self._rights_after[index], self._sealed[index] = granted, after
                    self._states[index] = "verified" if mode == "frozen" else "private_verified"
                self._evidence = "save_pending"
                owned._need(persist(tuple(self._sealed), tuple(self._files._sealed)) is None, "directory_evidence_response")
                self._guard()
                self._evidence = "saved"
                for index in (0, 1):
                    mode = self._parent_policy if index == 0 else "frozen"
                    owned._need(self._observe(index, mode) == self._sealed[index], "directory_prerename_changed")
                self._guard()
                self._rename = "pending"
                result = self._backend.set_file_information_by_handle(pins[1].handle, rename.FILE_RENAME_INFO, self._request)
                if type(result) is int and result == 0:
                    error = self._backend.get_last_error()
                    owned._need(type(error) is int and 0 < error < 1 << 32, "directory_error_unavailable")
                    raise owned.OwnershipError("directory_rename_failed", error)
                owned._need(type(result) is int and -(1 << 31) <= result < 1 << 31 and result != 0,
                            "directory_rename_response")
                # A confirmed API response remains confirmed if a later stop
                # is discovered. No name-based check/readback after this call.
                self._rename = "confirmed"
                self._guard()
            self._group.owner.borrowed((0, 1), operation)
        except BaseException as error:
            self._record(error)
            raise

    def snapshot(self):
        return {"used": self._used, "stopped": self._error is not None, "resource_stop": self._resource,
                "parent_policy": self._parent_policy,
                "directory_states": self._states[:], "rights_before": self._rights_before[:],
                "rights_after": self._rights_after[:], "evidence": self._evidence, "rename": self._rename,
                "retry_permitted": False, "cleanup_permitted": False, "native_publication_performed": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}


class WindowsDirectoryFixture(WindowsPrivateSink):
    def _open_access(self, path, *, directory, create):
        if directory and not create and path in (self._root, self._root / "stage"):
            return ROOT_ACCESS if path == self._root else STAGE_ACCESS
        return super()._open_access(path, directory=directory, create=create)


class WindowsDirectoryBackend(seal.WindowsSealBackend):
    def set_file_information_by_handle(self, handle, info_class, raw):
        # Only the fixed wire layout prepared by DirectoryRename is passed.
        buffer = C.create_string_buffer(raw, len(raw))
        return self._source._api.k.SetFileInformationByHandle(handle, info_class, buffer, len(raw))


class WindowsStageFileBackend(seal.WindowsSealBackend):
    def open_reader(self, cell, root_pin, plan):
        source = self._source
        stage = source._leases[len(source._root.parents) + 1]
        owned._need(stage.handle == root_pin.handle and plan.name == "facts.json", "stage_file_binding")
        cell.handle = source._api.k.CreateFileW(str(source._root / "stage" / plan.name),
                                               seal.FILE_SEAL_ACCESS, 1, None, 3, 0x00200000, None)
        if cell.handle == C.c_void_p(-1).value:
            raise owned.OwnershipError("stage_file_open", C.get_last_error())

    def view(self, handle, plan):
        return self._source._file_view(handle, self._source._root / "stage" / plan.name, False)


class _IoStatus(C.Structure):
    _fields_ = [("status", C.c_int32), ("padding", C.c_uint32), ("information", C.c_uint64)]


class WindowsNtDirectoryBackend(seal.WindowsSealBackend):
    """Explicit NT route for relative names; never fall back after a failure.

    Source is a synchronous CreateFile handle (no OVERLAPPED). Buffers remain
    in this retained backend through worker teardown. An unexpected pending
    result is a resource stop requiring immediate worker exit after cleanup.
    """
    def __init__(self, source):
        super().__init__(source)
        owned._need(C.sizeof(C.c_void_p) == 8 and C.sizeof(_IoStatus) == 16
                    and _IoStatus.information.offset == 8, "rename_iosb_abi")
        self._set = source._api.n.NtSetInformationFile
        self._set.restype = C.c_int32
        self._set.argtypes = [C.c_void_p, C.POINTER(_IoStatus), C.c_void_p, C.c_uint32, C.c_uint32]
        self._attempted = self.pending = self.completion_unknown = False
        self.ntstatus, self._last_error, self._buffer, self._io = None, 0, None, None

    def _matches_request(self, raw):
        return (type(raw) is bytes and len(raw) == 36
                and raw == rename.rename_request(int.from_bytes(raw[8:16], "little"), "rename_payload"))

    def set_file_information_by_handle(self, handle, info_class, raw):
        owned._need(not self._attempted and info_class == rename.FILE_RENAME_INFO and self._matches_request(raw),
                    "nt_directory_request")
        self._attempted = True
        # Same field offsets as Win64 FILE_RENAME_INFO, with trailing padding
        # to cover sizeof(FILE_RENAME_INFORMATION) + counted UTF-16 leaf bytes.
        self._buffer = C.create_string_buffer(raw + b"\0" * 4, 40)
        self._io = _IoStatus(-1, 0, 0)
        # An interrupted native return is also unconfirmed, even if status
        # could not be inspected or pending=True could not yet be assigned.
        self.completion_unknown = True
        status = self._set(handle, C.byref(self._io), self._buffer, 40, 10)
        owned._need(type(status) is int and -(1 << 31) <= status < 1 << 31, "nt_directory_status")
        self.ntstatus = status & 0xffffffff
        if status == 0x103:
            self.pending = True
            raise rename.BudgetStop("unexpected_async_rename")
        self.completion_unknown = False  # Only a validated non-pending return.
        if status == 0:
            return 1  # For non-pending calls the returned NTSTATUS is authoritative.
        self._last_error = self._map_status(status)
        owned._need(type(self._last_error) is int and 0 < self._last_error < 1 << 32, "nt_directory_error_mapping")
        return 0

    def get_last_error(self):
        return self._last_error  # Already mapped NTSTATUS, not thread last-error.

    def native_snapshot(self):
        return {"api": "NtSetInformationFile", "file_information_class": 10, "buffer_bytes": 40,
                "ntstatus": self.ntstatus, "pending": self.pending,
                "completion_unknown": self.completion_unknown,
                "io_status": None if self._io is None else self._io.status & 0xffffffff}
