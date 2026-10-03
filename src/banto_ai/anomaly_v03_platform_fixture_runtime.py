"""Candidate 26H2 runtime boundary for the isolated, invented platform fixture.

This is deliberately separate from the adopted 25H2 engineering validator and
the frozen formal runtime.  Two Python files are a limited identity check, not
the complete source/runtime closure required for S4 acceptance.
"""
from __future__ import annotations

import ctypes
import hashlib
import platform
import struct
import sys
import sysconfig
from pathlib import Path

from . import _anomaly_v03_runtime as rt
from . import _anomaly_v03_engineering_runtime as engineering


POLICY_ID = 'anomaly-v03-single-writer-platform-v2'
EXPECTED = {
    'os': 'Windows 11 Pro', 'release': '26H2', 'architecture': 'AMD64',
    'os_major': 10, 'os_minor': 0, 'os_build': 26300, 'os_ubr': 9457,
    'filesystem': 'local-NTFS', 'implementation': 'CPython',
    'python_version': '3.14.0', 'pointer_bits': 64, 'gil_disabled': False,
    'compiler': 'MSC v.1944', 'source_tag': 'v3.14.0:ebf955d',
    'python_exe_raw_sha256': '467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec',
    'python_dll_raw_sha256': 'f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a',
}


def validate_runtime(observed):
    """Exact candidate tuple; never infer acceptance from a version range."""
    rt.require(type(observed) is dict and
               rt.v.canonical_json(observed) == rt.v.canonical_json(EXPECTED),
               'unsupported platform fixture runtime')
    return dict(observed)


def probe_runtime(parent: Path):
    """Read the actual host and volume before each owned fixture boundary."""
    kernel, w = engineering._windows()
    import winreg

    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:
        values = {name: winreg.QueryValueEx(key, name)[0] for name in
                  ('CurrentBuildNumber', 'UBR', 'EditionID', 'DisplayVersion')}
    version = sys.getwindowsversion()
    build = int(values['CurrentBuildNumber'])
    rt.require((version.major, version.minor, version.build) == (10, 0, build),
               'platform fixture registry/kernel version mismatch')
    rt.require(platform.python_compiler() == 'MSC v.1944 64 bit (AMD64)' and
               sys._git == ('CPython', 'tags/v3.14.0', 'ebf955d'),
               'platform fixture Python build changed')

    parent = rt.regular_path(Path(parent), directory=True)
    kernel.GetVolumePathNameW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD]
    kernel.GetVolumePathNameW.restype = w.BOOL
    kernel.GetVolumeInformationW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD,
        ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD),
        w.LPWSTR, w.DWORD]
    kernel.GetVolumeInformationW.restype = w.BOOL
    kernel.GetDriveTypeW.argtypes, kernel.GetDriveTypeW.restype = [w.LPCWSTR], w.UINT
    volume, filesystem = ctypes.create_unicode_buffer(32768), ctypes.create_unicode_buffer(128)
    rt.require(kernel.GetVolumePathNameW(str(parent), volume, len(volume)),
               'platform fixture volume observation failed')
    rt.require(kernel.GetDriveTypeW(volume.value) == 3, 'platform fixture local drive required')
    rt.require(kernel.GetVolumeInformationW(volume.value, None, 0, None, None, None,
               filesystem, len(filesystem)), 'platform fixture filesystem observation failed')

    observed = {
        'os': ('Windows 11 Pro' if values['EditionID'] == 'Professional' and build >= 22000
               else values['EditionID']),
        'release': values['DisplayVersion'], 'architecture': platform.machine(),
        'os_major': version.major, 'os_minor': version.minor, 'os_build': build,
        'os_ubr': values['UBR'], 'filesystem': 'local-' + filesystem.value,
        'implementation': platform.python_implementation(),
        'python_version': platform.python_version(),
        'pointer_bits': struct.calcsize('P') * 8,
        'gil_disabled': bool(sysconfig.get_config_var('Py_GIL_DISABLED')),
        'compiler': 'MSC v.1944', 'source_tag': 'v3.14.0:ebf955d',
        'python_exe_raw_sha256': hashlib.sha256(
            rt.regular_path(Path(sys.executable)).read_bytes()).hexdigest(),
        'python_dll_raw_sha256': hashlib.sha256(
            rt.regular_path(Path(sys.base_prefix) / 'python314.dll').read_bytes()).hexdigest(),
    }
    return validate_runtime(observed)
