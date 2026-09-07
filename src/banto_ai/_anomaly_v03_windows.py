"""S4-B1, engineering-only Windows controls. NOT a publisher or a sandbox.

Only run_control_harness() is public; it accepts no path, ACL or token. All
mutations belong to a newly created UUID system-temp tree. Failure retains it.
Protected DACL means no inherited ACEs, not WORM, owner/admin/WRITE_DAC or
WRITE_OWNER resistance, privileged-writer protection, or power-loss durability.
The parent and fixed child are trusted code in the same account/logon. A hostile
same-user create/bind swap or writable mapping is outside this control's model.
No S4 acceptance or campaign permission is issued, even on native success.
"""

from __future__ import annotations

import ctypes as C
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

    def close(self, handle):
        if handle:
            self.call(self.k.CloseHandle(handle), "handle_close")

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
            except BaseException:
                self.close(result)
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
    _need(len(value) == size and value.endswith("\\"), "temp_path_result")
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
        except BaseException:
            self.close()
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
        try:
            ident = _FileId()
            self.api.call(self.api.k.GetFileInformationByHandleEx(h, 18, C.byref(ident), C.sizeof(ident)), "identity_requery")
            _need(ident.volume == observed["volume"] and bytes(ident.identifier).hex() == observed["file_id"], "named_handle_mismatch")
        finally:
            self.api.close(h)
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
        handle = self.api.k.FindFirstStreamW(str(self.path), 0, C.byref(item), 0)
        names = []
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
            finally:
                self.api.call(self.api.k.FindClose(handle), "stream_close")
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

    def close(self):
        if self.handle is not None:
            h, self.handle = self.handle, None
            self.api.close(h)


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
    guards = []
    try:
        for ancestor in reversed(path.parents):
            guards.append(_Bound(api, ancestor, directory=True))
        bound = _Bound(api, path, directory=False, share=1)
        try:
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
        finally:
            bound.close()
    finally:
        for guard in reversed(guards):
            guard.close()


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


def _source_pin():
    rows = []
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
    for path in (_SOURCE, _CHILD):
        raw = path.read_bytes()
        _need(_read_source(_api(), path) == (_sha(raw), len(raw)), "source_handle_hash")
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", "show", ":"+path.relative_to(_ROOT).as_posix()],
                                cwd=_ROOT, env=environment, capture_output=True, check=False, timeout=10)
        _need(result.returncode == 0 and result.stdout == raw, "source_index_bytes")
        rows.append({"path": path.relative_to(_ROOT).as_posix(), "sha256": _sha(raw), "bytes": len(raw)})
    return rows


class _Fixture:
    def __init__(self, api, user):
        self.api, self.user, self.ledger, self.guards, self.root = api, user, {}, [], None

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
        try:
            _need(not list(path.iterdir()), "new_directory_not_empty")
            self.record(name, bound, mode, None)
        finally:
            bound.close()

    def file(self, name, raw, mode):
        sd = self.api.descriptor(_dacl(self.user, mode, False)[0])
        try:
            bound = _Bound(self.api, self.path(name), directory=False, access=0x60083, creation=1, sd=sd)
        finally:
            self.api.k.LocalFree(sd)
        try:
            bound.write(raw)
            _need(bound.read() == raw, "file_readback")
            self.record(name, bound, mode, raw)
        finally:
            bound.close()

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
            try:
                _need(bound.identity == row["identity"] and self.api.security(bound.handle) == row["sd"], "fixture_identity_or_acl")
                bound.streams()
                if bound.directory:
                    pending.extend(((name+"/") if name else "") + x.name for x in bound.path.iterdir())
                else:
                    raw = bound.read()
                    _need(_sha(raw) == row["sha256"] and len(raw) == row["bytes"], "fixture_content")
                observed.add(name)
            finally:
                bound.close()
        _need(observed == set(self.ledger), "fixture_missing_object")

    def freeze(self):
        self.check()
        # Also deny DELETE_CHILD on the bootstrap parent: denying DELETE only on
        # frozen/ is insufficient when its parent still grants delete-child.
        for name in ("frozen/data.bin", "frozen/empty", "frozen", ""):
            row = self.ledger[name]
            bound = _Bound(self.api, self.path(name), directory=row["identity"]["directory"], access=0x60081, share=1)
            try:
                sd = bound.freeze(_dacl(self.user, "frozen", bound.directory)[0])
                _verify_sd(sd, self.user, "frozen", bound.directory)
                row["sd"] = sd
            finally:
                bound.close()
        self.check()  # ALL pins have been closed before launching the child.

    def cleanup(self):
        self.check()  # Whole-tree verification BEFORE any restoration or deletion.
        for name in sorted(self.ledger, key=lambda x: (x.count("/")+bool(x), x), reverse=True):
            self.check()
            row = self.ledger[name]
            bound = _Bound(self.api, self.path(name), directory=row["identity"]["directory"], access=0x60081)
            try:
                _need(bound.identity == row["identity"], "cleanup_identity")
                row["sd"] = bound.freeze(_dacl(self.user, "private", bound.directory)[0])
                _verify_sd(row["sd"], self.user, "private", bound.directory)
            finally:
                bound.close()
        # Read-back checked known objects only. No recursive deletion or adoption.
        for name in sorted(self.ledger, key=lambda x: (x.count("/")+bool(x), x), reverse=True):
            row = self.ledger[name]
            if not name:
                _need(self.guards[-1].path == self.root, "cleanup_root_guard")
                self.guards.pop().close()
            bound = _Bound(self.api, self.path(name), directory=row["identity"]["directory"], access=0x30081, share=1)
            try:
                _need(bound.identity == row["identity"], "cleanup_delete_identity")
                if bound.directory:
                    _need(not list(bound.path.iterdir()), "cleanup_unknown_child")
                else:
                    _need(_sha(bound.read()) == row["sha256"], "cleanup_bytes")
                disposition = B(1)
                self.api.call(self.api.k.SetFileInformationByHandle(bound.handle, 4, C.byref(disposition), C.sizeof(disposition)), "cleanup_disposition")
            finally:
                bound.close()
        _need(not self.root.exists(), "cleanup_residue")

    def close(self):
        for guard in reversed(self.guards):
            guard.close()
        self.guards.clear()


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


def run_control_harness():
    """Run a fixed small control; safe failure preserves evidence, never publishes."""
    started = time.monotonic()
    fixture = api = None
    parent = restricted = actual = impersonation = None
    process = None
    peaks = None
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
        nonce = uuid.uuid4().hex
        request = {"version": "b1.1", "nonce": nonce, "objects": fixture.ledger,
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
            raise _Failure("child_failed", child_exit_code=code.value)
        _need(api.profile(actual) == actual_profile and api.profile(parent) == parent_profile, "token_drift")
        report_handle = _Bound(api, fixture.path("control/report.json"), directory=False)
        try:
            raw = report_handle.read()
            report = _json(raw)
            _verify_report(report, identity, nonce, _sha(request_raw), actual_profile, parent_access, source)
            fixture.record("control/report.json", report_handle, "control", raw)
        finally:
            report_handle.close()
        fixture.check()
        _need(_source_pin() == source and _runtime() == runtime, "source_runtime_drift")
        evidence = {**_result_status(), "status": "native_control_pass", "runtime": runtime, "source": source,
                    "parent_profile": parent_profile, "child_os_identity": identity, "child_profile": actual_profile,
                    "duplicate_profile": duplicate_profile, "access": parent_access, "child_report": report,
                    "fixture_basename": fixture.root.name, "fixture_bytes": sum(x["bytes"] for x in fixture.ledger.values()),
                    "resources": peaks}
        fixture.cleanup()
        evidence.update(success_residue_count=0, elapsed_seconds=time.monotonic()-started)
        return evidence
    except BaseException as exc:
        reason, error = (exc.reason, exc.error) if type(exc) is _Failure else ("resource_failure" if isinstance(exc, MemoryError) else "unexpected_failure", 0)
        return {**_result_status(), "status": "failed", "reason": reason, "winerror": error,
                "retained_basename": fixture.root.name if fixture and fixture.root and fixture.root.exists() else None,
                "known_bytes": sum(x["bytes"] for x in fixture.ledger.values()) if fixture else 0,
                "child_exit_code": exc.child_exit_code if type(exc) is _Failure else None,
                "resources": peaks,
                "elapsed_seconds": time.monotonic()-started}
    finally:
        # Never clean failed trees or alter their ACLs. Terminate only our own child.
        if api:
            if process and api.k.WaitForSingleObject(process.process, 0) == 258:
                api.k.TerminateProcess(process.process, 1)
                api.k.WaitForSingleObject(process.process, 5000)
            for handle in (impersonation, actual, restricted, parent,
                           process.thread if process else None, process.process if process else None):
                if handle:
                    api.k.CloseHandle(handle)
            if fixture:
                try:
                    fixture.close()
                except BaseException:
                    pass  # Handle close is not permission to repair a retained tree.


def _access_matrix(api, root, ledger, token):
    result = {}
    for name in ("control/data.bin", "control", "frozen/data.bin", "frozen", "frozen/empty"):
        row = ledger[name]
        bound = _Bound(api, root/name, directory=row["identity"]["directory"])
        try:
            _need(bound.identity == row["identity"] and api.security(bound.handle) == row["sd"], "access_object_identity")
            rights = _DIR_RIGHTS if bound.directory else _FILE_RIGHTS
            result[name] = {key: api.access(bound.handle, token, mask) for key, mask in {"read": 0x80000000, **rights, "write_dac": 0x40000, "write_owner": 0x80000}.items()}
            _need(result[name]["read"]["access_status"], "read_access_denied")
            for key, mask in rights.items():
                _check_access(result[name][key], mask, not name.startswith("frozen"))
        finally:
            bound.close()
    return result


def _check_access(row, mask, allowed):
    _need(row["api_success"] is True and row["mask"] == mask and row["access_status"] is allowed
          and row["granted"] == (mask if allowed else 0) and row["privileges_used"] == 0, "access_expectation")


def _verify_report(report, identity, nonce, request_sha, profile, access, source):
    _need(set(report) == {"version", "nonce", "request_sha256", "identity", "profile", "source", "access", "operations", "no_impersonation", "isolated", "no_bytecode", "inherited_handles"}, "report_shape")
    _need(report["version"] == "b1.1" and report["nonce"] == nonce and report["request_sha256"] == request_sha, "report_replay")
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


def _child_main(root):
    """Private fixed protocol entry; never called by ordinary project consumers."""
    api = _api()
    _runtime()
    _need(root.parent == _temporary_path(api)
          and re.fullmatch(_PREFIX+r"[0-9a-f]{32}", root.name), "child_scope")
    api.no_impersonation()
    primary = api.token(api.k.GetCurrentProcess())
    duplicate = None
    guards = []
    try:
        for path in reversed((root, *root.parents)):
            guards.append(_Bound(api, path, directory=True))
        request_handle = _Bound(api, root/"control/request.json", directory=False)
        try:
            raw = request_handle.read()
        finally:
            request_handle.close()
        request = _json(raw)
        _need(set(request) == {"version", "nonce", "objects", "parent", "restricted", "source"}
              and request["version"] == "b1.1" and re.fullmatch(r"[0-9a-f]{32}", request["nonce"]), "request_shape")
        profile = api.profile(primary)
        _validate_restricted(request["parent"], profile)
        _need(_shape(profile) == _shape(request["restricted"]), "child_profile")
        _need(type(request["source"]) is list and len(request["source"]) == 2, "child_source_count")
        for descriptor, path in zip(request["source"], (_SOURCE, _CHILD)):
            digest, count = _read_source(api, path)
            _need(descriptor == {"path": path.relative_to(_ROOT).as_posix(), "sha256": digest, "bytes": count}, "child_source")
        duplicate = api.impersonation(primary)
        access = _access_matrix(api, root, request["objects"], duplicate)
        operations = _operations(api, root, profile["user"][0], request["objects"])
        _need(api.profile(primary) == profile, "child_token_drift")
        api.no_impersonation()
        _need(all(api.k.GetStdHandle(value & 0xffffffff) in (None, C.c_void_p(-1).value) for value in (-10, -11, -12)), "child_standard_handles")
        report = {"version": "b1.1", "nonce": request["nonce"], "request_sha256": _sha(raw),
                  "identity": _process_identity(api, api.k.GetCurrentProcess()), "profile": profile,
                  "source": request["source"], "access": access, "operations": operations,
                  "no_impersonation": True, "isolated": bool(sys.flags.isolated), "no_bytecode": sys.dont_write_bytecode,
                  "inherited_handles": False}
        sd = api.descriptor(_dacl(profile["user"][0], "control", False)[0])
        try:
            output = _Bound(api, root/"control/report.json", directory=False, access=0x20083, creation=1, sd=sd)
        finally:
            api.k.LocalFree(sd)
        try:
            output.write(_canonical(report))
        finally:
            output.close()
        return 0
    finally:
        for guard in reversed(guards):
            guard.close()
        api.close(duplicate)
        api.close(primary)


def _operations(api, root, user, ledger):
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
                error = getattr(exc, "winerror", 0)
            except _Failure as exc:
                # Only a real CreateFile denial can be an expected negative;
                # a failed native mutation/flush/query is NOT a passing denial.
                if exc.reason not in ("object_open", "mutation_api"):
                    raise
                error = exc.error
            result[mode]["mutation"][key] = error
            _need(error == (0 if mode == "control" else 5), "operation_unexpected")
        def write_data(append=False, truncate=False):
            bound = _Bound(api, file, directory=False, access=0x80 | (4 if append else 2))
            try:
                if truncate:
                    position = len(b"B1-control\n") if mode == "control" else 0
                    api.call(api.k.SetFilePointerEx(bound.handle, position, None, 0), "mutation_api")
                    api.call(api.k.SetEndOfFile(bound.handle), "mutation_api")
                else:
                    bound.write(b"append\n" if append else b"B1-control\n")
            finally:
                bound.close()
        def delete(path, directory=False):
            api.call((api.k.RemoveDirectoryW if directory else api.k.DeleteFileW)(str(path)), "mutation_api")
        def rename(source, target, replace=False):
            ok = api.k.MoveFileExW(str(source), str(target), 1) if replace else api.k.MoveFileW(str(source), str(target))
            api.call(ok, "mutation_api")
        for label, path, is_dir in (("file", file, False), ("directory", directory, True)):
            def attributes():
                bound = _Bound(api, path, directory=is_dir, access=0x180)
                try:
                    timestamp = C.c_uint64(132537600000000000)
                    api.call(api.k.SetFileTime(bound.handle, None, None, C.byref(timestamp)), "attributes_write")
                finally:
                    bound.close()
            def ea():
                bound = _Bound(api, path, directory=is_dir, access=0x80 | 0x10)
                try:
                    # FILE_FULL_EA_INFORMATION, fixed test-owned EA, then removal.
                    # NtSetEaFile is the user-mode native equivalent of ZwSetEaFile.
                    for value in (b"1", b""):
                        raw = b"\0\0\0\0\0\x08"+len(value).to_bytes(2, "little")+b"BANTO_B1\0"+value
                        buf, status = C.create_string_buffer(raw), _IoStatus()
                        _need(api.n.NtSetEaFile(bound.handle, C.byref(status), buf, len(raw)) == 0, "ea_write")
                finally:
                    bound.close()
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
                try:
                    bound.write(b"transient\n")
                finally:
                    bound.close()
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
            attempt("replace", lambda: rename(file, directory/"replaced.bin", True))
            rename(directory/"replaced.bin", file)
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
                try:
                    observed = dict(bound.identity)
                    _need(observed["attributes"] & ~32 == expected["attributes"] & ~32, "control_attributes_drift")
                    observed["attributes"] = expected["attributes"]
                    _need(observed == expected, "control_identity_drift")
                    basic = _BasicInfo()
                    basic.attributes = expected["attributes"]
                    api.call(api.k.SetFileInformationByHandle(bound.handle, 0, C.byref(basic), C.sizeof(basic)), "control_attributes_restore")
                    bound.identity = dict(expected)
                    bound.check()
                finally:
                    bound.close()
    return result
