"""Bounded ownership, early release and teardown; injected close backend only.

No handle acquisition, native DLL, filesystem cleanup, or acceptance entrypoint.
Ownership transfers only when construction returns successfully. Until then the
caller owns every supplied pin. Afterwards, use synchronous borrowed operations
and owner release APIs; never close or use transferred pins independently.
"""
from dataclasses import dataclass

from . import anomaly_v03_publication_model as model
from . import anomaly_v03_rename_adapter as rename

MAX_HANDLES = 32
RELEASE_STEPS = ("prepare", "seal_payload", "verify_final")


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
        self._busy = False
        self._released_steps = [False] * len(RELEASE_STEPS)

    def _record(self, error):
        if self._first_error is None:
            self._first_error = error
        self._resource_stop = self._resource_stop or _resource(error)

    def _stop_safely(self):
        try:
            self._journal.stop(resource=self._resource_stop)
        except BaseException as error:
            self._record(error)

    def _usable(self):
        _need(not self._started and not self._busy and self._first_error is None, "owner_not_available")
        state = self._journal.snapshot()
        _need(state["model_status"] in ("not_started", "in_progress")
              and state["teardown"] == "not_started", "publication_not_active")

    def _indices(self, indices):
        _need(type(indices) is tuple and 0 < len(indices) <= len(self._slots), "invalid_selection")
        _need(all(type(index) is int and 0 <= index < len(self._slots) for index in indices), "invalid_selection")
        _need(len(set(indices)) == len(indices), "duplicate_selection")
        _need(all(self._states[index] == "owned" for index in indices), "handle_not_owned")

    def borrowed(self, indices, operation):
        """Synchronous trusted callback; release/finish cannot run inside it."""
        entered = False
        try:
            self._usable()
            self._indices(indices)
            pins = tuple(self._slots[index].pin for index in indices)
            self._busy = entered = True
            result = operation(pins)
            _need(self._first_error is None and self._journal.snapshot()["model_status"]
                  in ("not_started", "in_progress", "awaiting_teardown"), "borrow_interrupted")
            return result
        except BaseException as error:
            self._record(error)
            self._stop_safely()
            raise
        finally:
            if entered:
                self._busy = False

    def _close_one(self, index):
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

    def release_before_publish(self, step, indices):
        """One bounded release group during a pending preparation/check step.

        A closed/unknown slot is never revisited by terminal finish. The caller
        must retain its rename handles; this API does not infer native roles.
        """
        entered = False
        try:
            self._usable()
            _need(type(step) is str and step in RELEASE_STEPS, "release_phase")
            phase = RELEASE_STEPS.index(step)
            _need(not self._released_steps[phase], "release_phase_reused")
            self._indices(indices)
            state = self._journal.snapshot()
            _need(any(row["step"] == step and row["state"] == "pending" for row in state["steps"]), "release_not_pending")
            # A parent cannot be released while a child is owned or unknown.
            selected = set(indices)
            _need(all(slot.parent not in selected or self._states[index] == "closed" or index in selected
                      for index, slot in enumerate(self._slots)), "live_descendant")
            order = sorted(indices, reverse=True)
            self._released_steps[phase] = True
            self._busy = entered = True
            for index in order:
                self._close_one(index)
            if self._first_error is not None:
                raise self._first_error
            _need(self._journal.snapshot()["model_status"] == "in_progress"
                  and any(row["step"] == step and row["state"] == "pending"
                          for row in self._journal.snapshot()["steps"]), "release_interrupted")
        except BaseException as error:
            self._record(error)
            self._stop_safely()
            raise
        finally:
            if entered:
                self._busy = False

    def finish(self, *, primary=None):
        """Perform terminal handle release, then raise the first/original error.

        An operation failure supplied as primary always wins over close errors.
        Each close exception is contained so the remaining distinct handles get
        one attempt. Close success cannot turn a stopped publication into success.
        """
        _need(primary is None or isinstance(primary, BaseException), "primary_type")
        if self._started or self._busy:
            self._record(self._reentry_error)
            self._stop_safely()
            raise self._reentry_error
        self._started = True
        if primary is not None:
            self._first_error = primary
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
                if self._states[index] == "owned":
                    self._close_one(index)
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
