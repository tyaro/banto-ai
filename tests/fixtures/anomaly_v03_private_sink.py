"""Engineering-only Windows private evidence storage; no publisher or cleanup.

Imports existing B1 low-level bindings lazily, but never runs its harness, token
mutation, or child controls. A new caller-selected local directory is retained.
The owner/admin, deliberate ACL changes, mappings and hostile same-user
create/bind race remain outside the trust model. This issues no acceptance.
"""
import ctypes as C
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sys

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_prepublication as prep
from .anomaly_v03_tracked_open import TrackedOpen

NAMES = ("prepare.json", "seal_payload.json", "verify_final.json")


class _Backend:
    def __init__(self, api):
        self.api = api

    def close_handle(self, handle):
        return self.api.k.CloseHandle(handle)

    def get_last_error(self):
        return C.get_last_error()


class WindowsPrivateSink:
    """Explicit connect -> up to three exclusive saves -> finish, no retry.

    connect requires an absent root and an existing local NTFS parent. All
    ancestors stay pinned without DELETE sharing until terminal finish.
    No mutation to existing ancestors, and no automatic file/directory deletion.
    """

    def __init__(self):
        self._leases = []
        self._used = [False] * 3
        self._states = ["not_started"] * 3
        self._counts = [0] * 3
        self._hashes = [None] * 3
        self._budget = 0
        self._started = self._connected = self._finished = self._failed = self._busy = False
        self._resource = False
        self._root_state = "not_started"
        self._token = None

    def _failure(self, error):
        self._failed = True
        self._resource = self._resource or owned._resource(error)

    def _check(self):
        owned._need(self._connected and not self._finished and not self._failed, "sink_not_available")
        for lease in self._leases:
            if lease.close_state == "not_started":
                lease.observed.check()

    def _file_view(self, handle, path, directory):
        # Borrow the captured raw handle: _Bound construction would open and own
        # another handle. Only observation/read methods are used on this view.
        view = self._win._Bound.__new__(self._win._Bound)
        view.api, view.path, view.directory, view.handle = self._api, path, directory, handle
        view.identity = view.observe()
        view.check()
        return view

    @contextmanager
    def _descriptor(self, directory):
        descriptor = self._api.descriptor(self._win._dacl(self._user, "private", directory)[0])
        primary = None
        try:
            yield descriptor
        except BaseException as error:
            primary = error
            raise
        finally:
            try:
                owned._need(not self._api.k.LocalFree(descriptor), "descriptor_free_failed")
            except BaseException as error:
                self._failure(error)
                if primary is None:
                    raise

    def _open(self, path, *, directory, create=False):
        lease = TrackedOpen(self._backend)
        self._leases.append(lease)  # Register BEFORE any native acquisition.
        def opener(cell):
            def create_file(descriptor):
                security = self._win._SA(C.sizeof(self._win._SA), descriptor, False) if descriptor else None
                cell.handle = self._api.k.CreateFileW(str(path), 0xC0020000 if create else 0x20081,
                    0 if create else 3, C.byref(security) if security else None, 1 if create else 3,
                    0x00200000 | (0x02000000 if directory else 0), None)
                if cell.handle == C.c_void_p(-1).value:
                    raise owned.OwnershipError("file_open_failed", C.get_last_error())
            if create:
                with self._descriptor(directory) as descriptor:
                    create_file(descriptor)
            else:
                create_file(None)
        lease.acquire(opener, lambda handle: self._file_view(handle, path, directory))
        return lease

    def _read_user(self):
        token = self._token = TrackedOpen(self._backend)
        def open_token(cell):
            value = self._win.H()
            ok = self._api.a.OpenProcessToken(self._api.k.GetCurrentProcess(), 8, C.byref(value))
            self._api.call(ok, "sink_token_query")
            # A FALSE call does not establish ownership of its output value.
            cell.handle = value.value
        try:
            return token.acquire(open_token, lambda handle: self._api.profile(handle)["user"][0])
        finally:
            token.close()

    def connect(self, root):
        owned._need(not self._started, "sink_attempt_reused")
        self._started = True
        try:
            owned._need(os.name == "nt" and sys.version_info[:3] == (3, 14, 0) and C.sizeof(C.c_void_p) == 8,
                        "sink_runtime_unavailable")
            from banto_ai import _anomaly_v03_windows as win
            self._win, self._api = win, win._api()
            self._backend = _Backend(self._api)
            self._root = Path(root)
            owned._need(self._root.is_absolute() and len(self._root.parents) <= 16, "sink_root_shape")
            win._lexical(self._root)
            # Read the caller SID without creating or changing a token.
            self._user = self._read_user()
            for parent in reversed(self._root.parents):
                self._open(parent, directory=True)
            self._root_state = "create_pending"
            with self._descriptor(True) as descriptor:
                security = win._SA(C.sizeof(win._SA), descriptor, False)
                self._api.call(self._api.k.CreateDirectoryW(str(self._root), C.byref(security)), "sink_root_create")
                self._root_state = "created"
            root_lease = self._open(self._root, directory=True)
            win._verify_sd(self._api.security(root_lease.handle), self._user, "private", True)
            owned._need(not list(self._root.iterdir()), "sink_root_not_empty")
            self._root_state = "verified"
            self._connected = True
        except BaseException as error:
            self._failure(error)
            self.finish(primary=error)

    def persist_evidence(self, step, raw, digest):
        lease, entered = None, False
        try:
            owned._need(not self._busy, "sink_reentered")
            self._busy = entered = True
            self._check()
            owned._need(type(step) is str and step in owned.RELEASE_STEPS, "sink_phase")
            index = owned.RELEASE_STEPS.index(step)
            owned._need(not self._used[index] and type(raw) is bytes and 0 < len(raw) <= prep.MAX_EVIDENCE_BYTES,
                        "sink_input")
            owned._need(type(digest) is str and hashlib.sha256(raw).hexdigest() == digest, "sink_digest")
            owned._need(self._budget + len(raw) <= prep.MAX_ATTEMPT_BYTES, "sink_budget")
            self._used[index] = True
            self._budget += len(raw)
            self._counts[index], self._hashes[index] = len(raw), digest
            self._states[index] = "create_pending"
            buffer, written = C.create_string_buffer(raw), self._win.D()
            lease = self._open(self._root / NAMES[index], directory=False, create=True)
            view = lease.observed
            self._win._verify_sd(self._api.security(lease.handle), self._user, "private", False)
            owned._need(not self._failed, "sink_interrupted")
            self._states[index] = "write_pending"
            self._api.call(self._api.k.WriteFile(lease.handle, buffer, len(raw), C.byref(written), None), "sink_write")
            owned._need(written.value == len(raw), "sink_short_write")
            owned._need(not self._failed, "sink_interrupted")
            self._states[index] = "flush_pending"
            self._api.call(self._api.k.FlushFileBuffers(lease.handle), "sink_flush")
            owned._need(not self._failed, "sink_interrupted")
            self._states[index] = "readback_pending"
            observed = view.read()
            owned._need(observed == raw and hashlib.sha256(observed).hexdigest() == digest, "sink_readback")
            self._win._verify_sd(self._api.security(lease.handle), self._user, "private", False)
            owned._need(not self._failed, "sink_interrupted")
            self._states[index] = "close_pending"
            lease.close()
            owned._need(not self._failed, "sink_interrupted")
            self._states[index] = "saved"
        except BaseException as error:
            self._failure(error)
            if lease is not None:
                lease.close(primary=error)
            raise
        finally:
            if entered:
                self._busy = False

    def finish(self, *, primary=None):
        if self._busy:
            error = owned.OwnershipError("sink_busy")
            self._failure(error)
            raise error
        if self._finished:
            if primary is not None:
                raise primary
            return
        self._finished = True
        first = primary
        for lease in reversed(self._leases):
            try:
                lease.close()
            except BaseException as error:
                self._failure(error)
                if first is None:
                    first = error
        if first is not None:
            raise first

    def snapshot(self):
        return {"root_state": self._root_state, "connected": self._connected, "finished": self._finished,
                "stopped": self._failed, "resource_stop": self._resource, "reserved_bytes": self._budget,
                "files": [{"name": NAMES[i], "state": self._states[i], "bytes": self._counts[i], "sha256": self._hashes[i]}
                          for i in range(3)],
                "handles": [lease.snapshot() for lease in self._leases],
                "token": None if self._token is None else self._token.snapshot(),
                "retry_permitted": False, "cleanup_permitted": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
