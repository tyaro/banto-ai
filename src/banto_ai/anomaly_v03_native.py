"""Windows native acceptance helpers for dedicated temporary v0.3 fixtures.

This module has no formal publisher entry point. Every ACL mutation is confined
to an already published FixturePublication under the system temporary directory.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

from ._anomaly_v03_io import _fixture_parent, windows_readonly_access_check
from ._anomaly_v03_runtime import require, regular_path

_DACL_SECURITY_INFORMATION = 0x4
_PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
_TOKEN_QUERY = 0x8
_TOKEN_DUPLICATE = 0x2
_DISABLE_MAX_PRIVILEGE = 0x1
_SECURITY_IMPERSONATION = 2
_TOKEN_IMPERSONATION = 2


def _api():
    require(os.name == "nt", "Windows native fixture required")
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.DWORD)]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    security.GetSecurityDescriptorDacl.argtypes = [
        wintypes.LPVOID, ctypes.POINTER(wintypes.BOOL), ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.BOOL)]
    security.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    security.SetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID]
    security.SetNamedSecurityInfoW.restype = wintypes.DWORD
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.OpenProcessToken.restype = wintypes.BOOL
    security.CreateRestrictedToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID,
        ctypes.POINTER(wintypes.HANDLE)]
    security.CreateRestrictedToken.restype = wintypes.BOOL
    security.DuplicateTokenEx.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
        wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.DuplicateTokenEx.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [wintypes.LPVOID]
    kernel.LocalFree.restype = wintypes.LPVOID
    return security, kernel


def _set_dacl(path: Path, sddl: str):
    security, kernel = _api()
    descriptor = wintypes.LPVOID()
    require(security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), None), "fixture SDDL conversion failed")
    try:
        present, dacl, defaulted = wintypes.BOOL(), wintypes.LPVOID(), wintypes.BOOL()
        require(security.GetSecurityDescriptorDacl(
            descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted))
            and present.value and dacl.value, "fixture DACL extraction failed")
        error = security.SetNamedSecurityInfoW(
            str(path), 1, _DACL_SECURITY_INFORMATION | _PROTECTED_DACL_SECURITY_INFORMATION,
            None, None, dacl, None)
        require(error == 0, "fixture DACL installation failed")
    finally:
        kernel.LocalFree(descriptor)


def _published_paths(root: Path) -> list[Path]:
    root = regular_path(root, directory=True)
    _fixture_parent(root.parent)
    require({p.name for p in root.iterdir()} == {"payload", "marker-pending.json", ".complete"},
            "fixture publication is incomplete")
    paths, pending = [root], [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            metadata = path.lstat()
            require(not getattr(metadata, "st_file_attributes", 0) & 0x400 and not path.is_symlink(),
                    "fixture reparse entry")
            is_directory = bool(metadata.st_file_attributes & 0x10)
            control = path.parent == root and path.name in (".complete", "marker-pending.json")
            paths.append(regular_path(path, directory=is_directory, links=2 if control else 1))
            if is_directory:
                pending.append(path)
    return paths


def protect_fixture_publication(root: Path):
    """Install read-only protected DACLs on a completed, temp-only fixture.

    The owner can still change the DACL. This does not grant formal acceptance.
    Failures leave the published tree and any DACLs already set for inspection.
    """
    paths = _published_paths(Path(root))
    # Windows file generic read contains the rights needed by the fresh reader.
    # No ordinary write/delete allow ACE exists, including for Administrators.
    sddl = "D:P(A;;FR;;;WD)"
    for path in sorted(paths[1:], key=lambda p: len(p.parts), reverse=True):
        _set_dacl(path, sddl)
    _set_dacl(paths[0], sddl)
    return {"objects": len(paths), "acl_scope": "system-temp-fixture", "native_acceptance": "not_completed"}


@contextmanager
def restricted_child_token():
    """Yield an impersonation token derived from a separate Python process.

    The child does no filesystem work. Its token is duplicated with privileges
    disabled, then used by real Win32 AccessCheck in the parent.
    """
    security, kernel = _api()
    child = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    handles = []
    try:
        source = wintypes.HANDLE()
        require(security.OpenProcessToken(int(child._handle), _TOKEN_QUERY | _TOKEN_DUPLICATE,
                                          ctypes.byref(source)), "child process token unavailable")
        handles.append(source)
        restricted = wintypes.HANDLE()
        require(security.CreateRestrictedToken(source, _DISABLE_MAX_PRIVILEGE, 0, None, 0, None,
                                                0, None, ctypes.byref(restricted)),
                "restricted child token unavailable")
        handles.append(restricted)
        impersonation = wintypes.HANDLE()
        require(security.DuplicateTokenEx(restricted, _TOKEN_QUERY, None,
                                           _SECURITY_IMPERSONATION, _TOKEN_IMPERSONATION,
                                           ctypes.byref(impersonation)),
                "restricted impersonation token unavailable")
        handles.append(impersonation)
        yield int(impersonation.value), child.pid
    finally:
        for handle in reversed(handles):
            kernel.CloseHandle(handle)
        child.terminate()
        child.wait(timeout=5)


def check_protected_fixture(root: Path) -> dict:
    """Check every object with an independent-process restricted token."""
    root = Path(root)
    paths = _published_paths(root)
    with restricted_child_token() as (token, pid):
        checks = []
        for path in paths:
            result = windows_readonly_access_check(
                path, token, links=2 if path.parent == root and path.name in (".complete", "marker-pending.json") else 1)
            require(result["protected_dacl"] and not any(result["allowed"].values()),
                    "fixture ordinary write/delete access remains")
            checks.append({"path": path.relative_to(root).as_posix() if path != root else ".",
                           "protected_dacl": True, "denied": sorted(result["allowed"])})
    return {"objects_checked": len(checks), "checks": checks, "child_pid": pid,
            "native_acceptance": "not_completed"}
