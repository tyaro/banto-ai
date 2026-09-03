"""TimesFM 3 CPU evaluation preflight.

This module intentionally uses only the Python standard library.  It inspects
only the explicitly supplied cache path; it never searches the repository or
any user/customer data location.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any, Mapping

MIN_PYTHON = (3, 12)
MIN_RAM_BYTES = 8 * 1024**3
MIN_DISK_BYTES = 4 * 1024**3
OPTIONAL_PACKAGES = ("timesfm3", "timesfm", "torch", "numpy")


def _memory_bytes() -> tuple[int | None, int | None]:
    """Return total/available RAM where the standard library can provide it."""
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_phys", ctypes.c_ulonglong),
                    ("avail_phys", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong),
                    ("avail_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("avail_virtual", ctypes.c_ulonglong),
                    ("avail_extended", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.total_phys), int(status.avail_phys)
        except (AttributeError, OSError, TypeError):
            pass
        return None, None
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        total = os.sysconf("SC_PHYS_PAGES")
        available = os.sysconf("SC_AVPHYS_PAGES")
        return int(page * total), int(page * available)
    except (AttributeError, OSError, ValueError):
        return None, None


def _disk_available(path: Path) -> int | None:
    try:
        probe = path if path.exists() else path.parent
        return int(shutil.disk_usage(probe).free)
    except OSError:
        return None


def _package_status() -> dict[str, bool]:
    return {
        name: importlib.util.find_spec(name) is not None
        for name in OPTIONAL_PACKAGES
    }


def collect_preflight(
    cache_dir: Path,
    *,
    python_version: tuple[int, int, int] | None = None,
    total_ram_bytes: int | None = None,
    available_disk_bytes: int | None = None,
    optional_packages: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Collect a JSON-serializable preflight report and fail-closed checks."""
    cache_dir = Path(cache_dir).expanduser().resolve()
    version = sys.version_info if python_version is None else python_version
    detected_total_ram, detected_available_ram = _memory_bytes()
    total_ram = detected_total_ram if total_ram_bytes is None else total_ram_bytes
    disk_free = (
        _disk_available(cache_dir)
        if available_disk_bytes is None
        else available_disk_bytes
    )
    packages = dict(_package_status() if optional_packages is None else optional_packages)
    python_ok = tuple(version[:2]) >= MIN_PYTHON
    ram_ok = total_ram is not None and total_ram >= MIN_RAM_BYTES
    disk_ok = disk_free is not None and disk_free >= MIN_DISK_BYTES
    checks = {
        "python": {"ok": python_ok, "minimum": "3.12", "detected": ".".join(map(str, version))},
        "ram": {"ok": ram_ok, "minimum_bytes": MIN_RAM_BYTES, "total_bytes": total_ram},
        "disk": {"ok": disk_ok, "minimum_free_bytes": MIN_DISK_BYTES, "free_bytes": disk_free},
    }
    return {
        "schema_version": "0.1",
        "status": "pass" if all(check["ok"] for check in checks.values()) else "fail",
        "evaluation": {"device": "cpu", "cuda_required": False, "cuda_failure_policy": "not-required"},
        "os": {
            "name": os.name,
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "python": checks["python"],
        "cpu": {"count": os.cpu_count(), "processor": platform.processor()},
        "ram": checks["ram"],
        "disk": {**checks["disk"], "path": str(cache_dir)},
        "optional_packages": packages,
        "checkpoint_cache": {
            "path": str(cache_dir),
            "exists": cache_dir.exists(),
            "is_directory": cache_dir.is_dir(),
            "has_entries": cache_dir.is_dir() and any(cache_dir.iterdir()),
        },
        "checks": checks,
        "scope": "Only the explicitly supplied cache path was inspected; repository and customer data were not searched.",
    }


def human_summary(report: Mapping[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        f"TimesFM 3 CPU preflight: {str(report['status']).upper()}",
        f"OS: {report['os']['system']} {report['os']['release']} ({report['os']['machine']})",
        f"Python: {report['python']['detected']} (minimum 3.12) [{'PASS' if checks['python']['ok'] else 'FAIL'}]",
        f"CPU: {report['cpu']['count'] or 'unknown'} logical cores",
        f"RAM: {report['ram']['total_bytes'] or 'unknown'} bytes (minimum {report['ram']['minimum_bytes']}) [{'PASS' if checks['ram']['ok'] else 'FAIL'}]",
        f"Free disk at cache path: {report['disk']['free_bytes'] or 'unknown'} bytes (minimum {report['disk']['minimum_free_bytes']}) [{'PASS' if checks['disk']['ok'] else 'FAIL'}]",
        f"Cache: {report['checkpoint_cache']['path']} (exists={report['checkpoint_cache']['exists']}, entries={report['checkpoint_cache']['has_entries']})",
        "CUDA: not required for this CPU evaluation",
        "Optional packages: " + ", ".join(f"{name}={'yes' if present else 'no'}" for name, present in report["optional_packages"].items()),
        "Scope: repository and customer data were not searched.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="preflight.py")
    parser.add_argument("--cache-dir", required=True, help="explicit external checkpoint cache path")
    parser.add_argument("--format", choices=("both", "human", "json"), default="both")
    args = parser.parse_args(argv)
    report = collect_preflight(Path(args.cache_dir))
    if args.format in ("both", "human"):
        print(human_summary(report))
    if args.format == "both":
        print("\n--- machine-readable JSON ---")
    if args.format in ("both", "json"):
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
