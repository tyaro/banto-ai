"""S4-A read-only inspection, not a frozen/closed runtime or native acceptance.

No ACL/token mutation, output claim, data generation, installation or file write.
File contents are hashed in bounded chunks; only descriptors are accumulated.
Capture is an observation: no immutability or executed-code attestation is implied.
"""

from __future__ import annotations

import ctypes
import hashlib
import importlib.machinery
import os
import platform
import re
import shutil
import site
import stat
import struct
import sys
import sysconfig
import time
from datetime import datetime, timezone
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_acceptance as a
from . import _anomaly_v03_contract as c
from . import _anomaly_v03_runtime as rt

CHUNK_SIZE = 1024 * 1024


def _stamp(metadata):
    rt.require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_ino != 0, "nonregular runtime/source object")
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)


def hash_file(path: Path, logical: str):
    """Reject links/reparse/identity changes; never buffer a whole DLL/stdlib file."""
    if logical != a.WORKFLOW:
        v.safe_relative_path(logical)
    path = rt.regular_path(path)
    before = _stamp(path.lstat())
    digest, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        opened = _stamp(os.fstat(stream.fileno()))
        # Windows lstat/fstat can expose different ctime interpretations. Bind
        # identity/size/mtime across APIs, but compare each API's ctime to itself.
        rt.require(opened[:4] == before[:4], "file changed before hash")
        while block := stream.read(CHUNK_SIZE):
            digest.update(block)
            count += len(block)
        rt.require(_stamp(os.fstat(stream.fileno())) == opened, "file changed during hash")
    rt.require(_stamp(rt.regular_path(path).lstat()) == before and count == before[2], "file changed after hash")
    return {"path": logical, "raw_sha256": digest.hexdigest(), "byte_count": count}


def _native_regular_path(path):
    # Only native objects from OS module enumeration use this helper. Sources,
    # configs, schemas and the Python executable retain the single-link helper.
    links = path.lstat().st_nlink
    rt.require(links >= 1, "invalid native link count")
    return rt.regular_path(path, links=links)


def _native_local(path):
    if os.name == "nt":
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetVolumePathNameW.argtypes, kernel.GetVolumePathNameW.restype = [w.LPCWSTR, w.LPWSTR, w.DWORD], w.BOOL
        kernel.GetDriveTypeW.argtypes, kernel.GetDriveTypeW.restype = [w.LPCWSTR], w.UINT
        volume = ctypes.create_unicode_buffer(32768)
        rt.require(kernel.GetVolumePathNameW(str(path), volume, len(volume))
                   and kernel.GetDriveTypeW(volume.value) == 3, "nonlocal native file")
    else:
        mounts = []
        with open("/proc/self/mountinfo", encoding="utf-8") as stream:
            for line in stream:
                left, right = line.split(" - ", 1)
                mount = Path(left.split()[4].replace("\\040", " ").replace("\\134", "\\"))
                if path == mount or mount in path.parents:
                    mounts.append((len(mount.parts), right.split()[0]))
        rt.require(mounts and max(mounts)[1] in ("ext4", "xfs", "btrfs"), "nonlocal native file")


def _native_stamp(metadata):
    rt.require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink >= 1 and metadata.st_ino != 0, "nonregular native object")
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns,
            metadata.st_ctime_ns, metadata.st_nlink)


def hash_native(path, logical):
    """Observe loaded native hardlinks, never claim alias immutability/acceptance."""
    v.safe_relative_path(logical)
    rt.require(logical == "native/"+path.name, "native logical path mismatch")
    path = _native_regular_path(path)
    _native_local(path)
    before = _native_stamp(path.lstat())
    digest, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        opened = _native_stamp(os.fstat(stream.fileno()))
        rt.require(opened[:4] == before[:4] and opened[5] == before[5], "native changed before hash")
        while block := stream.read(CHUNK_SIZE):
            digest.update(block)
            count += len(block)
        rt.require(_native_stamp(os.fstat(stream.fileno())) == opened, "native changed during hash")
    rt.require(_native_stamp(_native_regular_path(path).lstat()) == before and count == before[2], "native changed after hash")
    row = {"path": logical, "raw_sha256": digest.hexdigest(), "byte_count": count}
    # Absolute path/file IDs/link counts are provenance only, outside equivalence.
    # Unknown or user-writable images are not promoted to a trusted runtime.
    observed = {"path": logical, "physical_path": str(path), "device": before[0], "inode": before[1],
                "nlink": before[5], "trust_status": "not_accepted"}
    return row, observed


def _clean(root, expected_head):
    rt.require(type(expected_head) is str and re.fullmatch("[a-f0-9]{40}", expected_head), "full source revision required")
    rt.require(rt._git(root, "rev-parse", "HEAD").decode().strip() == expected_head, "HEAD changed")
    rt.require(not rt._git(root, "status", "--porcelain", "--untracked-files=no"), "tracked source dirty")
    names = rt._git(root, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    rt.require(not any(rt._source_path(name) or name.startswith(".github/workflows/") for name in names if name), "untracked source/workflow")


def capture_sources(root, expected_head):
    """Extend S3 source coverage without weakening its clean/Git/frozen checks.

    Missing shallow historical objects fail closed; no network fetch is attempted.
    Hold at most one source blob plus the small frozen configuration bundle.
    """
    root = rt.regular_path(root, directory=True)
    _clean(root, expected_head)
    entries, bundle = [], {}
    for record in rt._git(root, "ls-tree", "-rz", "--full-tree", expected_head).split(b"\0"):
        if not record:
            continue
        header, encoded = record.split(b"\t", 1)
        name = encoded.decode("utf-8")
        if not (rt._source_path(name) or name == a.WORKFLOW):
            continue
        mode, kind, blob = header.decode().split()
        rt.require(mode in ("100644", "100755") and kind == "blob", "nonregular Git source")
        row = hash_file(root/name, name)
        raw = rt._git(root, "cat-file", "blob", blob)
        rt.require(row["byte_count"] == len(raw) and row["raw_sha256"] == hashlib.sha256(raw).hexdigest(), "working bytes differ from Git blob")
        if name in (*c.CONFIG_PATHS, *c.SCHEMA_PATHS):
            bundle[name] = raw
        if name == "src/banto_ai/generator.py":
            rt.require(raw == rt._git(root, "show", c.BASE_REVISION+":"+name), "normal generator baseline changed")
        entries.append(row)
    required = {*a.REQUIRED_PRODUCER_PATHS, a.WORKFLOW}
    rt.require(required <= {row["path"] for row in entries}, "required engineering source missing")
    v.validate_bundle(bundle, science_plan_raw=rt._git(root, "show", c.SCIENCE_REVISION+":"+c.PLAN_PATH),
                      status_plan_raw=rt._git(root, "show", c.STATUS_REVISION+":"+c.PLAN_PATH))
    _clean(root, expected_head)
    return sorted(entries, key=lambda row: row["path"])


def stdlib_paths():
    root = rt.regular_path(Path(sysconfig.get_path("stdlib")), directory=True)
    paths, pending = [], [root]
    while pending:
        directory = pending.pop()
        rt.regular_path(directory, directory=True)
        for path in sorted(directory.iterdir()):
            # Third-party installation trees are explicitly outside stdlib scope.
            if path == root/"site-packages":
                continue
            meta = path.lstat()
            rt.require(not stat.S_ISLNK(meta.st_mode) and not getattr(meta, "st_file_attributes", 0) & 0x400, "reparse in stdlib")
            if stat.S_ISDIR(meta.st_mode):
                pending.append(path)
            else:
                rt.regular_path(path)
                paths.append(("stdlib/"+path.relative_to(root).as_posix(), path))
    # Capture the optional interpreter stdlib zip, not arbitrary sys.path values.
    archive = Path(sys.base_prefix)/f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    if archive.exists():
        paths.append(("stdlib-zip/"+archive.name, rt.regular_path(archive)))
    return sorted(paths)


def _windows_modules():
    from ctypes import wintypes as w
    kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [w.HANDLE, ctypes.POINTER(w.HMODULE), w.DWORD, ctypes.POINTER(w.DWORD), w.DWORD]
    psapi.EnumProcessModulesEx.restype = w.BOOL
    kernel.GetModuleFileNameW.argtypes = [w.HMODULE, w.LPWSTR, w.DWORD]
    kernel.GetModuleFileNameW.restype = w.DWORD
    size = 256
    for _ in range(8):
        modules, needed = (w.HMODULE * size)(), w.DWORD()
        rt.require(psapi.EnumProcessModulesEx(kernel.GetCurrentProcess(), modules, ctypes.sizeof(modules), ctypes.byref(needed), 3), "native module enumeration failed")
        if needed.value <= ctypes.sizeof(modules):
            paths = []
            for handle in modules[:needed.value//ctypes.sizeof(w.HMODULE)]:
                name = ctypes.create_unicode_buffer(32768)
                length = kernel.GetModuleFileNameW(handle, name, len(name))
                rt.require(0 < length < len(name), "native module name unavailable")
                paths.append(Path(name.value))
            return paths
        size = needed.value//ctypes.sizeof(w.HMODULE)+32
    raise rt.IntegrityError("unstable native module enumeration")


def native_paths():
    if os.name == "nt":
        paths = _windows_modules()
    else:
        paths = []
        with open("/proc/self/maps", encoding="utf-8") as stream:
            for line in stream:
                fields = line.split(None, 5)
                if len(fields) != 6 or not fields[5].startswith("/"):
                    continue
                path = fields[5].rstrip("\n")
                rt.require(not path.endswith(" (deleted)"), "deleted native mapping")
                if "x" in fields[1]:
                    paths.append(Path(path))
    paths = list(dict.fromkeys(paths))
    pairs = [("native/"+path.name, _native_regular_path(path)) for path in paths]
    rt.require(len({name.casefold() for name, _ in pairs}) == len(pairs), "ambiguous native logical identity")
    return pairs


def _windows_cpu():
    import winreg
    from ctypes import wintypes as w
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
        identity = " | ".join(str(winreg.QueryValueEx(key, name)[0]).strip() for name in ("VendorIdentifier", "Identifier", "ProcessorNameString"))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.IsProcessorFeaturePresent.argtypes, kernel.IsProcessorFeaturePresent.restype = [w.DWORD], w.BOOL
    return identity, sorted(f"PF-{index:03d}" for index in range(64) if kernel.IsProcessorFeaturePresent(index))


def _linux_cpu():
    with open("/proc/cpuinfo", encoding="utf-8") as stream:
        blocks = stream.read().strip().split("\n\n")
    identities, features = set(), None
    for block in blocks:
        values = dict(line.split(":", 1) for line in block.splitlines() if ":" in line)
        values = {key.strip(): value.strip() for key, value in values.items()}
        identities.add(" | ".join(values.get(key, "unknown") for key in ("vendor_id", "cpu family", "model", "stepping", "model name")))
        flags = set(values.get("flags", "").split())
        features = flags if features is None else features & flags
    rt.require(len(identities) == 1 and features, "CPU identity/features unavailable")
    return next(iter(identities)), sorted(features)


def probe_host(root):
    """Compatibility observation; this cannot open the formal runtime guard."""
    rt.require(sys.dont_write_bytecode, "inspection requires disabled bytecode writes")
    rt.require(platform.python_implementation() == "CPython" and sys.version_info[:2] in ((3, 12), (3, 14))
               and struct.calcsize("P") == 8 and not sysconfig.get_config_var("Py_GIL_DISABLED"), "unsupported_runtime")
    root = rt.regular_path(root, directory=True)
    basic = "compatibility-only"
    if os.name == "nt":
        import winreg
        from ctypes import wintypes as w
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            release, edition, build, ubr = (winreg.QueryValueEx(key, name)[0] for name in ("DisplayVersion", "EditionID", "CurrentBuildNumber", "UBR"))
        version = sys.getwindowsversion()
        rt.require((version.major, version.minor, int(build), ubr, edition, release, platform.machine()) ==
                   (10, 0, 26200, 9168, "Professional", "25H2", "AMD64"), "unsupported_runtime")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetVolumePathNameW.argtypes, kernel.GetVolumePathNameW.restype = [w.LPCWSTR, w.LPWSTR, w.DWORD], w.BOOL
        kernel.GetVolumeInformationW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD, w.LPVOID, w.LPVOID, w.LPVOID, w.LPWSTR, w.DWORD]
        kernel.GetVolumeInformationW.restype = w.BOOL
        kernel.GetDriveTypeW.argtypes, kernel.GetDriveTypeW.restype = [w.LPCWSTR], w.UINT
        volume, filesystem = ctypes.create_unicode_buffer(32768), ctypes.create_unicode_buffer(128)
        rt.require(kernel.GetVolumePathNameW(str(root), volume, len(volume)) and kernel.GetDriveTypeW(volume.value) == 3
            and kernel.GetVolumeInformationW(volume.value, None, 0, None, None, None, filesystem, len(filesystem)) and filesystem.value == "NTFS", "unsupported_runtime")
        if sys.version_info[:2] == (3, 14):
            rt.probe_runtime(root)
            basic = "matches-formal-basic-pin"
        host = dict(system="Windows", release=release, version=f"{version.major}.{version.minor}.{build}.{ubr}",
            build=int(build), ubr=ubr, edition=edition, architecture="AMD64", filesystem="NTFS", local_fixed=True)
        cpu, features = _windows_cpu()
        method = "win32-processor-feature-api"
        executable = rt.regular_path(Path(sys.executable))
    else:
        rt.require(sys.platform == "linux" and platform.machine() == "x86_64", "unsupported_runtime")
        distro = platform.freedesktop_os_release()
        rt.require((distro.get("ID"), distro.get("VERSION_ID")) == ("ubuntu", "24.04"), "unsupported_runtime")
        mounts = []
        with open("/proc/self/mountinfo", encoding="utf-8") as stream:
            for line in stream:
                left, right = line.split(" - ", 1)
                mount = Path(left.split()[4].replace("\\040", " ").replace("\\134", "\\"))
                if root == mount or mount in root.parents:
                    mounts.append((len(mount.parts), right.split()[0]))
        filesystem = max(mounts)[1] if mounts else "unknown"
        rt.require(filesystem in ("ext4", "xfs", "btrfs"), "unsupported filesystem observation")
        host = dict(system="Linux", release="24.04", version=platform.release(), build=None, ubr=None,
                    edition="ubuntu", architecture="x86_64", filesystem=filesystem, local_fixed=True)
        cpu, features = _linux_cpu()
        method = "linux-all-processors-intersection"
        # Kernel-reported executing object, not a followed user-controlled alias.
        executable = rt.regular_path(Path(os.readlink("/proc/self/exe")))
    return host, {"architecture": host["architecture"], "identity": cpu, "features": features, "feature_scope": method}, executable, basic


def _startup(root):
    base, stdlib = Path(sys.base_prefix), Path(sysconfig.get_path("stdlib"))
    locations = []
    for entry in sys.path:
        path = Path(entry).absolute() if entry else Path.cwd()
        if path == root/"src": label = "source"
        elif path == root or not entry: label = "cwd"
        elif path == stdlib or stdlib in path.parents: label = "stdlib"
        elif path == base or base in path.parents: label = "python" if path.exists() else "missing-runtime-path"
        else: label = "external-redacted"
        locations.append(label)
    return {"flags": [{"name": name, "value": int(getattr(sys.flags, name))} for name in a.FLAG_NAMES],
            "environment": [{"name": name, "present": name in os.environ} for name in a.ENV_NAMES],
            "import_locations": locations, "user_site_enabled": site.ENABLE_USER_SITE,
            "bytecode_writes_disabled": bool(sys.dont_write_bytecode)}


def extension_paths():
    return {Path(module.__file__).absolute() for module in tuple(sys.modules.values())
            if isinstance(getattr(module, "__file__", None), str)
            and any(module.__file__.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES)}


def collect_receipt(root: Path, expected_head: str):
    """Return an UNACCEPTED observation in memory. All writes remain absent."""
    started = time.monotonic()
    root = Path(root).absolute()
    host, cpu, executable, basic = probe_host(root)  # Reject before source work.
    source_rows = capture_sources(root, expected_head)
    stdlib = stdlib_paths()
    native = native_paths()  # after collector/Win32 imports, not campaign warmup
    bindings = [*stdlib, ("python/"+executable.name, executable)]
    rows = {name: hash_file(path, name) for name, path in bindings}
    native_observations = []
    for name, path in native:
        rows[name], identity = hash_native(path, name)
        native_observations.append(identity)
    native_rows = sorted((rows[name] for name, _ in native), key=lambda row: row["path"])
    extensions = extension_paths()
    native_by_path = {path: name for name, path in native}
    rt.require(extensions <= set(native_by_path), "loaded Python extension absent from native enumeration")
    rt.require(executable in native_by_path, "executing Python image absent from native enumeration")
    loaded_exe = rows[native_by_path[executable]]
    exe_row = rows["python/"+executable.name]
    rt.require((loaded_exe["raw_sha256"], loaded_exe["byte_count"]) ==
               (exe_row["raw_sha256"], exe_row["byte_count"]), "executing Python image mismatch")
    dll = f"native/python{sys.version_info.major}{sys.version_info.minor}.dll" if host["system"] == "Windows" else None
    if dll is not None:
        dll = next((name for name, _ in native if name.casefold() == dll.casefold()), None)
        rt.require(dll is not None, "executing Python DLL missing")
    tag = getattr(sys, "_git", ("", "", ""))
    source_tag = tag[1].removeprefix("tags/")+":"+tag[2] if tag[1] else platform.python_version()
    sources = [{"role": role, "state": "not_collected", "revision": None, "files": []} for role in a.ROLES]
    sources[0].update(state="collected", revision=expected_head, files=[r for r in source_rows if r["path"] != a.WORKFLOW])
    sources[-1].update(state="collected", revision=expected_head, files=[r for r in source_rows if r["path"] == a.WORKFLOW])
    stable = {"platform": host, "python": {"implementation": "CPython", "version": platform.python_version(),
        "compiler": platform.python_compiler(), "gil_disabled": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "source_tag": source_tag, "pointer_bits": struct.calcsize("P")*8, "executable": rows["python/"+executable.name],
        "executable_native_path": native_by_path[executable],
        "loaded_python_dll": dll, "basic_pin": basic}, "cpu": cpu, "startup": _startup(root),
        "stdlib": [rows[name] for name, _ in stdlib], "loaded_native": native_rows,
        "loaded_extensions": sorted((rows[native_by_path[path]] for path in extensions), key=lambda row: row["path"]),
        "sources": sources, "scope": {"phase": "post-probe-import-observation", "closure_verified": False,
            "stdlib_policy": "regular-tree-excluding-site-packages", "native_method": "EnumProcessModulesEx" if host["system"] == "Windows" else "proc-self-maps",
            "limitations": list(a.LIMITATIONS)}}
    # Repeat enumeration and hash contents; no stat-only or import-list shortcut.
    rt.require(stdlib_paths() == stdlib and set(native_paths()) == set(native), "runtime inventory changed")
    for name, path in bindings:
        rt.require(hash_file(path, name) == rows[name], "runtime bytes changed")
    for (name, path), identity in zip(native, native_observations, strict=True):
        rt.require(hash_native(path, name) == (rows[name], identity), "native bytes/identity changed")
    rt.require(capture_sources(root, expected_head) == source_rows and _startup(root) == stable["startup"], "source/startup changed")
    rt.require(probe_host(root) == (host, cpu, executable, basic), "host/CPU changed")
    rt.require(stdlib_paths() == stdlib and set(native_paths()) == set(native)
               and extension_paths() == extensions, "final runtime inventory changed")
    receipt = {"receipt_version": "s4-a.1", "acceptance_status": "not_completed",
        "requirements": dict.fromkeys(a.REQUIREMENTS, "not_completed"), "stable": stable,
        "observation": {"pid": os.getpid(), "observed_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.monotonic()-started, "free_bytes": shutil.disk_usage(root).free,
            "peak_process_bytes": None, "system_commit_bytes": None, "token_ids": [],
            "native_files": sorted(native_observations, key=lambda row: row["path"]),
            "native_load_order": [name for name, _ in native]}}
    digest = v.canonical_sha256(stable)
    a.validate_receipt(receipt, expected_stable_sha256=digest)
    return {"receipt": receipt, "equivalence_sha256": digest, "pin_origin": "self-observation-not-trusted-external-pin"}
