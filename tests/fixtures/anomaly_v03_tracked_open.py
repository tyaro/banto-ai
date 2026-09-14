"""Capture a CloseHandle-compatible value before inspecting the opened object.

The trusted opener writes cell.handle immediately after the OS call. If it
raises before recording a valid value, ownership is unknown and a worker exit
is still needed; this is not an allocation-proof acquisition primitive.
"""
from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_rename_adapter as rename


class TrackedOpen:
    def __init__(self, backend):
        self._backend = backend
        self.handle = None
        self.observed = None
        self.state = "not_started"
        self.close_state = "not_started"
        self.resource_stop = False
        self._error = None
        self._acquiring = False

    def _record(self, error):
        if self._error is None:
            self._error = error
        self.resource_stop = self.resource_stop or owned._resource(error)

    def acquire(self, opener, inspect):
        if self.state != "not_started":
            error = owned.OwnershipError("open_attempt_reused")
            self._record(error)
            raise error
        self.state = "opening"
        self._acquiring = True
        try:
            result = opener(self)
            owned._need(self._error is None and result is None and rename._handle(self.handle), "open_value_unavailable")
            self.state = "inspecting"
            self.observed = inspect(self.handle)
            owned._need(self._error is None and self.observed is not None, "open_observation_unavailable")
            self.state = "ready"
            return self.observed
        except BaseException as error:
            self.state = "unknown"
            self._record(error)
            self._acquiring = False
            self.close(primary=error)
        finally:
            self._acquiring = False

    def close(self, *, primary=None):
        owned._need(primary is None or isinstance(primary, BaseException), "primary_type")
        if self._acquiring:
            error = owned.OwnershipError("close_during_acquisition")
            self._record(error)
            raise error
        if primary is not None:
            self._error = primary
            self._record(primary)
        if self.close_state == "not_started":
            if rename._handle(self.handle):
                self.close_state = "pending"  # Never call CloseHandle again, even on reply loss.
                try:
                    result = self._backend.close_handle(self.handle)
                    if type(result) is int and result == 0:
                        code = self._backend.get_last_error()
                        owned._need(type(code) is int and 0 < code < 1 << 32, "close_error_unavailable")
                        raise owned.OwnershipError("close_failed", code)
                    owned._need(type(result) is int and -(1 << 31) <= result < 1 << 31 and result != 0,
                                "close_result_shape")
                    self.close_state = "closed"
                    self.state = "closed"
                except BaseException as error:
                    self.close_state = "unknown"
                    self._record(error)
            else:
                # Do not guess a numeric handle when acquisition never exposed one.
                self.close_state = "unavailable" if self.state != "not_started" else "not_needed"
        if self._error is not None:
            raise self._error

    def snapshot(self):
        return {"state": self.state, "close_state": self.close_state, "resource_stop": self.resource_stop,
                "retry_permitted": False, "cleanup_permitted": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
