"""Process runtime measurements shared by core and optional evaluation tools."""

from __future__ import annotations

import ctypes
import os
import sys
from typing import Any


def windows_peak_working_set_bytes(*, psapi: Any | None = None, kernel32: Any | None = None) -> int | None:
    """Win32 PeakWorkingSetSize using the complete PROCESS_MEMORY_COUNTERS layout."""
    try:
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        psapi = psapi or ctypes.windll.psapi
        kernel32 = kernel32 or ctypes.windll.kernel32
        get_current_process = kernel32.GetCurrentProcess
        get_current_process.restype = wintypes.HANDLE
        get_memory_info = psapi.GetProcessMemoryInfo
        get_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        get_memory_info.restype = wintypes.BOOL
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        if get_memory_info(get_current_process(), ctypes.byref(counters), counters.cb):
            return int(counters.PeakWorkingSetSize)
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return None


def process_peak_memory_bytes() -> tuple[int | None, str]:
    """Return OS process peak memory and its source, or a clear unavailable marker."""
    if os.name == "nt":
        value = windows_peak_working_set_bytes()
        return value, "os.process_peak_working_set" if value is not None else "unavailable"
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # Linux and the BSDs report KiB; macOS reports bytes.
        value_bytes = value if sys.platform == "darwin" else value * 1024
        return value_bytes, "os.resource.ru_maxrss"
    except (ImportError, AttributeError, OSError, TypeError, ValueError):
        return None, "unavailable"
