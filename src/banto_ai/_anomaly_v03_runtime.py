"""S3 read-only provenance/runtime boundaries; S4 native acceptance is pending."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import stat
import struct
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path

from . import _anomaly_v03_contract as c
from . import anomaly_v03 as v


class IntegrityError(v.V03ValidationError):
    """A global boundary failure: stop the remaining planned slots."""


def require(condition, reason):
    if not condition:
        raise IntegrityError(reason)


def regular_path(path: Path, *, directory=False, missing=False, links=1) -> Path:
    """Inspect spelling and EVERY ancestor before resolving/opening anything."""
    path = Path(path).absolute()
    require(".." not in path.parts and not str(path).startswith(("\\\\", "//")), "unsafe absolute path")
    for part in (*reversed(path.parents), path):
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            require(missing, "missing path")
            continue
        require(not stat.S_ISLNK(metadata.st_mode) and not getattr(metadata, "st_file_attributes", 0) & 0x400,
                "symlink/junction/reparse traversal")
        if part != path or directory:
            require(stat.S_ISDIR(metadata.st_mode), "non-directory ancestor")
        else:
            require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == links, "nonregular/multiply-linked file")
    require(path.resolve() == path, "resolved path changed")
    return path


def _git(root, *args):
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
    process = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
                             capture_output=True, check=False, env=environment, stdin=subprocess.DEVNULL)
    require(process.returncode == 0, "Git provenance unavailable")
    return process.stdout


@dataclass(frozen=True)
class Checkout:
    root: Path
    revision: str
    entries: tuple[tuple[str, bytes], ...]

    def source_descriptor(self):
        return {"revision": self.revision, "sources": [
            {"path": name, "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
            for name, raw in self.entries]}

    def snapshots(self):
        return {self.revision: dict(self.entries)}

    def recheck(self):
        require(_git(self.root, "rev-parse", "HEAD").decode().strip() == self.revision, "HEAD changed")
        require(not _git(self.root, "status", "--porcelain", "--untracked-files=no"), "tracked source dirty")
        extra = _git(self.root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
        require(not any(_source_path(p) for p in extra if p), "untracked source inventory")
        for name, raw in self.entries:
            require(regular_path(self.root/name).read_bytes() == raw, "working source bytes changed")


def _source_path(name):
    return (name.startswith(("src/", "schemas/", "examples/configs/", "tools/", "tests/"))
            or name in ("pyproject.toml", c.PLAN_PATH))


def capture_checkout(root: Path, expected_head: str) -> Checkout:
    """Full revision + tracked clean + exact regular working/Git bytes.

    Ignored artifacts are neither inputs nor cleanup targets. Untracked source
    files in an executable/configuration prefix are rejected, not normalized.
    """
    require(type(expected_head) is str and re.fullmatch("[0-9a-f]{40}", expected_head), "full producer revision required")
    root = regular_path(root, directory=True)
    require(_git(root, "rev-parse", "HEAD").decode().strip() == expected_head, "HEAD changed")
    require(not _git(root, "status", "--porcelain", "--untracked-files=no"), "tracked source dirty")
    extra = _git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    require(not any(_source_path(p) for p in extra if p), "untracked source inventory")
    entries = []
    for record in _git(root, "ls-tree", "-rz", "--full-tree", expected_head).split(b"\0"):
        if not record:
            continue
        header, encoded_name = record.split(b"\t", 1)
        name = encoded_name.decode("utf-8")
        if not _source_path(name):
            continue
        mode, kind, blob = header.decode().split()
        require(mode in ("100644", "100755") and kind == "blob", "nonregular Git source")
        v.safe_relative_path(name)
        raw = regular_path(root/name).read_bytes()
        committed = _git(root, "cat-file", "blob", blob)
        require(raw == committed, "working bytes differ from pinned Git source: " + name)
        entries.append((name, raw))
    names = {name for name, _ in entries}
    required = {*c.CONFIG_PATHS, *c.SCHEMA_PATHS, c.PLAN_PATH, "src/banto_ai/generator.py",
                *("src/banto_ai/"+name+".py" for name in ("anomaly_v03", "_anomaly_v03_contract", "_anomaly_v03_schema",
                    "_anomaly_v03_numeric", "anomaly_v03_scoring", "anomaly_v03_episodes", "anomaly_v03_materializer",
                    "anomaly_v03_runner", "_anomaly_v03_runtime", "_anomaly_v03_io")), "tools/evaluator/run_anomaly_v03.py"}
    require(required <= names, "required source missing")
    # The normal physics source must retain the registered baseline bytes.
    baseline = _git(root, "show", c.BASE_REVISION+":src/banto_ai/generator.py")
    require(dict(entries)["src/banto_ai/generator.py"] == baseline, "normal generator baseline changed")
    snapshots = {p: dict(entries)[p] for p in (*c.CONFIG_PATHS, *c.SCHEMA_PATHS)}
    v.validate_bundle(snapshots, science_plan_raw=_git(root, "show", c.SCIENCE_REVISION+":"+c.PLAN_PATH),
                      status_plan_raw=_git(root, "show", c.STATUS_REVISION+":"+c.PLAN_PATH))
    return Checkout(root, expected_head, tuple(sorted(entries)))


WINDOWS_POLICY_VERSION = "windows-runtime-policy.1"
FILE_PERSISTENT_ACLS = 0x00000008
WINDOWS_REQUIRED_EXPORTS = {
    "kernel32": ("CreateJobObjectW", "SetInformationJobObject", "AssignProcessToJobObject",
                 "IsProcessInJob", "QueryInformationJobObject", "TerminateJobObject", "CloseHandle",
                 "CreateProcessW", "InitializeProcThreadAttributeList", "UpdateProcThreadAttribute",
                 "DeleteProcThreadAttributeList", "MoveFileExW", "GetVolumePathNameW",
                 "GetVolumeInformationW", "GetDriveTypeW"),
    "advapi32": ("GetNamedSecurityInfoW", "SetNamedSecurityInfoW", "AccessCheck"),
}
WINDOWS_EXPORT_IDS = tuple(library + "." + name for library, names in WINDOWS_REQUIRED_EXPORTS.items() for name in names)


def validate_windows_host(*, major, minor, build, ubr, product_type, architecture, edition, release):
    """OS support boundary; exact release/build/UBR remain observations."""
    require(all(type(value) is int and 0 <= value <= 0xffffffff
                for value in (major, minor, build, ubr, product_type)), "invalid Windows version observation")
    require((major, minor, product_type, architecture) == (10, 0, 1, "AMD64") and build >= 22000,
            "unsupported Windows runtime")
    require(all(type(value) is str and 0 < len(value) <= 128 for value in (edition, release)),
            "invalid Windows release observation")


def windows_capabilities(libraries, filesystem_flags):
    """Export/volume availability only; never exercise Job, ACL or publication."""
    require(type(filesystem_flags) is int and 0 <= filesystem_flags <= 0xffffffff
            and filesystem_flags & FILE_PERSISTENT_ACLS, "persistent ACL support required")
    exports = []
    for library, names in WINDOWS_REQUIRED_EXPORTS.items():
        for name in names:
            require(callable(getattr(libraries[library], name, None)), "required Windows API unavailable")
            exports.append(library + "." + name)
    return {"policy_version": WINDOWS_POLICY_VERSION, "filesystem_flags": filesystem_flags,
            "api_exports": exports, "behavior_verified": False}


def require_same_runtime(expected: bytes, observed: dict):
    """An OS update may start a new run, but cannot replace a bound run snapshot."""
    require(type(expected) is bytes and 0 < len(expected) <= 32768, "runtime snapshot required")
    require(v.canonical_json(observed) == expected, "runtime changed during run")


def probe_runtime(parent: Path, *, expected_snapshot: dict | None = None) -> dict:
    """Read only. No output claim, data generation, native write or ACL mutation."""
    expected = v.canonical_json(expected_snapshot) if expected_snapshot is not None else None
    if expected is not None:
        require(0 < len(expected) <= 32768, "runtime snapshot byte limit")
    require(os.name == "nt" and platform.system() == "Windows", "unsupported_runtime")
    require(platform.machine() == "AMD64" and platform.python_implementation() == "CPython"
            and platform.python_version() == "3.14.0" and struct.calcsize("P") == 8
            and not sysconfig.get_config_var("Py_GIL_DISABLED")
            and platform.python_compiler() == "MSC v.1944 64 bit (AMD64)"
            and sys._git == ("CPython", "tags/v3.14.0", "ebf955d"), "unsupported_runtime")
    import ctypes
    import winreg
    from ctypes import wintypes

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
        build = int(winreg.QueryValueEx(key, "CurrentBuildNumber")[0])
        ubr = winreg.QueryValueEx(key, "UBR")[0]
        edition = winreg.QueryValueEx(key, "EditionID")[0]
        release = winreg.QueryValueEx(key, "DisplayVersion")[0]
    version = sys.getwindowsversion()
    require(version.build == build, "Windows version sources disagree")
    validate_windows_host(major=version.major, minor=version.minor, build=build, ubr=ubr,
                          product_type=version.product_type, architecture=platform.machine(),
                          edition=edition, release=release)
    executable = regular_path(Path(sys.executable))
    dll = regular_path(Path(sys.base_prefix)/"python314.dll")
    parent = regular_path(parent, directory=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumePathNameW.restype = wintypes.BOOL
    kernel.GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    kernel.GetDriveTypeW.argtypes, kernel.GetDriveTypeW.restype = [wintypes.LPCWSTR], wintypes.UINT
    volume, filesystem = ctypes.create_unicode_buffer(32768), ctypes.create_unicode_buffer(128)
    require(kernel.GetVolumePathNameW(str(parent), volume, len(volume)), "unsupported_runtime")
    require(kernel.GetDriveTypeW(volume.value) == 3, "unsupported_runtime")
    flags = wintypes.DWORD()
    require(kernel.GetVolumeInformationW(volume.value, None, 0, None, None, ctypes.byref(flags), filesystem, len(filesystem)), "unsupported_runtime")
    require(filesystem.value == "NTFS", "local NTFS required")
    capabilities = windows_capabilities({"kernel32": kernel, "advapi32": security}, flags.value)
    observed = {"os": "Windows 11", "os_edition": edition, "product_type": version.product_type,
        "runtime_policy": capabilities,
        "release": release, "architecture": platform.machine(), "os_major": version.major, "os_minor": version.minor,
        "os_build": build, "os_ubr": ubr, "filesystem": "local-"+filesystem.value,
        "implementation": platform.python_implementation(), "python_version": platform.python_version(),
        "pointer_bits": struct.calcsize("P")*8, "gil_disabled": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "compiler": "MSC v.1944", "source_tag": "v3.14.0:ebf955d",
        "python_exe_raw_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "python_dll_raw_sha256": hashlib.sha256(dll.read_bytes()).hexdigest()}
    python_fields = ("implementation", "python_version", "pointer_bits", "gil_disabled", "compiler", "source_tag",
                     "python_exe_raw_sha256", "python_dll_raw_sha256")
    pin = c.formal_runtime()
    require(all(observed[field] == pin[field] for field in python_fields), "unsupported Python basic pin")
    if expected is not None:
        require_same_runtime(expected, observed)
    # This is a basic pin probe, NOT S4's full loaded-DLL/CRT/stdlib inventory.
    return observed


def require_campaign_acceptance() -> None:
    """S4 must supply and freeze independently audited acceptance before opening.

    Intentionally no boolean override, environment switch, reduced campaign or
    alternate formal output path. Implementing S3 does not grant S4/S5 authority.
    """
    raise IntegrityError("s4_acceptance_not_frozen")


def acceptance_requirements() -> dict:
    return {"status": "not_completed", "linux_python": ["3.14"],
            "windows_python": ["3.14.0"], "native_publisher": "not_accepted",
            "protected_dacl": "not_accepted", "independent_token_access_check": "not_accepted",
            "full_runtime_inventory": "not_frozen", "consumer_revision": "not_frozen"}
