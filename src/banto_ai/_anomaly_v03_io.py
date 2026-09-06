"""S3 exclusive staging, fresh readback and completion-inventory publication.

The runnable publisher is restricted to dedicated system-temp fixtures. Native
DACL installation/independent-token acceptance and formal publication remain
S4 obligations. No recovery, overwrite, cleanup, repository ACL or old artifact
mutation is performed. Failed staging is retained for explicit inspection.
"""

from __future__ import annotations

import ctypes
import os
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path

from . import anomaly_v03 as v
from ._anomaly_v03_runtime import IntegrityError, regular_path, require
from .anomaly_v03_materializer import sha, json_bytes


def payload_entry(path: str, raw: bytes) -> dict:
    v.safe_relative_path(path)
    require(type(raw) is bytes, "payload must be bytes")
    if path.endswith(".jsonl"):
        require(not raw or raw.endswith(b"\n") and b"\r" not in raw, "invalid JSONL framing")
        values = [v.strict_json(line) for line in raw.splitlines()]
        require(b"".join(json_bytes(x) for x in values) == raw, "noncanonical JSONL")
        canonical, rows = v.canonical_json(values), len(values)
    elif path.endswith(".json"):
        value = v.strict_json(raw)
        require(json_bytes(value) == raw, "noncanonical JSON payload")
        canonical, rows = v.canonical_json(value), len(value) if type(value) is list else 1
    else:
        raw.decode("utf-8", errors="strict")
        require(raw.endswith(b"\n") and b"\r" not in raw, "non-UTF8/LF text")
        canonical, rows = raw, len(raw.splitlines())
    return {"path": path, "raw_sha256": sha(raw), "canonical_sha256": sha(canonical), "row_count": rows}


def inventory(files: dict[str, bytes]) -> list:
    return [payload_entry(path, files[path]) for path in sorted(files)]


def _identity(metadata):
    require(metadata.st_ino != 0, "filesystem identity unavailable")
    return metadata.st_dev, metadata.st_ino


class DirectoryBinding:
    """Windows denies deletion of each bound directory; POSIX fixture uses fstat."""

    def __init__(self, path):
        self.path = regular_path(path, directory=True)
        self.identity = _identity(self.path.lstat())
        self.handle = self.fd = None
        if os.name == "nt":
            from ctypes import wintypes
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            self.kernel.CreateFileW.restype = wintypes.HANDLE
            self.kernel.CloseHandle.argtypes, self.kernel.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
            self.handle = self.kernel.CreateFileW(str(self.path), 0x81, 0x3, None, 3, 0x02200000, None)
            if self.handle == ctypes.c_void_p(-1).value:
                self.handle = None
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.check()
        except BaseException:
            self.close()
            raise

    def check(self):
        require(_identity(regular_path(self.path, directory=True).lstat()) == self.identity, "directory identity changed")
        if self.fd is not None:
            require(_identity(os.fstat(self.fd)) == self.identity, "directory descriptor changed")

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def read_regular(path: Path, *, links=1) -> bytes:
    path = regular_path(path, links=links)
    before = path.lstat()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        require(_identity(opened) == _identity(before) and stat.S_ISREG(opened.st_mode), "file replaced during open")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            raw = stream.read()
            after = os.fstat(stream.fileno())
        require((opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) ==
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "file changed during read")
        require(_identity(regular_path(path, links=links).lstat()) == _identity(before) and len(raw) == before.st_size, "file replaced after read")
        return raw
    finally:
        if fd is not None:
            os.close(fd)


def _tree_paths(root: Path) -> tuple[str, ...]:
    root = regular_path(root, directory=True)
    files = []
    with_bindings = []
    try:
        pending = [root]
        while pending:
            directory = pending.pop()
            with_bindings.append(DirectoryBinding(directory))
            for entry in sorted(directory.iterdir()):
                metadata = entry.lstat()
                require(not getattr(metadata, "st_file_attributes", 0) & 0x400 and not stat.S_ISLNK(metadata.st_mode), "reparse in payload inventory")
                if stat.S_ISDIR(metadata.st_mode):
                    pending.append(entry)
                else:
                    relative = entry.relative_to(root).as_posix()
                    v.safe_relative_path(relative)
                    regular_path(entry)
                    files.append(relative)
        # Extra empty directories also change the inventory; reject them.
        expected_dirs = {root}
        for name in files:
            expected_dirs.update(p for p in (root/name).parents if p == root or root in p.parents)
        require({b.path for b in with_bindings} == expected_dirs, "unexpected empty directory")
        for binding in with_bindings:
            binding.check()
        return tuple(sorted(files))
    finally:
        for binding in reversed(with_bindings):
            binding.close()


class PayloadView(Mapping):
    """One-file-at-a-time read-only view; never retain a whole 2,880-slot run."""
    def __init__(self, root):
        self.root, self.paths = root, _tree_paths(root)
        self._names = frozenset(self.paths)

    def __getitem__(self, name):
        if name not in self._names:
            raise KeyError(name)
        return read_regular(self.root/name)

    def __iter__(self):
        return iter(self.paths)

    def __len__(self):
        return len(self.paths)


def read_tree(root: Path) -> dict[str, bytes]:
    """Convenience for small test trees. Campaign verification uses PayloadView."""
    return dict(PayloadView(root))


def _exclusive(path: Path, raw: bytes):
    regular_path(path, missing=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "nonregular output")
        with os.fdopen(fd, "wb") as stream:
            fd = None
            require(stream.write(raw) == len(raw), "partial write")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd is not None:
            os.close(fd)
    require(read_regular(path) == raw, "exclusive write readback differs")


def _rename_no_replace(source: Path, target: Path):
    if os.name == "nt":
        # Windows os.rename fails if destination exists; it never replaces it.
        os.rename(source, target)
    elif sys_platform_linux():
        # Linux fixture only. No check-then-POSIX-rename overwrite emulation.
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        require(rename is not None, "atomic no-replace unavailable")
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1):
            raise OSError(ctypes.get_errno(), "atomic no-replace failed")
    else:
        raise IntegrityError("atomic no-replace unsupported on this fixture platform")


def sys_platform_linux():
    import sys
    return sys.platform == "linux"


def _fixture_parent(parent: Path):
    parent = regular_path(parent, directory=True)
    temporary = regular_path(Path(tempfile.gettempdir()), directory=True)
    require(parent != temporary and temporary in parent.parents, "dedicated system-temp fixture parent required")
    require(not any((p/".git").exists() for p in (parent, *parent.parents)), "repository is not a fixture workspace")
    require(not any(p.name.startswith("anomaly-multiseed-v0") for p in (parent, *parent.parents)), "formal root is not a fixture workspace")
    return parent


class FixturePublication:
    """Single attempt, dedicated temp only. Final marker is the commit point.

    All payloads live under payload/. Marker installation is an atomic hardlink
    from the retained marker-pending.json. The two marker names are intentionally
    inventoried control files, never payload inputs. No native ACL claim is made.
    """

    def __init__(self, parent: Path, name: str):
        self.parent = _fixture_parent(parent)
        v.safe_relative_path(name)
        require("/" not in name and not name.startswith("anomaly-multiseed-v0"), "unsafe fixture name")
        self.root, self.bindings, self.expected = self.parent/name, [], {}
        self.committed = False
        self.bindings.append(DirectoryBinding(self.parent))
        try:
            self.root.mkdir()  # exclusive even when an old root has no marker
            self.bindings.append(DirectoryBinding(self.root))
            self.stage = self.root/"stage"
            self.stage.mkdir()
            self.bindings.append(DirectoryBinding(self.stage))
        except BaseException:
            self.close()
            raise

    def check(self):
        for binding in self.bindings:
            binding.check()

    def write(self, name: str, raw: bytes):
        self.check()
        require(not self.committed and self.stage.name == "stage", "publication already finalized")
        v.safe_relative_path(name)
        require(name not in self.expected, "duplicate exclusive output")
        path = self.stage/name
        for directory in reversed(path.parent.parents):
            if self.stage in directory.parents and not directory.exists():
                directory.mkdir()
                self.bindings.append(DirectoryBinding(directory))
        if not path.parent.exists():
            path.parent.mkdir()
            self.bindings.append(DirectoryBinding(path.parent))
        regular_path(path.parent, directory=True)
        _exclusive(path, raw)
        self.expected[name] = payload_entry(name, raw)
        self.check()

    def read(self, name):
        v.safe_relative_path(name)
        self.check()
        require(name in self.expected, "unowned payload read")
        raw = read_regular(self.stage/name)
        require(payload_entry(name, raw) == self.expected[name], "saved input/evidence changed")
        return raw

    def verify(self):
        self.check()
        captured = PayloadView(self.stage)
        require(inventory(captured) == [self.expected[n] for n in sorted(self.expected)], "staged payload inventory changed")
        return captured

    def publish(self, verify_semantics, recheck_boundary):
        captured = self.verify()
        fixed_inventory = [dict(self.expected[n]) for n in sorted(self.expected)]
        verify_semantics(captured)
        recheck_boundary()
        require(inventory(self.verify()) == fixed_inventory, "payload changed during semantic verification")
        marker = {"schema_version": "0.3", "marker_type": "anomaly-v03-fixture-complete",
                  "payload_inventory": fixed_inventory, "inventory_sha256": v.canonical_sha256(fixed_inventory),
                  "native_acceptance": "not_completed", "performance_status": "not_evaluated"}
        marker_raw = json_bytes(marker)
        _exclusive(self.root/"marker-pending.json", marker_raw)
        # Child directory handles must be released for Windows directory rename.
        for binding in reversed(self.bindings[2:]):
            binding.close()
        self.bindings = self.bindings[:2]
        _rename_no_replace(self.stage, self.root/"payload")
        self.stage = self.root/"payload"
        require(inventory(PayloadView(self.stage)) == fixed_inventory, "payload changed at finalization")
        recheck_boundary()
        self.check()
        require(inventory(PayloadView(self.stage)) == fixed_inventory and read_regular(self.root/"marker-pending.json") == marker_raw,
                "payload/marker changed before commit")
        # Link creation is atomic and fails on an existing marker. Retain source
        # evidence; no potentially failing mutation follows the commit point.
        os.link(self.root/"marker-pending.json", self.root/".complete", follow_symlinks=False)
        self.committed = True
        return {"output_path": str(self.root), "marker_raw_sha256": sha(marker_raw), "native_acceptance": "not_completed"}

    def close(self):
        for binding in reversed(self.bindings):
            binding.close()
        self.bindings = []

    def preserve_failure(self, result):
        """Best effort, owned root only; a bad topology is never repaired."""
        self.check()
        require(not self.committed, "cannot change committed publication")
        _exclusive(self.root/"failure.json", json_bytes({"schema_version": "0.3", "failure_stage": "publication",
                   "safe_reason": "incomplete", "result": result}))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()  # handle release only, retain every attempt


def verify_fixture_publication(root: Path, *, expected_marker_sha256: str, verify_semantics):
    root = regular_path(root, directory=True)
    _fixture_parent(root.parent)
    require({p.name for p in root.iterdir()} == {"payload", "marker-pending.json", ".complete"}, "publication control inventory")
    # These two known control names are intentionally hardlinked. They are not
    # opened through read_regular, which rejects all multiply-linked payloads.
    marker_path, pending = root/".complete", root/"marker-pending.json"
    for path in (marker_path, pending):
        meta = path.lstat()
        require(stat.S_ISREG(meta.st_mode) and not getattr(meta, "st_file_attributes", 0) & 0x400
                and meta.st_nlink == 2, "invalid marker object")
    require(_identity(marker_path.lstat()) == _identity(pending.lstat()), "marker identity mismatch")
    raw = read_regular(marker_path, links=2)
    require(sha(raw) == expected_marker_sha256 and raw == read_regular(pending, links=2), "external marker pin mismatch")
    v.strict_json(raw)
    files = PayloadView(root/"payload")
    entries = inventory(files)
    expected = {"schema_version": "0.3", "marker_type": "anomaly-v03-fixture-complete", "payload_inventory": entries,
                "inventory_sha256": v.canonical_sha256(entries), "native_acceptance": "not_completed", "performance_status": "not_evaluated"}
    require(raw == json_bytes(expected), "completion inventory/hash mismatch")
    verify_semantics(files)  # A newly forged marker/summary still cannot bless wrong ledgers.
    require(inventory(PayloadView(root/"payload")) == entries and read_regular(marker_path, links=2) == raw, "publication changed during verification")
    return {"payloads": len(entries), "fixture_verified": True, "native_acceptance": "not_completed"}


def native_acl_requirements():
    """The exact ordinary rights to deny in S4's independent reader token."""
    return {"file": {"write": 0x2, "append": 0x4, "write_ea": 0x10, "write_attributes": 0x100, "delete": 0x10000},
            "directory": {"add_file": 0x2, "add_subdirectory": 0x4, "delete_child": 0x40,
                          "write_ea": 0x10, "write_attributes": 0x100, "delete": 0x10000}}


def windows_readonly_access_check(path: Path, reader_token: int) -> dict:
    """Read a protected DACL and call real AccessCheck. Never installs an ACL.

    S4 must create an independent-process impersonation token and establish its
    provenance. Supplying an arbitrary token here is not acceptance proof.
    """
    require(os.name == "nt" and type(reader_token) is int and reader_token > 0, "Windows reader token required")
    from ctypes import wintypes
    path = Path(path)
    directory = path.is_dir()
    regular_path(path, directory=directory)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security.GetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
        wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID, ctypes.POINTER(wintypes.LPVOID)]
    security.GetNamedSecurityInfoW.restype = wintypes.DWORD
    security.GetSecurityDescriptorControl.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    security.GetSecurityDescriptorControl.restype = wintypes.BOOL
    class Mapping(ctypes.Structure):
        _fields_ = [(x, wintypes.DWORD) for x in ("read", "write", "execute", "all")]
    security.AccessCheck.argtypes = [wintypes.LPVOID, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(Mapping),
        wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.BOOL)]
    security.AccessCheck.restype = wintypes.BOOL
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [wintypes.LPVOID], wintypes.LPVOID
    descriptor, control, revision = wintypes.LPVOID(), wintypes.WORD(), wintypes.DWORD()
    error = security.GetNamedSecurityInfoW(str(path), 1, 7, None, None, None, None, ctypes.byref(descriptor))
    require(error == 0, "native security descriptor read failed")
    try:
        require(security.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)), "native descriptor control failed")
        allowed = {}
        mapping = Mapping(0x120089, 0x120116, 0x1200a0, 0x1f01ff)
        for label, access in native_acl_requirements()["directory" if directory else "file"].items():
            privilege, size = ctypes.create_string_buffer(4096), wintypes.DWORD(4096)
            granted, status = wintypes.DWORD(), wintypes.BOOL()
            require(security.AccessCheck(descriptor, reader_token, access, ctypes.byref(mapping), privilege,
                    ctypes.byref(size), ctypes.byref(granted), ctypes.byref(status)), "native AccessCheck failed")
            allowed[label] = bool(status.value)
        return {"protected_dacl": bool(control.value & 0x1000), "allowed": allowed,
                "independent_token_provenance": "requires_s4_evidence", "native_acceptance": "not_completed"}
    finally:
        kernel.LocalFree(descriptor)
