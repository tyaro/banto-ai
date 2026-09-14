"""Bounded reader generation after confirmed writer release; no seal or rename."""
import ctypes as C
from dataclasses import dataclass
import hashlib

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_observed_evidence as bridge
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_publication_model as model
from .anomaly_v03_tracked_open import TrackedOpen

READER_ACCESS = 0x120081  # READ_DATA | READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE
WRITER_ACCESS = 0x12019F  # Mapped GENERIC_READ | GENERIC_WRITE, recorded before close.


@dataclass(frozen=True)
class ReadPlan:
    writer_index: int
    name: str
    raw: bytes
    previous: prep.Observation


class ReacquiredReaders:
    """Own a separate bounded generation; original owner keeps root and history.

    Old closed slots never become owned again. New cells are reserved before
    any open, remain private to this holder and close inside the root borrow
    before acquire() returns or raises. No live reader escapes that borrow.
    The caller retains this holder before acquire(), including on reply loss.
    """
    def __init__(self, backend, *, group, root_index, plans, user):
        owned._need(type(group) is bridge.AcquiredOwner and group.active, "reader_parent_owner")
        owner = group.owner
        owner._usable()
        owner._indices((root_index,))
        owned._need(owner._slots[root_index].pin.directory and type(plans) is tuple
                    and 0 < len(plans) <= model.MAX_FILES and type(user) is str and bool(user), "reader_plan")
        indices, names = set(), set()
        for plan in plans:
            owned._need(type(plan) is ReadPlan and type(plan.writer_index) is int
                        and 0 <= plan.writer_index < len(owner._slots)
                        and plan.writer_index not in indices and type(plan.name) is str
                        and "/" not in plan.name and "\\" not in plan.name and plan.name.casefold() not in names,
                        "reader_plan")
            slot = owner._slots[plan.writer_index]
            owned._need(slot.parent == root_index and not slot.pin.directory
                        and type(plan.previous) is prep.Observation and plan.previous.pin == slot.pin
                        and type(plan.raw) is bytes and hashlib.sha256(plan.raw).hexdigest() == slot.pin.content_sha256,
                        "reader_original_binding")
            indices.add(plan.writer_index)
            names.add(plan.name.casefold())
        model.marker_bytes("0" * 40, {plan.name: plan.raw for plan in plans})  # Path/byte budgets.
        self._backend, self._group, self._root_index, self._plans, self._user = backend, group, root_index, plans, user
        self._leases = tuple(TrackedOpen(backend) for _ in plans)
        self._observations = [None] * len(plans)
        self._access = [None] * len(plans)
        self._states = ["not_started"] * len(plans)
        self._started = self._done = self._busy = self._resource = False
        self._error = None

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)
        self._group.reject(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(not self._done, "readers_finished")
        bridge._observation_ready(self._group._leases[self._root_index])

    def _expected_access(self, plan):
        return READER_ACCESS

    def _after_verified(self):
        """Trusted subclass hook; runs inside the parent borrow before close."""

    def acquire(self):
        entered = False
        try:
            owned._need(not self._started and not self._done and not self._busy, "reader_attempt_reused")
            self._started = self._busy = entered = True
            def open_all(pins):
                try:
                    self._guard()
                    owner = self._group.owner
                    for plan in self._plans:
                        old = self._group._leases[plan.writer_index]
                        owned._need(owner._states[plan.writer_index] == "closed" and old.close_state == "closed"
                                    and old._error is None, "writer_close_not_confirmed")
                    for index, (lease, plan) in enumerate(zip(self._leases, self._plans)):
                        self._guard()
                        self._states[index] = "open_pending"
                        def inspect(handle):
                            self._guard()
                            view = self._backend.view(handle, plan)
                            self._guard()
                            return view
                        lease.acquire(lambda cell: self._backend.open_reader(cell, pins[0], plan), inspect)
                        self._guard()
                        self._states[index] = "access_pending"
                        access = self._backend.granted_access(lease.handle)
                        self._guard()
                        self._access[index] = access
                        owned._need(type(access) is int and access == self._expected_access(plan), "reader_granted_access")
                        self._states[index] = "verify_pending"
                        observation = bridge.inspect_native(lease, expected=plan.raw, private_user=self._user, guard=self._guard)
                        old, new = plan.previous.pin, observation.pin
                        owned._need((new.volume, new.file_id, new.directory, new.content_sha256)
                                    == (old.volume, old.file_id, old.directory, old.content_sha256)
                                    and observation.descriptor == plan.previous.descriptor, "reopened_object_changed")
                        self._guard()
                        self._observations[index] = observation
                        self._states[index] = "verified"
                    self._guard()
                    self._after_verified()
                    self._guard()
                except BaseException as error:
                    self._record(error)
                    raise
                finally:
                    self._close_all()
                if self._error is not None:
                    raise self._error
            self._group.owner.borrowed((self._root_index,), open_all)
        except BaseException as error:
            self._record(error)
            if entered:
                self._busy = False
                self.finish(primary=error)
            raise
        finally:
            if entered:
                self._busy = False

    def finish(self, *, primary=None):
        if self._busy:
            error = owned.OwnershipError("reader_operation_active")
            self._record(error)
            raise error
        if primary is not None:
            self._error = primary
            self._record(primary)
        self._close_all()
        if self._error is not None:
            raise self._error

    def _close_all(self):
        if not self._done:
            self._done = True
            for lease in reversed(self._leases):
                try:
                    lease.close()
                except BaseException as error:
                    self._record(error)

    def snapshot(self):
        return {"started": self._started, "finished": self._done, "resource_stop": self._resource,
                "stopped": self._error is not None,
                "readers": [{"writer_slot": plan.writer_index, "name": plan.name, "state": self._states[index],
                             "granted_access": self._access[index], "close": self._leases[index].snapshot(),
                             "identity_and_bytes_matched": self._observations[index] is not None}
                            for index, plan in enumerate(self._plans)],
                "retry_permitted": False, "cleanup_permitted": False, "native_publication_performed": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}


class _ObjectBasic(C.Structure):
    _fields_ = [("attributes", C.c_uint32), ("access", C.c_uint32),
                ("handles", C.c_uint32), ("pointers", C.c_uint32), ("reserved", C.c_uint32 * 10)]


class WindowsReaderBackend:
    """Existing held private root, fixed access/share and no new writer rights."""
    def __init__(self, source):
        self._source = source
        api = source._api
        self._query = api.n.NtQueryObject
        self._query.restype = C.c_int32
        self._query.argtypes = [C.c_void_p, C.c_uint32, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint32)]
        self._map_status = api.n.RtlNtStatusToDosError
        self._map_status.restype, self._map_status.argtypes = C.c_uint32, [C.c_int32]
        owned._need(C.sizeof(_ObjectBasic) == 56, "object_basic_abi")

    def open_reader(self, cell, root_pin, plan):
        source = self._source
        root = source._leases[len(source._root.parents)]
        owned._need(root.handle == root_pin.handle, "reader_root_binding")
        cell.handle = source._api.k.CreateFileW(str(source._root / plan.name), READER_ACCESS, 1,
                                                None, 3, 0x00200000, None)
        if cell.handle == C.c_void_p(-1).value:
            raise owned.OwnershipError("reader_open_failed", C.get_last_error())

    def view(self, handle, plan):
        return self._source._file_view(handle, self._source._root / plan.name, False)

    def granted_access(self, handle):
        info, length = _ObjectBasic(), C.c_uint32()
        status = self._query(handle, 0, C.byref(info), C.sizeof(info), C.byref(length))
        if status != 0:
            error = owned.OwnershipError("reader_access_query", self._map_status(status))
            error.ntstatus = status & 0xffffffff
            raise error
        owned._need(length.value == C.sizeof(info), "object_basic_size")
        return int(info.access)

    def close_handle(self, handle):
        return self._source._backend.close_handle(handle)

    def get_last_error(self):
        return self._source._backend.get_last_error()
