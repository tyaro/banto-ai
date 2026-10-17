"""Mac-only resource observations for new demand work; no Windows equivalence."""

import ctypes
import os
import sys
import time


class _UsageV0(ctypes.Structure):
    # Apple xnu bsd/sys/resource.h, RUSAGE_INFO_V0 (96 bytes).
    _fields_ = [('uuid', ctypes.c_uint8 * 16)] + [
        (name, ctypes.c_uint64) for name in (
            'user_time', 'system_time', 'pkg_idle_wkups', 'interrupt_wkups',
            'pageins', 'wired_size', 'resident_size', 'phys_footprint',
            'proc_start_abstime', 'proc_exit_abstime')]


def memory_observation():
    if sys.platform != 'darwin':
        raise RuntimeError('Mac resource observation requires Darwin')
    import resource
    if ctypes.sizeof(_UsageV0) != 96:
        raise RuntimeError('unexpected rusage_info_v0 ABI')
    library = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    probe = library.proc_pid_rusage
    probe.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    probe.restype = ctypes.c_int
    usage = _UsageV0()
    if probe(os.getpid(), 0, ctypes.byref(usage)) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if usage.phys_footprint <= 0 or peak_rss <= 0:
        raise RuntimeError('unavailable Mac memory observation')
    return {'phys_footprint_bytes': int(usage.phys_footprint),
            'resident_bytes': int(usage.resident_size), 'peak_rss_bytes': peak_rss,
            'footprint_source': 'libproc.proc_pid_rusage.RUSAGE_INFO_V0',
            'peak_source': 'Darwin resource.getrusage(RUSAGE_SELF).ru_maxrss',
            'windows_private_bytes_equivalent': False}


class MacCheckpoint:
    """Sampled checkpoints, not a hard OS memory cap or campaign authorization."""

    def __init__(self, *, seconds=60, memory_bytes=2 * 1024**3):
        if (type(seconds) not in (int, float) or not 0 < seconds <= 900
                or type(memory_bytes) is not int or not 0 < memory_bytes <= 2 * 1024**3):
            raise ValueError('invalid Mac checkpoint limits')
        self.started = time.monotonic()
        self.seconds, self.memory_bytes = seconds, memory_bytes
        self.max_footprint = self.max_rss = 0

    def check(self):
        sample = memory_observation()
        self.max_footprint = max(self.max_footprint, sample['phys_footprint_bytes'])
        self.max_rss = max(self.max_rss, sample['peak_rss_bytes'])
        elapsed = time.monotonic() - self.started
        if elapsed > self.seconds or max(self.max_footprint, self.max_rss) > self.memory_bytes:
            raise RuntimeError('Mac resource checkpoint exceeded; preserve evidence')
        return {**sample, 'elapsed_seconds': elapsed,
                'sampled_peak_footprint_bytes': self.max_footprint,
                'peak_rss_bytes': self.max_rss,
                'limits': {'wall_seconds': self.seconds, 'each_memory_metric_bytes': self.memory_bytes},
                'hard_os_limit': False, 'formal_permission': False}
