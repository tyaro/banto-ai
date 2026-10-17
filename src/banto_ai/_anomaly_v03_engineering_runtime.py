"""Read-only Windows observations and bounded single-worker supervision helpers."""
from __future__ import annotations

import ctypes
import math
import os
import platform
import shutil
import struct
import sys
import sysconfig
from pathlib import Path

from . import anomaly_v03_engineering_contract as policy
from . import _anomaly_v03_runtime as rt
from .anomaly_v03_materializer import sha


class ResourceStop(rt.IntegrityError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _windows():
    rt.require(os.name == "nt", "Windows engineering worker required")
    from ctypes import wintypes as w
    return ctypes.WinDLL("kernel32", use_last_error=True), w


def probe_runtime(parent: Path):
    """Actual observation, with the adopted policy's OS build/UBR relaxation."""
    kernel, w = _windows()
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
        values = {name: winreg.QueryValueEx(key, name)[0] for name in
                  ("CurrentBuildNumber", "UBR", "EditionID", "DisplayVersion")}
    parent = rt.regular_path(parent, directory=True)
    kernel.GetVolumePathNameW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD]
    kernel.GetVolumePathNameW.restype = w.BOOL
    kernel.GetVolumeInformationW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD,
        ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD), w.LPWSTR, w.DWORD]
    kernel.GetVolumeInformationW.restype = w.BOOL
    kernel.GetDriveTypeW.argtypes, kernel.GetDriveTypeW.restype = [w.LPCWSTR], w.UINT
    volume, filesystem = ctypes.create_unicode_buffer(32768), ctypes.create_unicode_buffer(128)
    rt.require(kernel.GetVolumePathNameW(str(parent), volume, len(volume)), "volume observation failed")
    rt.require(kernel.GetDriveTypeW(volume.value) == 3, "local drive required")
    rt.require(kernel.GetVolumeInformationW(volume.value, None, 0, None, None, None, filesystem, len(filesystem)), "filesystem observation failed")
    version = sys.getwindowsversion()
    compiler = platform.python_compiler()
    rt.require(compiler == "MSC v.1944 64 bit (AMD64)" and sys._git == ("CPython", "tags/v3.14.0", "ebf955d"), "Python build changed")
    build = int(values["CurrentBuildNumber"])
    observed = {"os": "Windows 11 Pro" if values["EditionID"] == "Professional" and build >= 22000 else values["EditionID"],
        "release": values["DisplayVersion"], "architecture": platform.machine(),
        "os_major": version.major, "os_minor": version.minor, "os_build": build, "os_ubr": values["UBR"],
        "filesystem": "local-" + filesystem.value, "implementation": platform.python_implementation(),
        "python_version": platform.python_version(), "pointer_bits": struct.calcsize("P") * 8,
        "gil_disabled": bool(sysconfig.get_config_var("Py_GIL_DISABLED")), "compiler": "MSC v.1944",
        "source_tag": "v3.14.0:ebf955d",
        "python_exe_raw_sha256": sha(rt.regular_path(Path(sys.executable)).read_bytes()),
        "python_dll_raw_sha256": sha(rt.regular_path(Path(sys.base_prefix) / "python314.dll").read_bytes())}
    policy.validate_runtime(observed)
    return observed


def memory_bytes(process_handle=None):
    """Private usage and OS peak pagefile usage for the owned process only."""
    kernel, w = _windows()
    class Memory(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("peak_working", "working", "peak_paged", "paged",
                "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile", "private")]
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(Memory), w.DWORD]
    psapi.GetProcessMemoryInfo.restype = w.BOOL
    value = Memory()
    value.cb = ctypes.sizeof(value)
    rt.require(psapi.GetProcessMemoryInfo(process_handle if process_handle is not None else kernel.GetCurrentProcess(),
               ctypes.byref(value), value.cb), "process memory observation failed")
    return {"private_bytes": value.private, "peak_private_bytes": max(value.private, value.peak_pagefile)}


def free_resources(parent):
    kernel, w = _windows()
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", w.DWORD), ("load", w.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in ("total_phys", "avail_phys", "total_page",
                "avail_page", "total_virtual", "avail_virtual", "avail_extended")]
    kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MemoryStatus)]
    kernel.GlobalMemoryStatusEx.restype = w.BOOL
    value = MemoryStatus()
    value.length = ctypes.sizeof(value)
    rt.require(kernel.GlobalMemoryStatusEx(ctypes.byref(value)), "system memory observation failed")
    return {"free_ram_bytes": value.avail_phys, "free_disk_bytes": shutil.disk_usage(parent).free}


def require_start_resources(parent):
    observed = free_resources(parent)
    budget = policy.limits()
    if (observed["free_ram_bytes"] < budget["minimum_free_ram_bytes"]
            or observed["free_disk_bytes"] < budget["minimum_free_disk_bytes"]):
        raise ResourceStop("insufficient_resources")
    return observed


def check_budget(elapsed, peak_private, output_bytes):
    rt.require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0
               and type(peak_private) is int and peak_private >= 0
               and type(output_bytes) is int and output_bytes >= 0, "invalid resource measurement")
    budget = policy.limits()
    for value, cap, reason in ((elapsed, budget["wall_seconds"], "time_limit"),
                             (peak_private, budget["worker_private_bytes"], "memory_limit"),
                             (output_bytes, budget["output_bytes"], "output_limit")):
        if value > cap:
            raise ResourceStop(reason)
