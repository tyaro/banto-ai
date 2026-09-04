"""Standard-library preflight for the isolated Toto 2.0 CPU environment."""
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from tools.toto2 import CHECKPOINT_ALLOW_PATTERNS, EXPECTED_MODEL_SIZE_BYTES, OFFICIAL_PACKAGE_NAME, OFFICIAL_PACKAGE_VERSION  # noqa: E402

MIN_PYTHON = (3, 12)
MIN_RAM_BYTES = 4 * 1024**3
MIN_DISK_BYTES = 2 * 1024**3
OPTIONAL_PACKAGES = ("toto2", "toto_models", "torch", "numpy", "huggingface_hub", "safetensors")


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


def _outside(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def collect_preflight(cache_dir: Path, *, python_version: tuple[int, int, int] | None = None, total_ram_bytes: int | None = None, available_disk_bytes: int | None = None, optional_packages: Mapping[str, bool] | None = None) -> dict[str, Any]:
    cache = Path(cache_dir).expanduser().resolve()
    version = sys.version_info if python_version is None else python_version
    detected_total, _ = _memory_bytes()
    total = detected_total if total_ram_bytes is None else total_ram_bytes
    if available_disk_bytes is None:
        try:
            disk = int(shutil.disk_usage(cache if cache.exists() else cache.parent).free)
        except OSError:
            disk = None
    else:
        disk = available_disk_bytes
    packages = dict(optional_packages or {name: importlib.util.find_spec(name) is not None for name in OPTIONAL_PACKAGES})
    checks = {
        "python": {"ok": tuple(version[:2]) >= MIN_PYTHON, "minimum": "3.12", "detected": ".".join(map(str, version))},
        "ram": {"ok": total is not None and total >= MIN_RAM_BYTES, "minimum_bytes": MIN_RAM_BYTES, "total_bytes": total},
        "disk": {"ok": disk is not None and disk >= MIN_DISK_BYTES, "minimum_free_bytes": MIN_DISK_BYTES, "free_bytes": disk},
        "cache": {"ok": _outside(cache) and (not cache.exists() or cache.is_dir()), "path_outside_repository": _outside(cache), "directory_ok": not cache.exists() or cache.is_dir()},
    }
    return {"schema_version": "0.1", "status": "pass" if all(check["ok"] for check in checks.values()) else "fail", "package": {"name": OFFICIAL_PACKAGE_NAME, "version": OFFICIAL_PACKAGE_VERSION}, "evaluation": {"device": "cpu", "batch_size": 1, "local_files_only": True, "decode_block_size": None, "telemetry_disabled": True}, "checkpoint": {"allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS), "model_size_bytes": EXPECTED_MODEL_SIZE_BYTES}, "python": checks["python"], "cpu": {"count": os.cpu_count(), "processor": platform.processor()}, "ram": checks["ram"], "disk": {**checks["disk"], "path": str(cache)}, "optional_packages": packages, "checks": checks, "scope": "Only the explicitly supplied cache path was inspected; repository and customer data were not searched."}


def human_summary(report: Mapping[str, Any]) -> str:
    checks = report["checks"]
    return "\n".join([f"Toto 2.0 4M CPU preflight: {str(report['status']).upper()}", f"Python: {report['python']['detected']} (minimum 3.12) [{'PASS' if checks['python']['ok'] else 'FAIL'}]", f"Cache: {report['disk']['path']} (outside repository={'yes' if checks['cache']['path_outside_repository'] else 'no'})", "Execution: CPU, batch_size=1, local_files_only=True, decode_block_size=None, telemetry disabled"])


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
