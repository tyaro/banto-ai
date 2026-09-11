"""Bounded ownership/teardown prototype; injected CloseHandle backend only.

No handle acquisition, native DLL, filesystem cleanup, or acceptance entrypoint.
Ownership transfers only when construction returns successfully. Until then the
caller owns every supplied pin. Callers must not close/use the pins afterwards,
except through synchronous borrowed operations before finish starts.
"""
from dataclasses import dataclass

from . import anomaly_v03_publication_model as model
from . import anomaly_v03_rename_adapter as rename

MAX_HANDLES = 32


class OwnershipError(rename.AdapterError):
    def __init__(self, reason, winerror=0):
        self.reason, self.winerror = reason, winerror
        ValueError.__init__(self, "b2_handle_ownership_failed")


def _need(condition, reason="invalid_owned_handles"):
    if not condition:
        raise OwnershipError(reason)


def _resource(error):
    # Classification must not interrupt remaining handle releases. If the
    # classifier itself cannot complete, conservatively record resource stop.
    try:
        return rename._resource(error)
    except BaseException:
        return True


@dataclass(frozen=True)
class OwnedSlot:
    pin: rename.ObjectPin
    parent: int | None


class HandleOwner:
    """Close each owned handle at most once, children before ancestors.

    This object is single-threaded trusted state, not a sandbox. Unknown closes
    retain identity for evidence only: the numeric handle may already be reused.
    There is deliberately no retry, destructor, reopen, or path-cleanup API.
    """

    def __init__(self, backend, *, journal, slots):
        _need(type(journal) is model.PublicationJournal, "journal_type")
        _need(journal.snapshot()["teardown"] == "not_started", "journal_teardown_already_started")
        _need(type(slots) is tuple and 0 < len(slots) <= MAX_HANDLES)
        handles, identities = set(), set()
        for index, slot in enumerate(slots):
            _need(type(slot) is OwnedSlot)
            rename._pin(slot.pin)
            identity = (slot.pin.volume, slot.pin.file_id)
            _need(slot.pin.handle not in handles and identity not in identities)
            handles.add(slot.pin.handle)
            identities.add(identity)
            if slot.parent is None:
                _need(slot.pin.directory)
            else:
                _need(type(slot.parent) is int and 0 <= slot.parent < index)
                parent = slots[slot.parent].pin
                _need(parent.directory and parent.volume == slot.pin.volume)
        # Allocate every tracking slot before accepting ownership.
        self._states = ["owned"] * len(slots)
        self._codes = [0] * len(slots)
        self._reentry_error = OwnershipError("teardown_already_started")
        self._backend, self._journal, self._slots = backend, journal, slots
        self._started = self._done = self._resource_stop = False
        self._first_error = None
        self._journal_finalization = "not_started"

    def _record(self, error):
        if self._first_error is None:
            self._first_error = error
        self._resource_stop = self._resource_stop or _resource(error)

    def finish(self, *, primary=None):
        """Perform terminal handle release, then raise the first/original error.

        An operation failure supplied as primary always wins over close errors.
        Each close exception is contained so the remaining distinct handles get
        one attempt. Close success cannot turn a stopped publication into success.
        """
        _need(primary is None or isinstance(primary, BaseException), "primary_type")
        if self._started:
            self._record(self._reentry_error)
            self._journal.stop(resource=self._resource_stop)
            raise self._reentry_error
        self._started = True
        if primary is not None:
            self._record(primary)
        try:
            try:
                state = self._journal.snapshot()
                self._resource_stop = self._resource_stop or state["resource_stop"]
                if primary is not None or state["model_status"] not in ("stopped", "awaiting_teardown"):
                    self._journal.stop(resource=self._resource_stop)
            except BaseException as error:
                self._record(error)
            for index in range(len(self._slots) - 1, -1, -1):
                self._states[index] = "pending"
                try:
                    result = self._backend.close_handle(self._slots[index].pin.handle)
                    if type(result) is int and result == 0:
                        code = self._backend.get_last_error()
                        _need(type(code) is int and 0 < code < 1 << 32, "close_error_unavailable")
                        self._codes[index] = code
                        raise OwnershipError("close_failed", code)
                    _need(type(result) is int and -(1 << 31) <= result < 1 << 31 and result != 0,
                          "close_result_shape")
                    self._states[index] = "closed"
                except BaseException as error:
                    self._states[index] = "unknown"
                    self._record(error)
            self._journal_finalization = "pending"
            try:
                if self._first_error is not None:
                    self._journal.stop(resource=self._resource_stop)
                self._journal.finish_teardown(success=all(state == "closed" for state in self._states))
                self._journal_finalization = "confirmed"
            except BaseException as error:
                self._journal_finalization = "unknown"
                self._record(error)
                try:
                    self._journal.stop(resource=self._resource_stop)
                except BaseException as secondary:
                    self._record(secondary)
        finally:
            self._done = True
        if self._first_error is not None:
            raise self._first_error

    def snapshot(self):
        """Detached bounded metadata; never a low-memory allocation guarantee."""
        return {
            "owner_status": "finished" if self._done else "releasing" if self._started else "owned",
            "journal_finalization": self._journal_finalization,
            "handles": [{"slot": index, "parent": slot.parent, "state": self._states[index],
                         "winerror": self._codes[index]}
                        for index, slot in enumerate(self._slots)],
            "resource_stop": self._resource_stop,
            "all_closes_confirmed": all(state == "closed" for state in self._states),
            "retry_permitted": False, "path_cleanup_permitted": False,
            "acceptance_status": "not_completed", "formal_permission": False,
            "execution_authenticated": False,
        }
