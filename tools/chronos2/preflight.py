"""Chronos-2専用CPU評価の標準ライブラリだけの事前確認。"""

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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tools.chronos2 import (
    CHECKPOINT_ALLOW_PATTERNS,
    EXPECTED_MODEL_SIZE_BYTES,
    OFFICIAL_PACKAGE_NAME,
    OFFICIAL_PACKAGE_VERSION,
)

MIN_PYTHON = (3, 10)
MIN_RAM_BYTES = 8 * 1024**3
MIN_DISK_BYTES = 4 * 1024**3
OPTIONAL_PACKAGES = ("chronos", "torch", "transformers", "accelerate", "numpy", "pandas")


def _memory_bytes() -> tuple[int | None, int | None]:
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong), ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong), ("avail_extended", ctypes.c_ulonglong)]

            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.total_phys), int(status.avail_phys)
        except (AttributeError, OSError, TypeError):
            pass
        return None, None
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        return int(page * os.sysconf("SC_PHYS_PAGES")), int(page * os.sysconf("SC_AVPHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        return None, None


def _package_status() -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in OPTIONAL_PACKAGES}


def collect_preflight(cache_dir: Path, *, python_version: tuple[int, int, int] | None = None, total_ram_bytes: int | None = None, available_disk_bytes: int | None = None, optional_packages: Mapping[str, bool] | None = None) -> dict[str, Any]:
    cache = Path(cache_dir).expanduser().resolve()
    version = sys.version_info if python_version is None else python_version
    detected_total, _detected_available = _memory_bytes()
    total = detected_total if total_ram_bytes is None else total_ram_bytes
    if available_disk_bytes is None:
        try:
            disk = int(shutil.disk_usage(cache if cache.exists() else cache.parent).free)
        except OSError:
            disk = None
    else:
        disk = available_disk_bytes
    packages = dict(_package_status() if optional_packages is None else optional_packages)
    cache_outside = _outside(cache)
    cache_directory_ok = not cache.exists() or cache.is_dir()
    checks = {
        "python": {"ok": tuple(version[:2]) >= MIN_PYTHON, "minimum": "3.10", "detected": ".".join(map(str, version))},
        "ram": {"ok": total is not None and total >= MIN_RAM_BYTES, "minimum_bytes": MIN_RAM_BYTES, "total_bytes": total},
        "disk": {"ok": disk is not None and disk >= MIN_DISK_BYTES, "minimum_free_bytes": MIN_DISK_BYTES, "free_bytes": disk},
        "cache": {"ok": cache_outside and cache_directory_ok, "path_outside_repository": cache_outside, "directory_ok": cache_directory_ok},
    }
    return {
        "schema_version": "0.1",
        "status": "pass" if all(item["ok"] for item in checks.values()) else "fail",
        "package": {"name": OFFICIAL_PACKAGE_NAME, "version": OFFICIAL_PACKAGE_VERSION},
        "evaluation": {"device": "cpu", "cuda_required": False, "local_files_only": True, "telemetry_disabled": True},
        "os": {"name": os.name, "system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "python": checks["python"],
        "cpu": {"count": os.cpu_count(), "processor": platform.processor()},
        "ram": checks["ram"],
        "disk": {**checks["disk"], "path": str(cache)},
        "optional_packages": packages,
        "checkpoint": {"allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS), "model_size_bytes": EXPECTED_MODEL_SIZE_BYTES},
        "checkpoint_cache": {"path": str(cache), "exists": cache.exists(), "is_directory": cache.is_dir(), "has_entries": cache.is_dir() and any(cache.iterdir())},
        "checks": checks,
        "scope": "Only the explicitly supplied cache path was inspected; repository and customer data were not searched.",
    }


def _outside(path: Path) -> bool:
    from tools.chronos2 import ROOT
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def human_summary(report: Mapping[str, Any]) -> str:
    checks = report["checks"]
    return "\n".join([
        f"Chronos-2 CPU preflight: {str(report['status']).upper()}",
        f"Python: {report['python']['detected']} (minimum 3.10) [{'PASS' if checks['python']['ok'] else 'FAIL'}]",
        f"CPU: {report['cpu']['count'] or 'unknown'} logical cores",
        f"RAM: {report['ram']['total_bytes'] or 'unknown'} bytes [{'PASS' if checks['ram']['ok'] else 'FAIL'}]",
        f"Free disk at cache path: {report['disk']['free_bytes'] or 'unknown'} bytes [{'PASS' if checks['disk']['ok'] else 'FAIL'}]",
        f"Cache: {report['disk']['path']} (outside repository={'yes' if checks['cache']['path_outside_repository'] else 'no'})",
        "Execution: CPU, local_files_only=True, telemetry disabled",
        "Scope: repository and customer data were not searched.",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="preflight.py")
    parser.add_argument("--cache-dir", required=True)
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
