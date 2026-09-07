"""S4-B1, engineering-only Windows controls. NOT a publisher or a sandbox.

Only run_control_harness() is public; it accepts no path, ACL or token. All
mutations belong to a newly created UUID system-temp tree. Cleanup failure retains
its private pre-cleanup evidence and a partial transition record, not every file.
Protected DACL means no inherited ACEs, not WORM, owner/admin/WRITE_DAC or
WRITE_OWNER resistance, privileged-writer protection, or power-loss durability.
The parent and fixed child are trusted code in the same account/logon. A hostile
same-user create/bind swap or writable mapping is outside this control's model.
No S4 acceptance or campaign permission is issued, even on native success.
"""

from __future__ import annotations

import ctypes as C
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

__all__ = ["run_control_harness"]
_PREFIX = "banto-s4-b1-"
_LIMIT = 1024 * 1024
_MEMORY_LIMIT = 512 * 1024 * 1024
_REPLACE_TRACE_NAME = "control/replace-trace.jsonl"
_REPLACE_TRACE_LIMIT = 128 * 1024
_CHILD_RESOURCE_EXIT = 80
_REPLACE_STAGES = ("create_pending", "target_captured", "replace_pending", "replaced", "restore_pending", "restored")
_FILE_RIGHTS = {"write": 2, "append": 4, "write_ea": 16, "write_attributes": 256, "delete": 65536}
_DIR_RIGHTS = {"add_file": 2, "add_subdirectory": 4, "write_ea": 16,
               "write_attributes": 256, "delete": 65536, "delete_child": 64}
_PRIVILEGED = {"S-1-5-32-544", "S-1-5-32-547", "S-1-5-32-548", "S-1-5-32-549",
               "S-1-5-32-550", "S-1-5-32-551"}
_RC = "S-1-5-12"
_NON_GOALS = ["owner-admin", "write-dac-write-owner", "privileged-writer", "writable-mapping",
              "hostile-same-user-bootstrap-swap", "sandbox", "worm", "power-loss", "publication"]
_ROOT = Path(__file__).absolute().parents[2]
_CHILD = _ROOT / "tests/fixtures/anomaly_v03_native_child.py"
_SOURCE = Path(__file__).absolute()
_EXE_SHA = "467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec"
_DLL_SHA = "f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a"

D = C.c_uint32
H = C.c_void_p
B = C.c_int32
P = C.POINTER


class _Failure(Exception):
    def __init__(self, reason, error=0, *, child_exit_code=None):
        self.reason, self.error, self.child_exit_code = reason, int(error), child_exit_code
        super().__init__("s4_b1_control_failed")  # No paths, argv, handles or underlying exception text.


def _need(ok, reason):
    if not ok:
        raise _Failure(reason)


_RESOURCE_REASONS = ("memory_budget", "source_size", "source_index_size", "file_size", "child_resource_stop")


def _resource_stop(error):
    return (isinstance(error, MemoryError)
            or type(error) is _Failure and error.reason in _RESOURCE_REASONS
            or isinstance(getattr(error, "teardown", None), _Teardown) and error.teardown.resource_stop)


class _Teardown:
    """Small fixed-capacity diagnostics; no exception text, paths or handles."""
    def __init__(self):
        self.count, self.reasons, self.resource_stop = 0, [None] * 8, False

    def record(self, reason, error=None):
        if self.count < len(self.reasons):
            self.reasons[self.count] = reason
        self.count = min(self.count + 1, 65535)
        self.resource_stop |= _resource_stop(error)

    def merge(self, other):
        if other is self:
            return
        count = self.count
        for index in range(min(other.count, len(other.reasons), len(self.reasons) - min(count, len(self.reasons)))):
            self.reasons[count + index] = other.reasons[index]
        self.count = min(count + other.count, 65535)
        self.resource_stop |= other.resource_stop

    def attempt(self, reason, operation):
        try:
            operation()
            return True
        except BaseException as error:
            nested = getattr(error, "teardown", None)
            if isinstance(nested, _Teardown) and nested.count:
                self.merge(nested)
                self.resource_stop |= _resource_stop(error)
            else:
                self.record(reason, error)
            return False

    def report(self):
        return {"failure_count": self.count, "first_reason": self.reasons[0],
                "reasons": self.reasons[:min(self.count, len(self.reasons))],
                "omitted_count": max(0, self.count-len(self.reasons)), "resource_stop": self.resource_stop}


def _preserve_teardown(primary, teardown):
    if not teardown.count:
        return
    if primary is None:
        primary = _Failure("owned_teardown_failed")
        primary.teardown = teardown
        raise primary
    teardown.resource_stop |= _resource_stop(primary)
    existing = getattr(primary, "teardown", None)
    if isinstance(existing, _Teardown):
        existing.merge(teardown)
    else:
        primary.teardown = teardown


def _close_call(operation, reason, primary=None, teardown=None):
    collector = _Teardown() if teardown is None else teardown
    confirmed = collector.attempt(reason, operation)
    if teardown is None:
        _preserve_teardown(primary, collector)
    return confirmed


class _Closing:
    """The with statement supplies only this body's exception, never ambient state."""
    def __init__(self, close):
        self.close, self.teardown = close, _Teardown()

    def __enter__(self):
        return self

    def __exit__(self, kind, primary, traceback):
        self.teardown.attempt("bound_handle_close", self.close)
        _preserve_teardown(primary, self.teardown)
        return False


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    _need(type(raw) is bytes and len(raw) <= _LIMIT, "ipc_size")
    def pairs(rows):
        result = {}
        for key, value in rows:
            _need(key not in result, "ipc_duplicate")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(_Failure("ipc_number")))
        _need(_canonical(value) == raw, "ipc_canonical")
        return value
    except _Failure:
        raise
    except (ValueError, TypeError, RecursionError):
        raise _Failure("ipc_json") from None


class _Luid(C.Structure):
    _fields_ = [("low", D), ("high", C.c_int32)]


class _SidAttr(C.Structure):
    _fields_ = [("sid", H), ("attributes", D)]


class _Groups(C.Structure):
    _fields_ = [("count", D), ("rows", _SidAttr * 1)]


class _Privilege(C.Structure):
    _fields_ = [("luid", _Luid), ("attributes", D)]


class _Privileges(C.Structure):
    _fields_ = [("count", D), ("rows", _Privilege * 1)]


class _Statistics(C.Structure):
    _fields_ = [("token", _Luid), ("authentication", _Luid), ("expiration", C.c_int64),
               ("type", D), ("level", D), ("charged", D), ("available", D),
               ("groups", D), ("privileges", D), ("modified", _Luid)]


class _SA(C.Structure):
    _fields_ = [("length", D), ("descriptor", H), ("inherit", B)]


class _FileInfo(C.Structure):
    _pack_ = 4
    _fields_ = [("attributes", D), ("creation", C.c_uint64), ("access", C.c_uint64),
               ("write", C.c_uint64), ("volume", D), ("size_high", D), ("size_low", D),
               ("links", D), ("index_high", D), ("index_low", D)]


class _FileId(C.Structure):
    _fields_ = [("volume", C.c_uint64), ("identifier", C.c_ubyte * 16)]


class _Mapping(C.Structure):
    _fields_ = [("read", D), ("write", D), ("execute", D), ("all", D)]


class _Startup(C.Structure):
    _fields_ = [("cb", D), ("reserved", C.c_wchar_p), ("desktop", C.c_wchar_p), ("title", C.c_wchar_p),
               *[(x, D) for x in ("x", "y", "xsize", "ysize", "xchars", "ychars", "fill", "flags")],
               ("show", C.c_uint16), ("reserved2_size", C.c_uint16), ("reserved2", H),
               ("stdin", H), ("stdout", H), ("stderr", H)]


class _Process(C.Structure):
    _fields_ = [("process", H), ("thread", H), ("pid", D), ("tid", D)]


class _Memory(C.Structure):
    _fields_ = [("cb", D), ("faults", D), *[(x, C.c_size_t) for x in (
        "peak_working", "working", "peak_paged", "paged", "peak_nonpaged", "nonpaged",
        "pagefile", "peak_pagefile", "private")]]


class _Performance(C.Structure):
    _fields_ = [("cb", D), *[(x, C.c_size_t) for x in ("commit", "limit", "peak_commit", "physical",
        "available", "cache", "kernel", "paged", "nonpaged", "page_size")],
        ("handles", D), ("processes", D), ("threads", D)]


class _IoStatus(C.Structure):
    _fields_ = [("status_or_pointer", H), ("information", C.c_size_t)]


class _BasicInfo(C.Structure):
    _fields_ = [(x, C.c_int64) for x in ("creation", "access", "write", "change")] + [("attributes", D)]


class _StreamInfo(C.Structure):
    _fields_ = [("size", C.c_int64), ("name", C.c_wchar * 296)]


def _api():
    _need(os.name == "nt", "unsupported_platform")
    return _Win()


class _Win:
    def __init__(self):
        _need(os.name == "nt", "unsupported_platform")
        k, a, p = C.WinDLL("kernel32", use_last_error=True), C.WinDLL("advapi32", use_last_error=True), C.WinDLL("psapi", use_last_error=True)
        self.k, self.a, self.p = k, a, p
        def bind(dll, name, result, *args):
            fn = getattr(dll, name)
            fn.restype, fn.argtypes = result, list(args)
        bind(k, "CloseHandle", B, H)
        bind(k, "LocalFree", H, H)
        bind(k, "GetCurrentProcess", H)
        bind(k, "GetCurrentThread", H)
        try:
            bind(k, "GetTempPath2W", D, D, P(C.c_wchar))
        except AttributeError:
            raise _Failure("temp_path_api_unavailable") from None
        bind(k, "CreateFileW", H, C.c_wchar_p, D, D, P(_SA), D, D, H)
        bind(k, "CreateDirectoryW", B, C.c_wchar_p, P(_SA))
        bind(k, "GetFileInformationByHandle", B, H, P(_FileInfo))
        bind(k, "GetFileInformationByHandleEx", B, H, D, H, D)
        bind(k, "GetFinalPathNameByHandleW", D, H, C.c_wchar_p, D, D)
        bind(k, "GetVolumeInformationByHandleW", B, H, C.c_wchar_p, D, P(D), P(D), P(D), C.c_wchar_p, D)
        bind(k, "GetDriveTypeW", D, C.c_wchar_p)
        bind(k, "QueryDosDeviceW", D, C.c_wchar_p, C.c_wchar_p, D)
        bind(k, "ReadFile", B, H, H, D, P(D), H)
        bind(k, "PeekNamedPipe", B, H, H, D, P(D), P(D), P(D))
        bind(k, "WriteFile", B, H, H, D, P(D), H)
        bind(k, "SetFilePointerEx", B, H, C.c_int64, H, D)
        bind(k, "FlushFileBuffers", B, H)
        bind(k, "GetHandleInformation", B, H, P(D))
        bind(k, "GetStdHandle", H, D)
        bind(k, "GetProcessId", D, H)
        bind(k, "GetProcessTimes", B, H, P(C.c_uint64), P(C.c_uint64), P(C.c_uint64), P(C.c_uint64))
        bind(k, "QueryFullProcessImageNameW", B, H, D, C.c_wchar_p, P(D))
        bind(k, "ResumeThread", D, H)
        bind(k, "WaitForSingleObject", D, H, D)
        bind(k, "GetExitCodeProcess", B, H, P(D))
        bind(k, "TerminateProcess", B, H, D)
        bind(k, "SetFileInformationByHandle", B, H, D, H, D)
        bind(k, "SetFileTime", B, H, H, H, H)
        bind(k, "SetEndOfFile", B, H)
        bind(k, "DeleteFileW", B, C.c_wchar_p)
        bind(k, "RemoveDirectoryW", B, C.c_wchar_p)
        bind(k, "MoveFileW", B, C.c_wchar_p, C.c_wchar_p)
        bind(k, "MoveFileExW", B, C.c_wchar_p, C.c_wchar_p, D)
        bind(k, "FindFirstStreamW", H, C.c_wchar_p, D, P(_StreamInfo), D)
        bind(k, "FindNextStreamW", B, H, P(_StreamInfo))
        bind(k, "FindClose", B, H)
        bind(a, "OpenProcessToken", B, H, D, P(H))
        bind(a, "OpenThreadToken", B, H, D, B, P(H))
        bind(a, "GetTokenInformation", B, H, D, H, D, P(D))
        bind(a, "ConvertSidToStringSidW", B, H, P(H))
        bind(a, "ConvertStringSidToSidW", B, C.c_wchar_p, P(H))
        bind(a, "LookupPrivilegeNameW", B, C.c_wchar_p, P(_Luid), C.c_wchar_p, P(D))
        bind(a, "CreateRestrictedToken", B, H, D, D, P(_SidAttr), D, H, D, P(_SidAttr), P(H))
        bind(a, "DuplicateTokenEx", B, H, D, H, D, D, P(H))
        bind(a, "CreateProcessAsUserW", B, H, C.c_wchar_p, C.c_wchar_p, H, H, B, D, H, C.c_wchar_p, P(_Startup), P(_Process))
        bind(a, "ConvertStringSecurityDescriptorToSecurityDescriptorW", B, C.c_wchar_p, D, P(H), H)
        bind(a, "GetSecurityDescriptorDacl", B, H, P(B), P(H), P(B))
        bind(a, "GetSecurityDescriptorControl", B, H, P(C.c_uint16), P(D))
        bind(a, "GetSecurityInfo", D, H, D, D, P(H), P(H), P(H), P(H), P(H))
        bind(a, "SetSecurityInfo", D, H, D, D, H, H, H, H)
        bind(a, "GetAce", B, H, D, P(H))
        bind(a, "MapGenericMask", None, P(D), P(_Mapping))
        bind(a, "AccessCheck", B, H, H, D, P(_Mapping), H, P(D), P(D), P(B))
        bind(p, "GetProcessMemoryInfo", B, H, P(_Memory), D)
        bind(p, "GetPerformanceInfo", B, P(_Performance), D)
        self.n = C.WinDLL("ntdll", use_last_error=True)
        bind(self.n, "NtSetEaFile", C.c_int32, H, P(_IoStatus), H, D)

    def call(self, ok, reason):
        if not ok:
            raise _Failure(reason, C.get_last_error())

    def close(self, handle, *, primary=None, teardown=None):
        if handle:
            return _close_call(lambda: self.call(self.k.CloseHandle(handle), "handle_close"),
                               "owned_handle_close", primary, teardown)
        return True

    def sid(self, pointer):
        value = H()
        self.call(self.a.ConvertSidToStringSidW(pointer, C.byref(value)), "sid_query")
        try:
            return C.wstring_at(value)
        finally:
            self.k.LocalFree(value)

    def token(self, process, access=0xA):
        value = H()
        self.call(self.a.OpenProcessToken(process, access, C.byref(value)), "token_open")
        return value.value

    def no_impersonation(self):
        token = H()
        if self.a.OpenThreadToken(self.k.GetCurrentThread(), 8, True, C.byref(token)):
            self.close(token)
            raise _Failure("unexpected_impersonation")
        _need(C.get_last_error() == 1008, "thread_token_query")

    def query(self, token, kind):
        size = D()
        ok = self.a.GetTokenInformation(token, kind, None, 0, C.byref(size))
        _need(not ok and C.get_last_error() in (24, 122) and 0 < size.value <= 65536, "token_query_size")
        for _ in range(2):
            buf = C.create_string_buffer(size.value)
            if self.a.GetTokenInformation(token, kind, buf, len(buf), C.byref(size)):
                return buf
            _need(C.get_last_error() == 122 and len(buf) < size.value <= 65536, "token_query")
        raise _Failure("token_query_changed")

    def profile(self, token):
        def groups(kind):
            buf = self.query(token, kind)
            count = D.from_buffer(buf).value
            _need(count <= 1024 and _Groups.rows.offset + count*C.sizeof(_SidAttr) <= len(buf), "token_groups_size")
            rows = (_SidAttr*count).from_buffer(buf, _Groups.rows.offset)
            result = sorted([[self.sid(x.sid), x.attributes] for x in rows])
            _need(len({x[0] for x in result}) == len(result), "token_duplicate_sid")
            return result
        def integer(kind):
            raw = self.query(token, kind).raw
            _need(len(raw) in (1, 4), "token_integer_size")
            return int.from_bytes(raw, "little")
        user = self.query(token, 1)
        integrity = self.query(token, 25)
        privileges = self.query(token, 3)
        count = D.from_buffer(privileges).value
        _need(count <= 256 and _Privileges.rows.offset + count*C.sizeof(_Privilege) <= len(privileges), "token_privileges_size")
        priv = []
        for row in (_Privilege*count).from_buffer(privileges, _Privileges.rows.offset):
            name, size = C.create_unicode_buffer(256), D(256)
            self.call(self.a.LookupPrivilegeNameW(None, C.byref(row.luid), name, C.byref(size)), "privilege_name")
            priv.append([name.value, row.attributes])
        stats = _Statistics.from_buffer(self.query(token, 10))
        def luid(value):
            return f"{value.high & 0xffffffff:08x}{value.low:08x}"
        return {"user": [self.sid(_SidAttr.from_buffer(user).sid), _SidAttr.from_buffer(user).attributes],
                "groups": groups(2), "privileges": sorted(priv), "restricted": groups(11),
                "type": integer(8), "integrity": self.sid(_SidAttr.from_buffer(integrity).sid),
                "elevated": integer(20), "elevation_type": integer(18), "session": integer(12),
                "has_restrictions": integer(21), "token_id": luid(stats.token),
                "modified_id": luid(stats.modified), "authentication_id": luid(stats.authentication)}

    def restricted(self, parent, profile):
        _validate_parent(profile)
        allocations = []
        try:
            def sid(value):
                out = H()
                self.call(self.a.ConvertStringSidToSidW(value, C.byref(out)), "sid_create")
                allocations.append(out)
                return out
            disable = (_SidAttr * len([g for g in profile["groups"] if g[0] in _PRIVILEGED]))()
            for row, group in zip(disable, (g for g in profile["groups"] if g[0] in _PRIVILEGED)):
                row.sid, row.attributes = sid(group[0]).value, 0
            restrict = (_SidAttr * 1)(_SidAttr(sid(_RC).value, 0))
            result = H()
            self.call(self.a.CreateRestrictedToken(parent, 9, len(disable), disable, 0, None, 1, restrict, C.byref(result)), "restricted_token_create")
            try:
                _validate_restricted(profile, self.profile(result))
                return result.value
            except BaseException as error:
                self.close(result, primary=error)
                raise
        finally:
            for value in allocations:
                self.k.LocalFree(value)

    def impersonation(self, primary):
        value = H()
        self.call(self.a.DuplicateTokenEx(primary, 8, None, 2, 2, C.byref(value)), "token_duplicate")
        return value.value

    def descriptor(self, sddl):
        value = H()
        self.call(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(value), None), "sd_create")
        return value

    def security(self, handle):
        owner, group, dacl, sacl, sd = H(), H(), H(), H(), H()
        # LABEL_SECURITY_INFORMATION is read-only and does not request audit SACL
        # privilege. A DACL denial must not actually be a mandatory-integrity denial.
        error = self.a.GetSecurityInfo(handle, 1, 0x17, C.byref(owner), C.byref(group), C.byref(dacl), C.byref(sacl), C.byref(sd))
        if error:
            raise _Failure("sd_query", error)
        try:
            _need(owner.value and group.value and dacl.value, "sd_null")
            control, revision = C.c_uint16(), D()
            self.call(self.a.GetSecurityDescriptorControl(sd, C.byref(control), C.byref(revision)), "sd_control")
            _need(control.value & 0x1000 and control.value & 4, "sd_not_protected")
            acl_header = C.string_at(dacl, 8)
            count = int.from_bytes(acl_header[4:6], "little")
            _need(0 < count <= 32, "sd_ace_count")
            aces = []
            for i in range(count):
                ace = H()
                self.call(self.a.GetAce(dacl, i, C.byref(ace)), "sd_ace")
                header = C.string_at(ace, 8)
                _need(header[0] in (0, 1) and header[1] == 0, "sd_inherited_or_unknown_ace")
                aces.append([header[0], header[1], int.from_bytes(header[4:8], "little"), self.sid(ace.value+8)])
            integrity, mandatory_policy = "S-1-16-8192", 1  # No label means medium integrity.
            if sacl.value:
                count = int.from_bytes(C.string_at(sacl, 8)[4:6], "little")
                _need(count <= 1, "sd_label_count")
                if count:
                    ace = H()
                    self.call(self.a.GetAce(sacl, 0, C.byref(ace)), "sd_label_ace")
                    raw = C.string_at(ace, 8)
                    _need(raw[0] == 17, "sd_label_type")
                    integrity = self.sid(ace.value+8)
                    mandatory_policy = int.from_bytes(raw[4:8], "little")
            _need(integrity in ("S-1-16-0", "S-1-16-4096", "S-1-16-8192") and mandatory_policy & ~7 == 0,
                  "sd_mandatory_integrity")
            return {"protected": True, "owner": self.sid(owner), "group": self.sid(group), "aces": aces,
                    "integrity": integrity, "mandatory_policy": mandatory_policy}
        finally:
            self.k.LocalFree(sd)

    def access(self, handle, token, desired):
        sd, owner, group = H(), H(), H()
        error = self.a.GetSecurityInfo(handle, 1, 7, C.byref(owner), C.byref(group), None, None, C.byref(sd))
        if error:
            raise _Failure("access_sd", error)
        try:
            _need(owner.value and group.value, "access_sd_owner")
            mapping, mask = _Mapping(0x120089, 0x120116, 0x1200a0, 0x1f01ff), D(desired)
            self.a.MapGenericMask(C.byref(mask), C.byref(mapping))
            size, granted, status = D(), D(), B()
            C.set_last_error(0)
            ok = self.a.AccessCheck(sd, token, mask, C.byref(mapping), None, C.byref(size), C.byref(granted), C.byref(status))
            _need(not ok and C.get_last_error() == 122 and 0 < size.value <= 65536, "access_buffer_size")
            for _ in range(2):
                buf = C.create_string_buffer(size.value)
                C.set_last_error(0)
                ok = self.a.AccessCheck(sd, token, mask, C.byref(mapping), buf, C.byref(size), C.byref(granted), C.byref(status))
                error = C.get_last_error()
                if ok:
                    return {"api_success": True, "access_status": bool(status.value), "granted": granted.value,
                            "mask": mask.value, "winerror": error, "privileges_used": D.from_buffer(buf).value}
                _need(error == 122 and len(buf) < size.value <= 65536, "access_api_failure")
            raise _Failure("access_buffer_changed")
        finally:
            self.k.LocalFree(sd)

    def resources(self, process):
        memory, performance = _Memory(), _Performance()
        memory.cb, performance.cb = C.sizeof(memory), C.sizeof(performance)
        self.call(self.p.GetProcessMemoryInfo(process, C.byref(memory), memory.cb), "memory_query")
        self.call(self.p.GetPerformanceInfo(C.byref(performance), performance.cb), "commit_query")
        return {"peak_working_bytes": memory.peak_working, "private_bytes": memory.private,
                "peak_pagefile_bytes": memory.peak_pagefile, "system_commit_bytes": performance.commit*performance.page_size,
                "system_commit_limit_bytes": performance.limit*performance.page_size}


def _validate_parent(p):
    _need(p["type"] == 1 and p["elevated"] == 0 and not p["restricted"]
          and (p["elevation_type"], p["has_restrictions"]) in ((1, 0), (3, 1)),
          "parent_token_policy")
    _need(p["integrity"] == "S-1-16-8192", "parent_integrity_policy")
    _need(all(attrs & 0x10 and not attrs & 4 for sid, attrs in p["groups"] if sid in _PRIVILEGED), "parent_privileged_group")


def _shape(p):
    return {k: v for k, v in p.items() if k not in {"token_id", "modified_id", "type"}}


def _validate_restricted(parent, child):
    _need(child["type"] == 1 and child["elevated"] == 0 and child["has_restrictions"] == 1, "restricted_policy")
    _need(child["user"] == parent["user"] and child["authentication_id"] == parent["authentication_id"]
          and child["session"] == parent["session"] and child["integrity"] == parent["integrity"], "restricted_identity")
    _need(child["token_id"] != parent["token_id"], "restricted_same_token")
    _need([g[0] for g in child["restricted"]] == [_RC], "restricted_sids")
    expected = [[sid, (attrs | 0x10) & ~6 if sid in _PRIVILEGED else attrs] for sid, attrs in parent["groups"]]
    _need(child["groups"] == expected, "restricted_groups")
    _need(all(name == "SeChangeNotifyPrivilege" for name, attrs in child["privileges"]), "restricted_privileges")


def _lexical(path):
    text = str(path)
    _need(path.is_absolute() and re.match(r"^[A-Za-z]:[\\/]", text) and not text.startswith("\\\\"), "path_local")
    _need(":" not in text[2:] and all(x not in (".", "..") and not x.endswith((" ", ".")) for x in path.parts[1:]), "path_alias")
    _need(not any(re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", x.split(".")[0]) for x in path.parts[1:]), "path_device")


def _temporary_path(api):
    # GetTempPath2W only retrieves a candidate: it does not test existence or
    # access by creating a probe file. No fallback or candidate/cache probing.
    # https://learn.microsoft.com/windows/win32/api/fileapi/nf-fileapi-gettemppath2w
    buffer = C.create_unicode_buffer(32768)
    size = api.k.GetTempPath2W(len(buffer), buffer)
    _need(0 < size < len(buffer), "temp_path_query")
    value = buffer.value
    try:
        units = len(value.encode("utf-16-le", errors="strict")) // 2
    except UnicodeEncodeError:
        raise _Failure("temp_path_result") from None
    _need(units == size and value.endswith("\\"), "temp_path_result")
    path = Path(value)
    _lexical(path)
    return path  # Untrusted until the caller's existing ancestry/handle checks.


class _Bound:
    def __init__(self, api, path, *, directory, access=0x20081, creation=3, sd=None, share=3):
        _lexical(path)
        self.api, self.path, self.directory, self.handle = api, path, directory, None
        sa = _SA(C.sizeof(_SA), sd, False) if sd else None
        h = api.k.CreateFileW(str(path), access, share, C.byref(sa) if sa else None, creation,
                             0x00200000 | (0x02000000 if directory else 0), None)
        if h == C.c_void_p(-1).value:
            raise _Failure("object_open", C.get_last_error())
        self.handle = h
        try:
            self.identity = self.observe()
            self.check()
        except BaseException as error:
            self.close(primary=error)
            raise

    def observe(self):
        api, info, ident = self.api, _FileInfo(), _FileId()
        api.call(api.k.GetFileInformationByHandle(self.handle, C.byref(info)), "file_info")
        api.call(api.k.GetFileInformationByHandleEx(self.handle, 18, C.byref(ident), C.sizeof(ident)), "file_id")
        _need(not info.attributes & 0x400 and bool(info.attributes & 16) == self.directory, "object_reparse_or_type")
        _need(self.directory or info.links == 1, "object_hardlink")
        _need(self.directory or not info.attributes & 1, "object_readonly")
        final = C.create_unicode_buffer(32768)
        n = api.k.GetFinalPathNameByHandleW(self.handle, final, len(final), 0)
        _need(0 < n < len(final), "object_final_path")
        value = final.value
        _need(value.startswith("\\\\?\\") and not value.startswith("\\\\?\\UNC\\"), "object_remote")
        _need(value[4:].casefold() == str(self.path).casefold(), "object_path_changed")
        filesystem, serial, maximum, flags = C.create_unicode_buffer(32), D(), D(), D()
        api.call(api.k.GetVolumeInformationByHandleW(self.handle, None, 0, C.byref(serial), C.byref(maximum),
                                                    C.byref(flags), filesystem, len(filesystem)), "volume_query")
        _need(filesystem.value == "NTFS" and api.k.GetDriveTypeW(self.path.anchor) == 3, "volume_not_local_ntfs")
        device = C.create_unicode_buffer(32768)
        api.call(api.k.QueryDosDeviceW(self.path.drive, device, len(device)), "drive_query")
        _need(re.fullmatch(r"\\Device\\HarddiskVolume[0-9]+", device.value) is not None, "mapped_drive")
        _need(any(ident.identifier), "object_id_missing")
        inherit = D()
        api.call(api.k.GetHandleInformation(self.handle, C.byref(inherit)), "handle_flags")
        _need(not inherit.value & 1, "handle_inheritable")
        return {"volume": ident.volume, "file_id": bytes(ident.identifier).hex(), "directory": self.directory,
                "links": info.links, "attributes": info.attributes}

    def check(self):
        observed = self.observe()
        _need(observed == self.identity, "object_identity_changed")
        meta = self.path.lstat()
        _need(not stat.S_ISLNK(meta.st_mode) and not getattr(meta, "st_file_attributes", 0) & 0x400, "path_reparse")
        # Reopen through the name, compare its native ID to the retained handle.
        h = self.api.k.CreateFileW(str(self.path), 0x80, 7, None, 3, 0x00200000 | (0x02000000 if self.directory else 0), None)
        if h == C.c_void_p(-1).value:
            raise _Failure("identity_reopen", C.get_last_error())
        with _Closing(lambda: self.api.close(h)):
            ident = _FileId()
            self.api.call(self.api.k.GetFileInformationByHandleEx(h, 18, C.byref(ident), C.sizeof(ident)), "identity_requery")
            _need(ident.volume == observed["volume"] and bytes(ident.identifier).hex() == observed["file_id"], "named_handle_mismatch")
        return observed

    def read(self):
        self.check()
        self.api.call(self.api.k.SetFilePointerEx(self.handle, 0, None, 0), "read_seek")
        output = bytearray()
        while True:
            buf, size = C.create_string_buffer(65536), D()
            self.api.call(self.api.k.ReadFile(self.handle, buf, len(buf), C.byref(size), None), "read_file")
            if not size.value:
                break
            output.extend(buf.raw[:size.value])
            _need(len(output) <= _LIMIT, "file_size")
        self.check()
        return bytes(output)

    def streams(self):
        self.check()
        item = _StreamInfo()
        names = []
        primary, teardown = None, _Teardown()
        handle = self.api.k.FindFirstStreamW(str(self.path), 0, C.byref(item), 0)
        if handle == C.c_void_p(-1).value:
            _need(self.directory and C.get_last_error() == 38, "stream_query")
        else:
            try:
                while True:
                    names.append(item.name)
                    _need(len(names) <= 1, "alternate_stream")
                    if not self.api.k.FindNextStreamW(handle, C.byref(item)):
                        _need(C.get_last_error() == 38, "stream_next")
                        break
            except BaseException as error:
                primary = error
                raise
            finally:
                teardown.attempt("stream_close", lambda: self.api.call(self.api.k.FindClose(handle), "stream_close"))
                _preserve_teardown(primary, teardown)
        _need(names == ([] if self.directory else ["::$DATA"]), "alternate_stream")
        self.check()

    def write(self, raw):
        _need(type(raw) is bytes and len(raw) <= _LIMIT, "write_size")
        size = D()
        self.api.call(self.api.k.WriteFile(self.handle, raw, len(raw), C.byref(size), None), "write_file")
        _need(size.value == len(raw), "partial_write")
        self.api.call(self.api.k.FlushFileBuffers(self.handle), "flush_file")
        self.check()

    def freeze(self, sddl):
        before = self.check()
        descriptor = self.api.descriptor(sddl)
        try:
            present, defaulted, acl = B(), B(), H()
            self.api.call(self.api.a.GetSecurityDescriptorDacl(descriptor, C.byref(present), C.byref(acl), C.byref(defaulted)), "freeze_dacl")
            _need(present.value and acl.value, "freeze_null")
            error = self.api.a.SetSecurityInfo(self.handle, 1, 0x80000004, None, None, acl, None)
            if error:
                raise _Failure("freeze_set", error)
        finally:
            self.api.k.LocalFree(descriptor)
        result = self.api.security(self.handle)
        _need(self.check() == before, "freeze_identity")
        return result

    def close(self, *, primary=None, teardown=None):
        if self.handle is not None:
            if not _close_call(lambda: _need(self.api.close(self.handle) is not False, "handle_close"),
                               "bound_handle_close", primary, teardown):
                return False
            self.handle = None  # Retain identity until CloseHandle is confirmed.
        return True


def _dacl(user, mode, directory):
    deny = (0x10156 if directory else 0x10116) if mode == "frozen" else 0
    rows = ([[1, 0, deny, "S-1-1-0"]] if deny else [])
    rows += [[0, 0, 0x1f01ff, sid] for sid in (user, "S-1-5-18", "S-1-5-32-544")]
    if mode in ("control", "frozen"):
        rows.append([0, 0, 0x120089 if mode == "frozen" else 0x1f01ff, _RC])
    sddl = "D:P" + "".join(f"({'D' if kind else 'A'};;0x{mask:x};;;{sid})" for kind, _, mask, sid in rows)
    return sddl, rows


def _verify_sd(sd, user, mode, directory):
    _need(sd["protected"] is True and sd["owner"] == user and bool(sd["group"])
          and sd["aces"] == _dacl(user, mode, directory)[1], "sd_policy_mismatch")


def _read_source(api, path):
    guards, bound, primary, teardown = [], None, None, _Teardown()
    try:
        for ancestor in reversed(path.parents):
            guards.append(_Bound(api, ancestor, directory=True))
        bound = _Bound(api, path, directory=False, share=1)
        # Runtime DLLs exceed the small fixture bound. Hash streaming through
        # the retained descriptor, without permitting arbitrary large IPC.
        digest, count = hashlib.sha256(), 0
        while True:
            buf, size = C.create_string_buffer(65536), D()
            api.call(api.k.ReadFile(bound.handle, buf, len(buf), C.byref(size), None), "source_read")
            if not size.value:
                break
            digest.update(buf.raw[:size.value])
            count += size.value
            _need(count <= 128*1024*1024, "source_size")
        bound.check()
        return digest.hexdigest(), count
    except BaseException as error:
        primary = error
        raise
    finally:
        if bound is not None:
            teardown.attempt("source_handle_close", bound.close)
        for guard in reversed(guards):
            teardown.attempt("source_guard_close", guard.close)
        _preserve_teardown(primary, teardown)


def _runtime():
    _need(os.name == "nt" and sys.version_info[:3] == (3, 14, 0) and C.sizeof(H) == 8, "runtime_unavailable")
    import winreg
    import platform
    import sysconfig
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
        values = [winreg.QueryValueEx(key, name)[0] for name in ("CurrentBuildNumber", "UBR", "EditionID", "DisplayVersion")]
    _need(values == ["26200", 9168, "Professional", "25H2"] and platform.machine() == "AMD64"
          and platform.python_compiler() == "MSC v.1944 64 bit (AMD64)" and sys._git == ("CPython", "tags/v3.14.0", "ebf955d")
          and not sysconfig.get_config_var("Py_GIL_DISABLED"), "runtime_pin")
    api = _api()
    _need(_read_source(api, Path(sys.executable))[0] == _EXE_SHA
          and _read_source(api, Path(sys.base_prefix)/"python314.dll")[0] == _DLL_SHA, "runtime_hash")
    return {"build": "10.0.26200.9168", "python": "3.14.0", "exe_sha256": _EXE_SHA, "dll_sha256": _DLL_SHA}


def _source_bytes(api, path):
    guards, bound, primary, teardown = [], None, None, _Teardown()
    try:
        for ancestor in reversed(path.parents):
            guards.append(_Bound(api, ancestor, directory=True))
        bound = _Bound(api, path, directory=False, share=1)
        info = _FileInfo()
        api.call(api.k.GetFileInformationByHandle(bound.handle, C.byref(info)), "source_size_query")
        size = (info.size_high << 32) | info.size_low
        _need(size <= _LIMIT, "source_size")  # Before any content read/allocation.
        raw = bound.read()  # Independently bounded; retained identity checked.
        _need(len(raw) == size, "source_size_changed")
        return raw
    except BaseException as error:
        primary = error
        raise
    finally:
        if bound is not None:
            teardown.attempt("source_handle_close", bound.close)
        for guard in reversed(guards):
            teardown.attempt("source_guard_close", guard.close)
        _preserve_teardown(primary, teardown)


def _index_bytes(api, path, environment):
    import msvcrt
    primary, teardown = None, _Teardown()
    # One unbuffered stdout reader, no competing pipe reader, no stderr capture.
    # Peek only queries available bytes; read never waits for a full-sized chunk.
    process = subprocess.Popen(
        ["git", "--no-pager", "-c", "core.fsmonitor=false", "show", ":"+path.relative_to(_ROOT).as_posix()],
        cwd=_ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, bufsize=0, close_fds=True, creationflags=0x08000000)
    try:
        handle = msvcrt.get_osfhandle(process.stdout.fileno())
        deadline, output = time.monotonic()+10, bytearray()
        while True:
            _need(time.monotonic() < deadline, "source_index_timeout")
            exited = process.poll() is not None
            available = D()
            ok = api.k.PeekNamedPipe(handle, None, 0, None, C.byref(available), None)
            if not ok:
                _need(C.get_last_error() == 109, "source_index_pipe")  # Broken pipe / EOF.
                break
            if available.value:
                _need(available.value <= _LIMIT-len(output), "source_index_size")
                raw = process.stdout.read(min(available.value, 65536))
                _need(raw and len(raw) <= available.value, "source_index_pipe")
                output.extend(raw)
            elif exited:
                break
            else:
                time.sleep(0.005)
        _need(process.wait(timeout=max(0.001, deadline-time.monotonic())) == 0, "source_index_bytes")
        return bytes(output)
    except subprocess.TimeoutExpired:
        primary = _Failure("source_index_timeout")
        raise primary from None
    except BaseException as error:
        primary = error
        raise
    finally:
        # Only this git child: no filesystem fallback or diagnostic reread.
        exited = False
        try:
            exited = process.poll() is not None
        except BaseException as error:
            teardown.record("index_process_poll", error)
        if not exited:
            teardown.attempt("index_process_kill", process.kill)
        teardown.attempt("index_process_wait", lambda: _need(type(process.wait(timeout=5)) is int, "index_process_wait"))
        teardown.attempt("index_pipe_close", process.stdout.close)
        _preserve_teardown(primary, teardown)


def _source_pin():
    rows = []
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
    for path in (_SOURCE, _CHILD):
        api = _api()
        raw = _source_bytes(api, path)
        _need(_index_bytes(api, path, environment) == raw, "source_index_bytes")
        rows.append({"path": path.relative_to(_ROOT).as_posix(), "sha256": _sha(raw), "bytes": len(raw)})
    return rows


_MAX_OBJECTS = 32
_MAX_FILE_BYTES = 1024 * 1024
_MAX_TOTAL_BYTES = 4 * _MAX_FILE_BYTES
_MAX_METADATA_BYTES = 64 * 1024


class CleanupEvidenceError(ValueError):
    def __init__(self):
        super().__init__("cleanup_evidence_contract")


def _require(condition):
    if not condition:
        raise CleanupEvidenceError()


def _metadata(value):
    # Only captured canonical bytes cross this boundary. No arbitrary serializers
    # or callbacks may execute after a native mutation has begun.
    _require(type(value) is bytes and 0 < len(value) <= _MAX_METADATA_BYTES)
    return value


@dataclass(frozen=True, repr=False)
class CapturedObject:
    name: str
    directory: bool
    identity: bytes = field(repr=False)
    security: bytes = field(repr=False)
    cleanup_security: bytes = field(repr=False)
    content: bytes = field(repr=False)

    def __post_init__(self):
        _require(type(self.name) is str and len(self.name) <= 128)
        _require(self.name == "" or re.fullmatch(r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*", self.name)
                 and all(part not in (".", "..") for part in self.name.split("/")))
        _require(type(self.directory) is bool)
        _metadata(self.identity)
        _metadata(self.security)
        _metadata(self.cleanup_security)
        _require(type(self.content) is bytes and len(self.content) <= _MAX_FILE_BYTES)
        _require(not self.directory or not self.content)

    def __repr__(self):
        return "CapturedObject(<private evidence>)"


@dataclass(repr=False)
class _Progress:
    acl: str = "unchanged"
    deletion: str = "not_started"
    close: str = "not_started"
    failed_operation: str | None = None


class CleanupJournal:
    """One attempt, no retries; mark pending BEFORE each external mutation.

    A failed native call can have side effects. 'unknown' preserves that fact.
    A successful delete disposition and close do not prove name absence.
    Full snapshots are retained in memory only, with no crash-durability claim.
    """

    def __init__(self, objects, operations):
        _require(type(objects) is tuple and 0 < len(objects) <= _MAX_OBJECTS)
        _require(all(type(item) is CapturedObject for item in objects))
        _require(type(operations) is bytes and 0 < len(operations) <= _MAX_FILE_BYTES)
        names = {item.name for item in objects}
        _require(len(names) == len(objects) and "" in names)
        by_name = {item.name: item for item in objects}
        _require(by_name[""].directory)
        for item in objects:
            if item.name:
                parent = item.name.rpartition("/")[0]
                _require(parent in by_name and by_name[parent].directory)
        _require(sum(len(item.content) for item in objects) <= _MAX_TOTAL_BYTES)
        # Immutable input objects and byte strings cannot alias the mutable native
        # ledger. Allocate every transition slot before exposing this journal.
        self._objects = tuple(sorted(objects, key=lambda item: item.name))
        self._operations = operations
        self._progress = {item.name: _Progress() for item in self._objects}
        inventory = [{"name": item.name, "directory": item.directory,
                      "identity_sha256": _sha(item.identity), "security_sha256": _sha(item.security),
                      "cleanup_security_sha256": _sha(item.cleanup_security),
                      "content_sha256": _sha(item.content), "bytes": len(item.content)}
                     for item in self._objects]
        self._snapshot_digest = _sha(json.dumps(
            {"version": 1, "objects": inventory, "operations_sha256": _sha(operations)},
            sort_keys=True, separators=(",", ":")).encode("ascii"))
        self._status = "prepared"
        self._resource_stop = False
        self._active = None

    def __repr__(self):
        return "CleanupJournal(<private evidence>)"

    @property
    def private_snapshot(self):
        """Explicit in-memory access only; callers must not log this evidence."""
        return self._objects, self._operations

    def _row(self, name):
        _require(type(name) is str and name in self._progress)
        return self._progress[name]

    def begin(self, name, operation):
        _require(self._status in ("prepared", "running") and not self._resource_stop)
        _require(self._active is None and operation in ("acl", "delete", "absence"))
        row = self._row(name)
        if operation == "acl":
            _require(row.acl == "unchanged" and row.deletion == "not_started")
        elif operation == "delete":
            _require(row.acl == "changed" and row.deletion == "not_started")
            # A parent may be deleted only after all its captured descendants
            # have confirmed absence. Unknown/foreign children remain a native
            # preflight concern, and never get added to this journal.
            _require(all(other.deletion == "absent" for child, other in self._progress.items()
                         if child != name and (not name or child.startswith(name + "/"))))
        else:
            _require(row.deletion == "armed" and row.close == "confirmed")
        # Allocate the pair before updating any state; allocation failure leaves
        # the old state intact and the native caller has not started the API yet.
        active = (name, operation)
        if operation == "acl":
            row.acl = "pending"
        elif operation == "delete":
            row.deletion = "pending"
        self._active, self._status = active, "running"

    def confirmed(self):
        _require(self._status == "running" and self._active is not None and not self._resource_stop)
        name, operation = self._active
        row = self._progress[name]
        if operation == "acl":
            row.acl = "changed"  # Caller has verified the new descriptor.
        elif operation == "delete":
            row.deletion = "armed"  # Native disposition accepted, not absence.
        else:
            row.deletion = "absent"  # Caller has positively verified absence.
        self._active = None

    def close_confirmed(self, name):
        # Handle-only teardown is permitted after a failure/resource stop. It
        # never upgrades an uncertain disposition to confirmed absence.
        row = self._row(name)
        _require(self._active is None and row.deletion in ("armed", "unknown") and row.close != "confirmed")
        row.close = "confirmed"

    def failed(self, *, resource_stop=False):
        _require(type(resource_stop) is bool and self._status != "completed")
        if self._active is not None:
            name, operation = self._active
            row = self._progress[name]
            row.failed_operation = operation
            if operation == "acl":
                row.acl = "unknown"
            elif operation == "delete":
                row.deletion = "unknown"
            self._active = None
        self._status = "failed"
        self._resource_stop |= resource_stop

    def close_failed(self, name, *, resource_stop=False):
        _require(type(resource_stop) is bool and self._status != "completed")
        row = self._row(name)
        _require(self._active is None and row.deletion in ("armed", "unknown") and row.close != "confirmed")
        row.close = "unknown"
        self.failed(resource_stop=resource_stop)
        # Keep a prior mutation failure as the primary cause.
        if row.failed_operation is None:
            row.failed_operation = "close"

    def complete(self):
        _require(self._status == "running" and self._active is None and not self._resource_stop)
        _require(all(row.deletion == "absent" for row in self._progress.values()))
        self._status = "completed"

    def report(self):
        """Redacted, bounded memory-only view. It allocates; not an OOM handler.

        Retained bounds describe captured objects only. They are not a fresh
        filesystem inventory and say nothing about foreign objects or disk usage.
        """
        rows, absent_bytes, present_bytes, uncertain_bytes = [], 0, 0, 0
        absent_count = present_count = uncertain_count = 0
        for item in self._objects:
            row = self._progress[item.name]
            size = len(item.content)
            if row.deletion == "absent":
                absent_count += 1
                absent_bytes += size
            elif row.deletion == "not_started":
                present_count += 1
                present_bytes += size
            else:
                uncertain_count += 1
                uncertain_bytes += size
            rows.append({"name": item.name, "acl": row.acl, "deletion": row.deletion,
                         "close": row.close, "failed_operation": row.failed_operation})
        return {"version": 1, "status": self._status, "resource_stop": self._resource_stop,
                "snapshot_sha256": self._snapshot_digest, "objects": rows,
                "captured_objects": len(rows), "captured_bytes": absent_bytes + present_bytes + uncertain_bytes,
                "confirmed_absent_objects": absent_count, "confirmed_absent_bytes": absent_bytes,
                "retained_captured_objects_min": present_count,
                "retained_captured_objects_max": present_count + uncertain_count,
                "retained_captured_bytes_min": present_bytes,
                "retained_captured_bytes_max": present_bytes + uncertain_bytes,
                "unknown_objects": uncertain_count,
                "success_residue_count": 0 if self._status == "completed" else None,
                "report_performed_filesystem_io": False, "native_accepted": False, "formal_permission": False}


class _Fixture:
    def __init__(self, api, user):
        self.api, self.user, self.ledger, self.guards, self.root = api, user, {}, [], None
        self.teardown = _Teardown()
        self.cleanup_journal = None
        self.cleanup_handles = [None] * _MAX_OBJECTS
        # Allocate diagnostics before any owned fixture exists. The retry uses
        # separate collectors so it cannot mutate diagnostics attached to a
        # primary exception during the original close attempt.
        self.cleanup_collectors = [_Teardown() for _ in range(_MAX_OBJECTS)]
        self.cleanup_retry_collectors = [_Teardown() for _ in range(_MAX_OBJECTS)]
        self.cleanup_attempted = False

    def create(self):
        temporary = _temporary_path(self.api)
        for path in reversed((temporary, *temporary.parents)):
            self.guards.append(_Bound(self.api, path, directory=True))
        _need(not any((path/".git").exists() for path in (temporary, *temporary.parents)), "temp_in_repository")
        self.root = temporary/(_PREFIX+uuid.uuid4().hex)
        _need(not self.root.exists(), "temp_collision")
        self.directory("", "private")
        self.guards.append(_Bound(self.api, self.root, directory=True))
        self.directory("control", "control")
        self.directory("frozen", "control")
        for name in ("control/data.bin", "frozen/data.bin"):
            self.file(name, b"B1-control\n", "control")
        self.directory("frozen/empty", "control")

    def path(self, name):
        _need(name == "" or re.fullmatch(r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*", name) and all(p not in (".", "..") for p in name.split("/")), "fixture_name")
        path = self.root/name
        _need(path == self.root or self.root in path.parents, "fixture_escape")
        return path

    def directory(self, name, mode):
        path = self.path(name)
        sd = self.api.descriptor(_dacl(self.user, mode, True)[0])
        try:
            sa = _SA(C.sizeof(_SA), sd, False)
            self.api.call(self.api.k.CreateDirectoryW(str(path), C.byref(sa)), "directory_create")
        finally:
            self.api.k.LocalFree(sd)
        # No claim that CreateDirectoryW + this bind is atomic against a hostile owner.
        bound = _Bound(self.api, path, directory=True, access=0x60081)
        with _Closing(bound.close):
            _need(not list(path.iterdir()), "new_directory_not_empty")
            self.record(name, bound, mode, None)

    def file(self, name, raw, mode):
        sd = self.api.descriptor(_dacl(self.user, mode, False)[0])
        try:
            bound = _Bound(self.api, self.path(name), directory=False, access=0x60083, creation=1, sd=sd)
        finally:
            self.api.k.LocalFree(sd)
        with _Closing(bound.close):
            bound.write(raw)
            _need(bound.read() == raw, "file_readback")
            self.record(name, bound, mode, raw)

    def record(self, name, bound, mode, raw):
        _need(name not in self.ledger, "duplicate_owned_path")
        sd = self.api.security(bound.handle)
        _verify_sd(sd, self.user, mode, bound.directory)
        bound.streams()
        self.ledger[name] = {"identity": bound.check(), "sd": sd, "sha256": None if raw is None else _sha(raw),
                             "bytes": 0 if raw is None else len(raw)}

    def check(self):
        for guard in self.guards:
            guard.check()
        observed = set()
        pending = [""]
        while pending:
            name = pending.pop()
            _need(name in self.ledger, "unknown_fixture_object")
            row = self.ledger[name]
            bound = _Bound(self.api, self.path(name), directory=row["identity"]["directory"])
            with _Closing(bound.close):
                _need(bound.identity == row["identity"] and self.api.security(bound.handle) == row["sd"], "fixture_identity_or_acl")
                bound.streams()
                if bound.directory:
                    pending.extend(((name+"/") if name else "") + x.name for x in bound.path.iterdir())
                else:
                    raw = bound.read()
                    _need(_sha(raw) == row["sha256"] and len(raw) == row["bytes"], "fixture_content")
                observed.add(name)
        _need(observed == set(self.ledger), "fixture_missing_object")

    def freeze(self):
        self.check()
        # Also deny DELETE_CHILD on the bootstrap parent: denying DELETE only on
        # frozen/ is insufficient when its parent still grants delete-child.
        for name in ("frozen/data.bin", "frozen/empty", "frozen", ""):
            row = self.ledger[name]
            bound = _Bound(self.api, self.path(name), directory=row["identity"]["directory"], access=0x60081, share=1)
            with _Closing(bound.close):
                sd = bound.freeze(_dacl(self.user, "frozen", bound.directory)[0])
                _verify_sd(sd, self.user, "frozen", bound.directory)
                row["sd"] = sd
        self.check()  # ALL pins have been closed before launching the child.

    def _cleanup_children(self, bound, expected):
        observed = set()
        with os.scandir(bound.path) as entries:
            for entry in entries:
                _need(len(observed) < _MAX_OBJECTS and entry.name in expected, "cleanup_unknown_child")
                observed.add(entry.name)
        _need(observed == expected, "cleanup_missing_child")

    def _cleanup_close(self, index, primary=None, *, retry=False):
        bound = self.cleanup_handles[index]
        if bound is None:
            return
        local = self.cleanup_retry_collectors[index] if retry else self.cleanup_collectors[index]
        confirmed = bound.close(teardown=local)
        if not confirmed and not local.count:
            local.record("cleanup_handle_close")
        journal = self.cleanup_journal
        # The snapshot order also indexes retained handle ownership.
        if journal is not None:
            name = journal._objects[index].name
            row = journal._progress[name]
            if row.deletion in ("armed", "unknown"):
                if confirmed:
                    journal.close_confirmed(name)
                else:
                    journal.close_failed(name, resource_stop=local.resource_stop)
            elif not confirmed:
                journal.failed(resource_stop=local.resource_stop)
        if confirmed:
            self.cleanup_handles[index] = None
        _preserve_teardown(primary, local)

    def capture_cleanup(self, operations):
        """Complete private snapshot, no ACL changes or deletes. Never retries."""
        _need(not self.cleanup_attempted, "cleanup_retry")
        self.cleanup_attempted = True
        _need(type(operations) is bytes and 0 < len(operations) <= _LIMIT, "cleanup_operations_size")
        _need(0 < len(self.ledger) <= _MAX_OBJECTS, "cleanup_object_count")
        for guard in self.guards:
            guard.check()
        captured, total = [], 0
        names = sorted(self.ledger)
        for index, name in enumerate(names):
            primary = None
            row = self.ledger[name]
            bound = _Bound(self.api, self.path(name), directory=row["identity"]["directory"], share=1)
            self.cleanup_handles[index] = bound
            try:
                sd = self.api.security(bound.handle)
                _need(bound.identity == row["identity"] and sd == row["sd"], "cleanup_capture_identity_or_sd")
                bound.streams()
                raw = b""
                if bound.directory:
                    expected = {child.rpartition("/")[2] for child in names
                                if child and child.rpartition("/")[0] == name}
                    self._cleanup_children(bound, expected)
                else:
                    raw = bound.read()
                    _need(len(raw) == row["bytes"] and _sha(raw) == row["sha256"], "cleanup_capture_bytes")
                total += len(raw)
                _need(total <= _MAX_TOTAL_BYTES, "file_size")
                target = {**sd, "aces": _dacl(self.user, "private", bound.directory)[1]}
                captured.append(CapturedObject(name, bound.directory, _canonical(bound.identity),
                                               _canonical(sd), _canonical(target), raw))
            except BaseException as error:
                primary = error
                raise
            finally:
                self._cleanup_close(index, primary)
        # All allocations and hashes complete BEFORE the first mutation. Caller
        # retains this object even if cleanup or result serialization later fails.
        self.cleanup_journal = CleanupJournal(tuple(captured), operations)
        return self.cleanup_journal

    def _cleanup_verify(self, bound, item, *, private):
        _need(_canonical(bound.check()) == item.identity, "cleanup_identity")
        expected_sd = item.cleanup_security if private else item.security
        _need(_canonical(self.api.security(bound.handle)) == expected_sd, "cleanup_sd")
        bound.streams()
        if bound.directory:
            expected = {child.name.rpartition("/")[2] for child in self.cleanup_journal._objects
                        if child.name and child.name.rpartition("/")[0] == item.name
                        and self.cleanup_journal._progress[child.name].deletion != "absent"}
            self._cleanup_children(bound, expected)
        else:
            _need(bound.read() == item.content, "cleanup_bytes")

    def cleanup(self, *, operations=b'{"scope":"same-parent","operations":"not-supplied"}'):
        journal = self.capture_cleanup(operations)
        # The captured order indexes handle slots; deletion order is bottom-up.
        order = sorted(range(len(journal._objects)),
                       key=lambda i: (journal._objects[i].name.count("/") + bool(journal._objects[i].name),
                                      journal._objects[i].name), reverse=True)
        try:
            for index in order:
                item, primary = journal._objects[index], None
                bound = _Bound(self.api, self.path(item.name), directory=item.directory, access=0x60081, share=1)
                self.cleanup_handles[index] = bound
                try:
                    self._cleanup_verify(bound, item, private=False)
                    journal.begin(item.name, "acl")
                    actual = bound.freeze(_dacl(self.user, "private", item.directory)[0])
                    _need(_canonical(actual) == item.cleanup_security, "cleanup_acl_readback")
                    journal.confirmed()
                except BaseException as error:
                    primary = error
                    journal.failed(resource_stop=_resource_stop(error))
                    raise
                finally:
                    self._cleanup_close(index, primary)
            for index in order:
                item, primary = journal._objects[index], None
                if not item.name:
                    _need(self.guards and self.guards[-1].path == self.root, "cleanup_root_guard")
                    _need(self.guards[-1].close() is True, "cleanup_guard_close")
                    self.guards.pop()  # Only a confirmed close releases ownership.
                bound = _Bound(self.api, self.path(item.name), directory=item.directory, access=0x30081, share=1)
                self.cleanup_handles[index] = bound
                try:
                    self._cleanup_verify(bound, item, private=True)
                    disposition = B(1)
                    journal.begin(item.name, "delete")
                    self.api.call(self.api.k.SetFileInformationByHandle(
                        bound.handle, 4, C.byref(disposition), C.sizeof(disposition)), "cleanup_disposition")
                    journal.confirmed()
                except BaseException as error:
                    primary = error
                    journal.failed(resource_stop=_resource_stop(error))
                    raise
                finally:
                    self._cleanup_close(index, primary)
                journal.begin(item.name, "absence")
                try:
                    self.path(item.name).lstat()
                except FileNotFoundError as error:
                    _need(getattr(error, "winerror", 2) == 2, "cleanup_absence_error")
                else:
                    raise _Failure("cleanup_residue")
                journal.confirmed()
            journal.complete()
        except BaseException as error:
            journal.failed(resource_stop=_resource_stop(error))
            raise
        return journal

    def close(self, *, primary=None, teardown=None):
        if teardown is not None:
            self.teardown = teardown
        for index in range(len(self.cleanup_handles)-1, -1, -1):
            self.teardown.attempt("cleanup_handle_close", lambda: self._cleanup_close(index, retry=True))
        for index in range(len(self.guards)-1, -1, -1):
            guard = self.guards[index]
            if self.teardown.attempt("fixture_guard_close", lambda: _need(guard.close() is not False, "fixture_guard_close")):
                del self.guards[index]
        if teardown is None:
            _preserve_teardown(primary, self.teardown)
        return not self.guards and not any(self.cleanup_handles)


def _process_identity(api, process):
    created, exited, kernel, user = (C.c_uint64() for _ in range(4))
    api.call(api.k.GetProcessTimes(process, C.byref(created), C.byref(exited), C.byref(kernel), C.byref(user)), "process_times")
    path, size = C.create_unicode_buffer(32768), D(32768)
    api.call(api.k.QueryFullProcessImageNameW(process, 0, path, C.byref(size)), "process_image")
    _need(Path(path.value) == Path(sys.executable), "process_image_path")
    _need(_read_source(api, Path(path.value))[0] == _EXE_SHA, "process_image_hash")
    return {"pid": api.k.GetProcessId(process), "creation_time": created.value, "exe_sha256": _EXE_SHA}


def _start(api, token, fixture):
    startup, process = _Startup(), _Process()
    startup.cb = C.sizeof(startup)
    startup.desktop = ""
    # Deliberately no inherited handles or standard handles, and no interactive desktop.
    arguments = [sys.executable, "-B", "-I", str(_CHILD), str(fixture.root)]
    command = C.create_unicode_buffer(subprocess.list2cmdline(arguments))
    environment = C.create_unicode_buffer("SystemRoot="+os.environ["SystemRoot"]+"\0TEMP="+str(fixture.root.parent)
                                         +"\0TMP="+str(fixture.root.parent)+"\0\0")
    api.call(api.a.CreateProcessAsUserW(token, sys.executable, command, None, None, False,
                                      0x08000000 | 0x400 | 4, environment, str(fixture.root/"control"),
                                      C.byref(startup), C.byref(process)), "restricted_process_prerequisite")
    return process


def _result_status():
    return {"engineering_only": True, "native_accepted": False, "s4_accepted": False,
            "formal_permission": False, "non_goals": list(_NON_GOALS), "windows_3_12": "not_run/runtime_unavailable",
            "source_scope": "two-candidate-index-blobs-only", "execution_authenticated": False}


def _owned_teardown(api, process, handles, fixture, teardown):
    # These are exclusively the handles returned to this harness for its child
    # and tokens. No path lookup, cleanup, adoption or publication occurs here.
    if api is not None:
        if process is not None:
            wait = None
            try:
                wait = api.k.WaitForSingleObject(process.process, 0)
                _need(wait in (0, 258), "owned_process_wait")
            except BaseException as error:
                teardown.record("owned_process_wait", error)
            if wait != 0:
                teardown.attempt("owned_process_terminate", lambda: api.call(
                    api.k.TerminateProcess(process.process, 1), "owned_process_terminate"))
                teardown.attempt("owned_process_unconfirmed", lambda: _need(
                    api.k.WaitForSingleObject(process.process, 5000) == 0, "owned_process_unconfirmed"))
        for handle in handles:
            if handle:
                teardown.attempt("owned_handle_close", lambda: api.call(api.k.CloseHandle(handle), "owned_handle_close"))
    if fixture is not None:
        teardown.attempt("fixture_close", lambda: fixture.close(teardown=teardown))


class _ControlOutcome(dict):
    """JSON/repr expose only the safe mapping; private evidence lives with it."""
    def __init__(self):
        super().__init__()
        self.private_evidence = None
        self.private_control_evidence = None
        self.private_replace_evidence = None


def _finish_outcome(outcome, primary, teardown):
    previous = getattr(primary, "teardown", None)
    if isinstance(previous, _Teardown):
        # Preserve the earliest diagnostics as well as the primary reason.
        previous.merge(teardown)
        teardown = previous
    if teardown.count:
        teardown.resource_stop |= _resource_stop(primary)
        outcome["teardown"] = teardown.report()
        if outcome["status"] == "native_control_pass":
            outcome.update(status="failed", reason="owned_teardown_failed", winerror=0)
            outcome.pop("success_residue_count", None)
        if teardown.resource_stop:
            outcome.update(retained_exists=None, retained_existence="unverified")
    return outcome


def run_control_harness():
    """Run a fixed control; return safe JSON plus explicit private evidence access."""
    started = time.monotonic()
    fixture = api = None
    parent = restricted = actual = impersonation = None
    process = None
    peaks = None
    outcome, primary, teardown = None, None, _Teardown()
    result, control_status = _ControlOutcome(), "not_completed"
    trace_teardown = _Teardown()
    try:
        api = _api()
        runtime, source = _runtime(), _source_pin()
        api.no_impersonation()
        parent = api.token(api.k.GetCurrentProcess(), 0x8B)
        parent_profile = api.profile(parent)
        restricted = api.restricted(parent, parent_profile)
        restricted_profile = api.profile(restricted)
        fixture = _Fixture(api, parent_profile["user"][0])
        fixture.create()
        fixture.freeze()
        fixture.file(_REPLACE_TRACE_NAME, b"", "control")
        nonce = uuid.uuid4().hex
        request = {"version": "b1.2", "nonce": nonce, "objects": fixture.ledger,
                   "parent": parent_profile, "restricted": restricted_profile, "source": source}
        request_raw = _canonical(request)
        fixture.file("control/request.json", request_raw, "private")
        process = _start(api, restricted, fixture)
        identity = _process_identity(api, process.process)
        _need(identity["pid"] != os.getpid() and identity["pid"] == process.pid, "child_pid")
        actual = api.token(process.process)
        actual_profile = api.profile(actual)
        _validate_restricted(parent_profile, actual_profile)
        _need(_shape(actual_profile) == _shape(restricted_profile), "child_primary_profile")
        impersonation = api.impersonation(actual)
        duplicate_profile = api.profile(impersonation)
        _need(duplicate_profile["type"] == 2 and _shape(duplicate_profile) == _shape(actual_profile), "child_duplicate_profile")
        parent_access = _access_matrix(api, fixture.root, fixture.ledger, impersonation)
        _need(api.k.ResumeThread(process.thread) != 0xffffffff, "child_resume")
        peaks = {"combined_peak_private_bytes": 0, "combined_peak_working_bytes": 0}
        deadline = time.monotonic()+30
        while True:
            own, child = api.resources(api.k.GetCurrentProcess()), api.resources(process.process)
            peaks["combined_peak_private_bytes"] = max(peaks["combined_peak_private_bytes"], own["peak_pagefile_bytes"]+child["peak_pagefile_bytes"])
            peaks["combined_peak_working_bytes"] = max(peaks["combined_peak_working_bytes"], own["peak_working_bytes"]+child["peak_working_bytes"])
            peaks.update({k: own[k] for k in ("system_commit_bytes", "system_commit_limit_bytes")})
            _need(peaks["combined_peak_private_bytes"] < _MEMORY_LIMIT, "memory_budget")
            wait = api.k.WaitForSingleObject(process.process, 20)
            if wait == 0:
                break
            _need(wait == 258 and time.monotonic() < deadline, "child_timeout")
        code = D()
        api.call(api.k.GetExitCodeProcess(process.process, C.byref(code)), "child_exit_query")
        if code.value:
            child_failure = _Failure("child_resource_stop" if code.value == _CHILD_RESOURCE_EXIT else "child_failed",
                                     child_exit_code=code.value)
            if not _resource_stop(child_failure):
                try:
                    _capture_replace_trace(api, fixture, result, nonce, complete=False)
                except BaseException as error:
                    trace_teardown.record("replace_trace_capture", error)
                    _preserve_teardown(child_failure, trace_teardown)
            raise child_failure
        _capture_replace_trace(api, fixture, result, nonce, complete=True)
        _need(api.profile(actual) == actual_profile and api.profile(parent) == parent_profile, "token_drift")
        report_handle = _Bound(api, fixture.path("control/report.json"), directory=False)
        with _Closing(report_handle.close):
            raw = report_handle.read()
            report = _json(raw)
            _verify_report(report, identity, nonce, _sha(request_raw), actual_profile, parent_access, source)
            fixture.record("control/report.json", report_handle, "control", raw)
        fixture.check()
        _need(_source_pin() == source and _runtime() == runtime, "source_runtime_drift")
        evidence = {**_result_status(), "status": "native_control_pass", "runtime": runtime, "source": source,
                    "parent_profile": parent_profile, "child_os_identity": identity, "child_profile": actual_profile,
                    "duplicate_profile": duplicate_profile, "access": parent_access, "child_report": report,
                    "fixture_basename": fixture.root.name, "fixture_bytes": sum(x["bytes"] for x in fixture.ledger.values()),
                    "resources": peaks, "replace_trace": result.get("replace_trace")}
        control_status = "pass"
        result.private_control_evidence = _canonical(evidence)
        fixture.cleanup(operations=result.private_control_evidence)
        outcome = {**_result_status(), "status": "native_control_pass", "runtime": runtime, "source": source,
                   "fixture_basename": fixture.root.name, "fixture_bytes": evidence["fixture_bytes"],
                   "resources": peaks, "success_residue_count": 0, "elapsed_seconds": time.monotonic()-started}
    except BaseException as exc:
        primary = exc
        reason, error = (exc.reason, exc.error) if type(exc) is _Failure else ("resource_failure" if isinstance(exc, MemoryError) else "unexpected_failure", 0)
        if _resource_stop(exc):
            # Resource stop: memory-only metadata, never exists/stat/hash/list or
            # source/temp/artifact rereads. Remaining teardown is handle/process-only.
            outcome = {**_result_status(), "status": "failed", "reason": reason, "winerror": error,
                    "retained_basename": fixture.root.name if fixture and fixture.root else None,
                    "retained_exists": None, "retained_existence": "unverified",
                    "known_bytes": sum(x["bytes"] for x in fixture.ledger.values()) if fixture else 0,
                    "child_exit_code": exc.child_exit_code if type(exc) is _Failure else None, "resources": peaks,
                    "elapsed_seconds": time.monotonic()-started}
        else:
            outcome = {**_result_status(), "status": "failed", "reason": reason, "winerror": error,
                       "retained_basename": fixture.root.name if fixture and fixture.root else None,
                       "retained_exists": None, "retained_existence": "unverified",
                       "known_bytes": sum(x["bytes"] for x in fixture.ledger.values()) if fixture else 0,
                       "child_exit_code": exc.child_exit_code if type(exc) is _Failure else None,
                       "resources": peaks,
                       "elapsed_seconds": time.monotonic()-started}
    finally:
        # Never resume cleanup or inspect failed trees. Terminate only our child.
        _owned_teardown(api, process, (impersonation, actual, restricted, parent,
                        process.thread if process else None, process.process if process else None), fixture, teardown)
    result.update(_finish_outcome(outcome, primary, teardown))
    result["control_status"] = "failed" if primary is not None and control_status == "not_completed" else control_status
    journal = getattr(fixture, "cleanup_journal", None)
    result.private_evidence = journal if type(journal) is CleanupJournal else None
    result["cleanup_status"] = journal._status if type(journal) is CleanupJournal else (
        "capture_failed" if getattr(fixture, "cleanup_attempted", False) is True else "not_started")
    result["teardown_status"] = "failed" if "teardown" in result else "pass"
    if type(journal) is CleanupJournal:
        result["known_bytes_basis"] = "pre_cleanup_snapshot_not_retained_bytes"
        # Detail rendering allocates; defer it after any resource stop. The actual
        # immutable snapshot and transition slots remain owned by the result.
        if not _resource_stop(primary) and not teardown.resource_stop and not journal._resource_stop:
            try:
                result["cleanup"] = journal.report()
            except BaseException as error:
                result.update(status="failed", reason="resource_failure" if _resource_stop(error)
                              else "cleanup_report_failed", winerror=0)
                result.pop("success_residue_count", None)
    return result


def _access_matrix(api, root, ledger, token):
    result = {}
    for name in ("control/data.bin", "control", "frozen/data.bin", "frozen", "frozen/empty"):
        row = ledger[name]
        bound = _Bound(api, root/name, directory=row["identity"]["directory"])
        with _Closing(bound.close):
            _need(bound.identity == row["identity"] and api.security(bound.handle) == row["sd"], "access_object_identity")
            rights = _DIR_RIGHTS if bound.directory else _FILE_RIGHTS
            result[name] = {key: api.access(bound.handle, token, mask) for key, mask in {"read": 0x80000000, **rights, "write_dac": 0x40000, "write_owner": 0x80000}.items()}
            _need(result[name]["read"]["access_status"], "read_access_denied")
            for key, mask in rights.items():
                _check_access(result[name][key], mask, not name.startswith("frozen"))
    return result


def _check_access(row, mask, allowed):
    _need(row["api_success"] is True and row["mask"] == mask and row["access_status"] is allowed
          and row["granted"] == (mask if allowed else 0) and row["privileges_used"] == 0, "access_expectation")


def _verify_report(report, identity, nonce, request_sha, profile, access, source):
    _need(set(report) == {"version", "nonce", "request_sha256", "identity", "profile", "source", "access", "operations", "no_impersonation", "isolated", "no_bytecode", "inherited_handles"}, "report_shape")
    _need(report["version"] == "b1.2" and report["nonce"] == nonce and report["request_sha256"] == request_sha, "report_replay")
    _need(_canonical(report["identity"]) == _canonical(identity) and _canonical(report["profile"]) == _canonical(profile)
          and _canonical(report["source"]) == _canonical(source), "report_provenance")
    _need(_canonical(report["access"]) == _canonical(access) and report["no_impersonation"] is True and report["isolated"] is True
          and report["no_bytecode"] is True and report["inherited_handles"] is False, "report_controls")
    _need(_canonical(report["operations"]) == _canonical(_expected_operations()), "report_operations")


def _expected_operations():
    return {mode: {"file_right_open": {key: code for key in _FILE_RIGHTS},
                   "directory_right_open": {key: code for key in _DIR_RIGHTS},
                   "mutation": {key: code for key in ("write", "append", "file_ea", "file_attributes", "directory_ea",
                       "directory_attributes", "delete", "add_file", "add_subdirectory", "delete_child", "truncate", "rename", "replace")}}
            for mode, code in (("control", 0), ("frozen", 5))}


def _child_teardown(api, guards, tokens, primary, teardown):
    for guard in reversed(guards):
        teardown.attempt("child_guard_close", guard.close)
    for token in tokens:
        if token:
            teardown.attempt("child_token_close", lambda: api.close(token))
    _preserve_teardown(primary, teardown)


def _child_main(root):
    """Private fixed protocol entry; never called by ordinary project consumers."""
    api = _api()
    _runtime()
    _need(root.parent == _temporary_path(api)
          and re.fullmatch(_PREFIX+r"[0-9a-f]{32}", root.name), "child_scope")
    api.no_impersonation()
    primary = duplicate = failure = None
    guards, teardown = [], _Teardown()
    try:
        primary = api.token(api.k.GetCurrentProcess())
        for path in reversed((root, *root.parents)):
            guards.append(_Bound(api, path, directory=True))
        request_handle = _Bound(api, root/"control/request.json", directory=False)
        with _Closing(request_handle.close):
            raw = request_handle.read()
        request = _json(raw)
        _need(set(request) == {"version", "nonce", "objects", "parent", "restricted", "source"}
              and request["version"] == "b1.2" and re.fullmatch(r"[0-9a-f]{32}", request["nonce"]), "request_shape")
        profile = api.profile(primary)
        _validate_restricted(request["parent"], profile)
        _need(_shape(profile) == _shape(request["restricted"]), "child_profile")
        _need(type(request["source"]) is list and len(request["source"]) == 2, "child_source_count")
        for descriptor, path in zip(request["source"], (_SOURCE, _CHILD)):
            digest, count = _read_source(api, path)
            _need(descriptor == {"path": path.relative_to(_ROOT).as_posix(), "sha256": digest, "bytes": count}, "child_source")
        duplicate = api.impersonation(primary)
        access = _access_matrix(api, root, request["objects"], duplicate)
        trace_handle = _Bound(api, root/_REPLACE_TRACE_NAME, directory=False, access=0x20083, share=1)
        guards.append(trace_handle)  # Retain ownership even if its later close fails.
        trace_row = request["objects"][_REPLACE_TRACE_NAME]
        _need(trace_handle.identity == trace_row["identity"] and api.security(trace_handle.handle) == trace_row["sd"]
              and trace_handle.read() == b"", "replace_trace_initial")
        trace_handle.streams()
        trace = _ReplaceTrace(request["nonce"], trace_handle.write)
        operations = _operations(api, root, profile["user"][0], request["objects"], replace_trace=trace)
        _need(api.profile(primary) == profile, "child_token_drift")
        api.no_impersonation()
        _need(all(api.k.GetStdHandle(value & 0xffffffff) in (None, C.c_void_p(-1).value) for value in (-10, -11, -12)), "child_standard_handles")
        report = {"version": "b1.2", "nonce": request["nonce"], "request_sha256": _sha(raw),
                  "identity": _process_identity(api, api.k.GetCurrentProcess()), "profile": profile,
                  "source": request["source"], "access": access, "operations": operations,
                  "no_impersonation": True, "isolated": bool(sys.flags.isolated), "no_bytecode": sys.dont_write_bytecode,
                  "inherited_handles": False}
        sd = api.descriptor(_dacl(profile["user"][0], "control", False)[0])
        try:
            output = _Bound(api, root/"control/report.json", directory=False, access=0x20083, creation=1, sd=sd)
        finally:
            api.k.LocalFree(sd)
        with _Closing(output.close):
            output.write(_canonical(report))
        return 0
    except BaseException as error:
        failure = error
        raise
    finally:
        _child_teardown(api, guards, (duplicate, primary), failure, teardown)


class _ReplaceTrace:
    """Six bounded append records. Never writes from an exception handler.

    Intent is flushed before the operation. A partial final record is not a
    confirmation. Private records contain original bytes/SDs; repr is redacted.
    """
    def __init__(self, nonce, sink=None):
        _need(type(nonce) is str and re.fullmatch(r"[0-9a-f]{32}", nonce), "replace_trace_nonce")
        self.nonce, self.sink = nonce, sink
        self.lines, self.count, self.size = [None] * len(_REPLACE_STAGES), 0, 0
        self.previous, self.failed = "0" * 64, False
        self.pending_record = None

    def __repr__(self):
        return "_ReplaceTrace(<private evidence>)"

    def emit(self, stage, details):
        _need(not self.failed and self.count < len(_REPLACE_STAGES)
              and stage == _REPLACE_STAGES[self.count], "replace_trace_order")
        raw = _canonical({"version": 1, "sequence": self.count, "nonce": self.nonce,
                          "stage": stage, "previous_sha256": self.previous, "details": details}) + b"\n"
        _need(self.size + len(raw) <= _REPLACE_TRACE_LIMIT, "file_size")
        digest = _sha(raw)
        self.pending_record = raw  # Before the sink; retained even on short write.
        if self.sink is not None:
            self.sink(raw)  # Native sink is WriteFile + FlushFileBuffers + identity check.
        self.lines[self.count] = raw
        self.count += 1
        self.size += len(raw)
        self.previous, self.pending_record = digest, None

    def raw(self):
        """Allocates; only call outside a resource-failure handler."""
        return b"".join(self.lines[:self.count])


def _replace_snapshot(api, path):
    bound = _Bound(api, path, directory=False)
    with _Closing(bound.close):
        bound.streams()
        raw = bound.read()
        return {"identity": dict(bound.identity), "security": api.security(bound.handle),
                "content_hex": raw.hex(), "bytes": len(raw), "sha256": _sha(raw)}


def _replace_absent(path):
    try:
        path.lstat()
    except FileNotFoundError as error:
        _need(getattr(error, "winerror", 2) == 2, "replace_absence_error")
        return
    raise _Failure("replace_expected_absence")


def _validate_replace_trace(raw, source_row, nonce, *, complete):
    _need(type(nonce) is str and re.fullmatch(r"[0-9a-f]{32}", nonce)
          and type(complete) is bool, "replace_trace_context")
    _need(type(raw) is bytes and len(raw) <= _REPLACE_TRACE_LIMIT, "replace_trace_size")
    rows, previous, size = [], "0" * 64, 0
    tail = b""
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            tail = line
            break
        _need(len(rows) < len(_REPLACE_STAGES), "replace_trace_count")
        row = _json(line[:-1])
        _need(type(row) is dict and set(row) == {"version", "sequence", "nonce", "stage", "previous_sha256", "details"}
              and type(row["version"]) is int and row["version"] == 1
              and type(row["sequence"]) is int and row["sequence"] == len(rows)
              and row["nonce"] == nonce and row["stage"] == _REPLACE_STAGES[len(rows)]
              and row["previous_sha256"] == previous, "replace_trace_record")
        _need(type(row["details"]) is dict, "replace_trace_details")
        if len(rows) < 2:
            key = "source" if not rows else "target"
            _need(set(row["details"]) == {key}, "replace_trace_snapshot")
            snapshot = row["details"][key]
            _need(type(snapshot) is dict and set(snapshot) == {"identity", "security", "content_hex", "bytes", "sha256"}, "replace_trace_snapshot")
            value = snapshot["content_hex"]
            _need(type(value) is str and len(value) % 2 == 0 and re.fullmatch(r"[0-9a-f]*", value), "replace_trace_content")
            content = bytes.fromhex(value)
            _need(type(snapshot["bytes"]) is int and snapshot["bytes"] == len(content)
                  and snapshot["sha256"] == _sha(content), "replace_trace_content")
            _need(type(snapshot["identity"]) is dict and snapshot["identity"].get("directory") is False
                  and snapshot["security"] == source_row["sd"], "replace_trace_identity")
            if not rows:
                _need(snapshot["identity"] == source_row["identity"] and snapshot["bytes"] == source_row["bytes"]
                      and snapshot["sha256"] == source_row["sha256"], "replace_trace_source")
            else:
                source_id, target_id = source_row["identity"], snapshot["identity"]
                _need(set(target_id) == set(source_id)
                      and all(type(target_id[key]) is type(source_id[key]) for key in source_id)
                      and type(target_id.get("file_id")) is str and re.fullmatch(r"[0-9a-f]{32}", target_id["file_id"])
                      and content == b"B1-replace-destination\n"
                      and {**target_id, "file_id": source_id["file_id"]} == source_id
                      and target_id["file_id"] != source_id["file_id"], "replace_trace_target")
        else:
            _need(row["details"] == {}, "replace_trace_details")
        rows.append(row)
        previous, size = _sha(line), size + len(line)
    if complete:
        _need(len(rows) == len(_REPLACE_STAGES) and not tail, "replace_trace_incomplete")
    # These are inferences from the confirmed prefix under the fixed producer,
    # not a fresh filesystem inventory. Pending records deliberately stay uncertain.
    source_state = ("not_observed", "at_original", "at_original", "uncertain", "at_destination", "uncertain", "at_original")[len(rows)]
    target_state = ("not_observed", "uncertain", "captured_present", "uncertain", "consumed", "consumed", "consumed")[len(rows)]
    return {"status": "complete" if len(rows) == len(_REPLACE_STAGES) and not tail else "incomplete",
            "confirmed_records": len(rows), "last_stage": rows[-1]["stage"] if rows else None,
            "source_state": "uncertain" if tail else source_state,
            "original_destination_state": "uncertain" if tail else target_state,
            "complete_prefix_bytes": size, "unconfirmed_tail_bytes": len(tail), "sha256": _sha(raw),
            "native_accepted": False}


def _capture_replace_trace(api, fixture, result, nonce, *, complete):
    row = fixture.ledger[_REPLACE_TRACE_NAME]
    bound = _Bound(api, fixture.path(_REPLACE_TRACE_NAME), directory=False, share=1)
    with _Closing(bound.close):
        _need(bound.identity == row["identity"] and api.security(bound.handle) == row["sd"], "replace_trace_pin")
        bound.streams()
        raw = bound.read()
        result.private_replace_evidence = raw  # Retain before close/parsing; invalid evidence is not discarded.
    result["replace_trace"] = _validate_replace_trace(raw, fixture.ledger["control/data.bin"], nonce, complete=complete)
    if complete:
        # This is the one explicitly writable child evidence file. Identity/SD
        # remain pinned; accept its content only after the entire trace validates.
        row["sha256"], row["bytes"] = _sha(raw), len(raw)


def _replace_control(api, root, user, ledger, trace=None):
    source_name, target_name = "control/data.bin", "control/replaced.bin"
    source, target = root/source_name, root/target_name
    trace = _ReplaceTrace(uuid.uuid4().hex) if trace is None else trace
    try:
        before = _replace_snapshot(api, source)
        source_row = ledger[source_name]
        _need(before["identity"] == source_row["identity"] and before["security"] == source_row["sd"]
              and before["sha256"] == source_row["sha256"] and before["bytes"] == source_row["bytes"], "replace_source_pin")
        _need(target_name not in ledger, "replace_target_collision")
        _replace_absent(target)
        trace.emit("create_pending", {"source": before})
        owned = _Fixture(api, user)
        owned.root, owned.ledger = root, ledger
        owned.file(target_name, b"B1-replace-destination\n", "control")
        destination = _replace_snapshot(api, target)
        _need(destination["identity"] == ledger[target_name]["identity"]
              and destination["identity"].get("volume") == before["identity"].get("volume")
              and destination["identity"].get("file_id") != before["identity"].get("file_id")
              and destination["security"] == before["security"]
              and destination["content_hex"] == b"B1-replace-destination\n".hex(), "replace_target_pin")
        trace.emit("target_captured", {"target": destination})
        trace.emit("replace_pending", {})
        api.call(api.k.MoveFileExW(str(source), str(target), 1), "mutation_api")
        _need(_replace_snapshot(api, target) == before, "replace_readback")
        _replace_absent(source)
        trace.emit("replaced", {})
        trace.emit("restore_pending", {})
        api.call(api.k.MoveFileW(str(target), str(source)), "mutation_api")
        _need(_replace_snapshot(api, source) == before, "replace_restore")
        _replace_absent(target)
        trace.emit("restored", {})
        del ledger[target_name]
        return trace
    except BaseException as error:
        trace.failed = True
        error.private_replace_evidence = trace  # No FS, hashes, serialization or repair after failure.
        raise


def _operations(api, root, user, ledger, *, replace_trace=None):
    result = {mode: {"file_right_open": {}, "directory_right_open": {}, "mutation": {}} for mode in ("control", "frozen")}
    for mode in ("control", "frozen"):
        directory, file = root/mode, root/mode/"data.bin"
        # Successful control operations are reversible and use only the fixed fixture.
        for key, mask in _FILE_RIGHTS.items():
            h = api.k.CreateFileW(str(file), mask, 7, None, 3, 0x00200000, None)
            error = C.get_last_error() if h == C.c_void_p(-1).value else 0
            if not error:
                api.close(h)
            result[mode]["file_right_open"][key] = error
        for key, mask in _DIR_RIGHTS.items():
            h = api.k.CreateFileW(str(directory), mask, 7, None, 3, 0x02200000, None)
            error = C.get_last_error() if h == C.c_void_p(-1).value else 0
            if not error:
                api.close(h)
            result[mode]["directory_right_open"][key] = error
        def attempt(key, operation):
            try:
                operation()
                error = 0
            except OSError as exc:
                if isinstance(getattr(exc, "teardown", None), _Teardown) or isinstance(getattr(exc, "private_replace_evidence", None), _ReplaceTrace):
                    raise
                error = getattr(exc, "winerror", 0)
            except _Failure as exc:
                # Only a real CreateFile denial can be an expected negative;
                # a failed native mutation/flush/query is NOT a passing denial.
                if isinstance(getattr(exc, "teardown", None), _Teardown) or isinstance(getattr(exc, "private_replace_evidence", None), _ReplaceTrace):
                    raise  # A denial never excuses unconfirmed handle release.
                if exc.reason not in ("object_open", "mutation_api"):
                    raise
                error = exc.error
            result[mode]["mutation"][key] = error
            _need(error == (0 if mode == "control" else 5), "operation_unexpected")
        def write_data(append=False, truncate=False):
            bound = _Bound(api, file, directory=False, access=0x80 | (4 if append else 2))
            with _Closing(bound.close):
                if truncate:
                    position = len(b"B1-control\n") if mode == "control" else 0
                    api.call(api.k.SetFilePointerEx(bound.handle, position, None, 0), "mutation_api")
                    api.call(api.k.SetEndOfFile(bound.handle), "mutation_api")
                else:
                    bound.write(b"append\n" if append else b"B1-control\n")
        def delete(path, directory=False):
            api.call((api.k.RemoveDirectoryW if directory else api.k.DeleteFileW)(str(path)), "mutation_api")
        def rename(source, target, replace=False):
            ok = api.k.MoveFileExW(str(source), str(target), 1) if replace else api.k.MoveFileW(str(source), str(target))
            api.call(ok, "mutation_api")
        for label, path, is_dir in (("file", file, False), ("directory", directory, True)):
            def attributes():
                bound = _Bound(api, path, directory=is_dir, access=0x180)
                with _Closing(bound.close):
                    timestamp = C.c_uint64(132537600000000000)
                    api.call(api.k.SetFileTime(bound.handle, None, None, C.byref(timestamp)), "attributes_write")
            def ea():
                bound = _Bound(api, path, directory=is_dir, access=0x80 | 0x10)
                with _Closing(bound.close):
                    # FILE_FULL_EA_INFORMATION, fixed test-owned EA, then removal.
                    # NtSetEaFile is the user-mode native equivalent of ZwSetEaFile.
                    for value in (b"1", b""):
                        raw = b"\0\0\0\0\0\x08"+len(value).to_bytes(2, "little")+b"BANTO_B1\0"+value
                        buf, status = C.create_string_buffer(raw), _IoStatus()
                        _need(api.n.NtSetEaFile(bound.handle, C.byref(status), buf, len(raw)) == 0, "ea_write")
            attempt(label+"_attributes", attributes)
            attempt(label+"_ea", ea)
        if mode == "control":
            # A writable positive control proves denied frozen operations are not
            # merely a WRITE_RESTRICTED token that cannot write anywhere.
            attempt("write", write_data)
            attempt("append", lambda: write_data(append=True))
            write_data(truncate=True)
            new = directory/"transient.bin"
            def create_control():
                sd = api.descriptor(_dacl(user, "control", False)[0])
                try:
                    bound = _Bound(api, new, directory=False, access=0x20083, creation=1, sd=sd)
                finally:
                    api.k.LocalFree(sd)
                with _Closing(bound.close):
                    bound.write(b"transient\n")
            attempt("add_file", create_control)
            attempt("delete", lambda: delete(new))
            new = directory/"transient-dir"
            def create_directory():
                sd = api.descriptor(_dacl(user, "control", True)[0])
                try:
                    sa = _SA(C.sizeof(_SA), sd, False)
                    api.call(api.k.CreateDirectoryW(str(new), C.byref(sa)), "control_directory_create")
                finally:
                    api.k.LocalFree(sd)
            attempt("add_subdirectory", create_directory)
            attempt("delete_child", lambda: delete(new, True))
            attempt("truncate", lambda: write_data(truncate=True))
            attempt("rename", lambda: rename(file, directory/"renamed.bin"))
            rename(directory/"renamed.bin", file)
            attempt("replace", lambda: _replace_control(api, root, user, ledger, replace_trace))
        else:
            attempt("write", write_data)
            attempt("append", lambda: write_data(append=True))
            attempt("delete", lambda: delete(file))
            attempt("add_file", lambda: _Bound(api, directory/"unexpected.bin", directory=False, access=2, creation=1).close())
            attempt("add_subdirectory", lambda: api.call(api.k.CreateDirectoryW(str(directory/"unexpected-dir"), None), "mutation_api"))
            attempt("delete_child", lambda: delete(directory/"empty", True))
            attempt("truncate", lambda: write_data(truncate=True))
            attempt("rename", lambda: rename(file, directory/"renamed.bin"))
            attempt("replace", lambda: rename(root/"control/data.bin", file, True))
        _need(_canonical(result[mode]) == _canonical(_expected_operations()[mode]), "operation_matrix")
        if mode == "control":
            # NtSetEaFile sets ARCHIVE even on directories. Restore this known
            # positive-control metadata only after the complete control passes.
            # Do not relax identity matching or tolerate arbitrary attribute drift.
            for name in ("control", "control/data.bin"):
                expected = ledger[name]["identity"]
                bound = _Bound(api, root/name, directory=expected["directory"], access=0x180)
                with _Closing(bound.close):
                    observed = dict(bound.identity)
                    _need(observed["attributes"] & ~32 == expected["attributes"] & ~32, "control_attributes_drift")
                    observed["attributes"] = expected["attributes"]
                    _need(observed == expected, "control_identity_drift")
                    basic = _BasicInfo()
                    basic.attributes = expected["attributes"]
                    api.call(api.k.SetFileInformationByHandle(bound.handle, 0, C.byref(basic), C.sizeof(basic)), "control_attributes_restore")
                    bound.identity = dict(expected)
                    bound.check()
    return result
