"""A file sealing generation held through one synchronous continuation.

Engineering-only: no directory sealing or native rename. The continuation is
trusted, runs under the original root borrow, and cannot resume after a stop.
Existing closed writer slots remain historical; all new cells close on exit.
"""
import ctypes as C
from dataclasses import dataclass
import json

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_observed_evidence as bridge
from . import anomaly_v03_reader_reacquisition as reopen

FILE_SEAL_ACCESS = reopen.READER_ACCESS | 0x40000  # WRITE_DAC, no data writes.
MARKER_SEAL_ACCESS = FILE_SEAL_ACCESS | 0x10000  # DELETE acquired before sealing.


def access_for(plan):
    return MARKER_SEAL_ACCESS if plan.name == "marker-pending.json" else FILE_SEAL_ACCESS


@dataclass(frozen=True)
class SealedPins:
    parent: object
    observations: tuple
    marker_index: int


class SealedFiles(reopen.ReacquiredReaders):
    def __init__(self, backend, *, group, root_index, plans, user):
        super().__init__(backend, group=group, root_index=root_index, plans=plans, user=user)
        markers = [i for i, plan in enumerate(plans) if plan.name == "marker-pending.json"]
        owned._need(len(markers) == 1 and len(plans) >= 2, "seal_marker_plan")
        self._marker_index = markers[0]
        owned._need(plans[self._marker_index].previous.pin.content_sha256
                    == group.owner._journal.snapshot()["marker_sha256"], "seal_marker_binding")
        self._sealed = [None] * len(plans)
        self._seal_states = ["not_started"] * len(plans)
        self._held_access = [None] * len(plans)
        self._continuation = "not_started"
        self._operation = None

    def seal_and_use(self, operation):
        try:
            owned._need(not self._started and not self._done and callable(operation), "seal_attempt_reused")
            self._operation = operation
            super().acquire()
        except BaseException as error:
            self._record(error)
            raise

    def acquire(self):
        error = owned.OwnershipError("seal_requires_continuation")
        self._record(error)
        raise error

    def _expected_access(self, plan):
        return access_for(plan)

    def _after_verified(self):
        # Every new cell is live and validated before the first DACL mutation.
        for index, (lease, plan) in enumerate(zip(self._leases, self._plans)):
            self._guard()
            before = bridge.inspect_native(lease, expected=plan.raw, private_user=self._user, guard=self._guard)
            owned._need(before == self._observations[index], "seal_precondition_changed")
            self._seal_states[index] = "set_pending"
            result = self._backend.seal(lease.handle, guard=self._guard, reject=self._record)
            self._guard()
            owned._need(result is None, "seal_set_response")
            self._seal_states[index] = "readback_pending"
            after = bridge.inspect_native(lease, expected=plan.raw, private_user=self._user,
                                          guard=self._guard, security_mode="frozen")
            # Only the ACE list changes. Preserve owner/group/integrity/policy.
            old_sd, new_sd = json.loads(before.descriptor), json.loads(after.descriptor)
            old_sd.pop("aces")
            new_sd.pop("aces")
            owned._need(after.pin == before.pin and old_sd == new_sd, "seal_object_changed")
            access = self._backend.granted_access(lease.handle)
            self._guard()
            owned._need(type(access) is int and access == access_for(plan), "sealed_handle_access")
            self._held_access[index] = access
            self._sealed[index] = after
            self._seal_states[index] = "verified"
        self._guard()
        pins = SealedPins(self._group.owner._slots[self._root_index].pin, tuple(self._sealed), self._marker_index)
        self._continuation = "pending"
        result = self._operation(pins)
        self._guard()
        owned._need(result is None, "seal_continuation_response")
        self._continuation = "returned"

    def snapshot(self):
        result = super().snapshot()
        result["sealing"] = [{"name": plan.name, "state": self._seal_states[i],
                              "held_access_after_seal": self._held_access[i],
                              "observation": None if self._sealed[i] is None else {
                                  "volume": self._sealed[i].pin.volume,
                                  "file_id": self._sealed[i].pin.file_id.hex(),
                                  "content_sha256": self._sealed[i].pin.content_sha256,
                                  "descriptor": json.loads(self._sealed[i].descriptor)}}
                             for i, plan in enumerate(self._plans)]
        result["continuation"] = self._continuation
        return result


class WindowsSealBackend(reopen.WindowsReaderBackend):
    def open_reader(self, cell, root_pin, plan):
        source = self._source
        root = source._leases[len(source._root.parents)]
        owned._need(root.handle == root_pin.handle, "seal_root_binding")
        cell.handle = source._api.k.CreateFileW(str(source._root / plan.name), access_for(plan), 1,
                                                None, 3, 0x00200000, None)
        if cell.handle == C.c_void_p(-1).value:
            raise owned.OwnershipError("seal_open_failed", C.get_last_error())

    def seal(self, handle, *, guard, reject):
        source, descriptor, primary = self._source, None, None
        present, defaulted, acl = C.c_int32(), C.c_int32(), C.c_void_p()
        try:
            guard()
            descriptor = source._api.descriptor(source._win._dacl(source._user, "frozen", False)[0])
            guard()
            source._api.call(source._api.a.GetSecurityDescriptorDacl(
                descriptor, C.byref(present), C.byref(acl), C.byref(defaulted)), "seal_dacl")
            guard()
            owned._need(present.value and acl.value and not defaulted.value, "seal_null_or_default_dacl")
            error = source._api.a.SetSecurityInfo(handle, 1, 0x80000004, None, None, acl, None)
            # DWORD result is the error itself; never read GetLastError here.
            owned._need(type(error) is int and 0 <= error < 1 << 32, "seal_result_shape")
            if error:
                raise owned.OwnershipError("seal_set_failed", error)
            guard()
        except BaseException as error:
            primary = error
            raise
        finally:
            if descriptor is not None:
                try:
                    owned._need(not source._api.k.LocalFree(descriptor), "seal_descriptor_free")
                except BaseException as error:
                    reject(error)
                    if primary is None:
                        raise
