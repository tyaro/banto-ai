"""Engineering runtime snapshots using the existing streaming inventory helpers.

This separate format preserves actual Windows updates without changing S4 pins.
It observes the inspection process after launcher imports, not a runtime closure.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import time

from . import anomaly_v03 as v
from . import anomaly_v03_acceptance as acceptance
from . import anomaly_v03_engineering as engine
from . import anomaly_v03_engineering_contract as policy
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_inventory as inventory
from . import _anomaly_v03_runtime as rt

FORMAT = "anomaly-v03-engineering-runtime-snapshot-v1"
MAX_BYTES = 16 * 1024**2


def validate(value, root, revision):
    """Validate snapshot metadata; fresh collection supplies byte observations."""
    rt.require(type(value) is dict and set(value) == {"format", "source_root", "revision", "runtime", "cpu",
        "startup", "sources", "stdlib", "loaded_native", "loaded_extensions", "native_files", "pid",
        "elapsed_seconds", "scope", "formal_permission", "full_runtime_inventory_complete"}, "snapshot fields")
    engine._same([value["format"], value["source_root"], value["revision"], value["scope"],
        value["formal_permission"], value["full_runtime_inventory_complete"]],
        [FORMAT, str(Path(root).absolute()), revision, "inspection-process-after-launcher-imports", False, False],
        "snapshot binding or scope")
    policy.validate_runtime(value["runtime"])
    rt.require(value["startup"]["bytecode_writes_disabled"] is True, "snapshot requires disabled bytecode writes")
    for key, prefix in (("sources", None), ("stdlib", ("stdlib/", "stdlib-zip/")), ("loaded_native", "native/"), ("loaded_extensions", "native/")):
        rows = value[key]
        rt.require(type(rows) is list and len(rows) <= 100000 and (bool(rows) or key == "loaded_extensions"), "snapshot inventory size")
        for row in rows:
            rt.require(type(row) is dict and set(row) == {"path", "raw_sha256", "byte_count"}, "snapshot file fields")
            rt.require(type(row["byte_count"]) is int and row["byte_count"] >= 0, "snapshot file bytes")
            rt.require(type(row["raw_sha256"]) is str and len(row["raw_sha256"]) == 64
                       and set(row["raw_sha256"]) <= set("0123456789abcdef"), "snapshot file hash")
            if prefix is not None:
                rt.require(row["path"].startswith(prefix), "snapshot inventory namespace")
        acceptance._files(rows)
    native = {row["path"].casefold(): row for row in value["loaded_native"]}
    for row in value["loaded_extensions"]:
        engine._same(native.get(row["path"].casefold()), row, "extension missing from native inventory")
    for name, key in (("python.exe", "python_exe_raw_sha256"), ("python314.dll", "python_dll_raw_sha256")):
        rt.require(native.get("native/" + name, {}).get("raw_sha256") == value["runtime"][key], "snapshot Python image mismatch")
    rt.require({*acceptance.REQUIRED_PRODUCER_PATHS, acceptance.WORKFLOW} <= {row["path"] for row in value["sources"]},
               "snapshot required source inventory")
    return value


def collect(root, revision):
    """Read and re-read sources, stdlib and OS-enumerated native files; no writes."""
    started = time.monotonic()
    root = engine._root(Path(root))
    observed = resources.probe_runtime(root)
    resources.require_start_resources(root)
    cpu = inventory._windows_cpu()
    startup = inventory._startup(root)
    rt.require(startup["bytecode_writes_disabled"] is True, "snapshot requires disabled bytecode writes")
    sources = inventory.capture_sources(root, revision)
    stdlib, native = inventory.stdlib_paths(), inventory.native_paths()
    extensions = inventory.extension_paths()
    paths = {path: name for name, path in native}
    executable = rt.regular_path(Path(sys.executable))
    rt.require(extensions <= set(paths) and executable in paths, "executed image missing from native enumeration")
    standard_rows = [inventory.hash_file(path, name) for name, path in stdlib]
    native_pairs = [inventory.hash_native(path, name) for name, path in native]
    native_rows = {row["path"]: row for row, identity in native_pairs}
    rt.require(inventory.stdlib_paths() == stdlib and set(inventory.native_paths()) == set(native), "snapshot inventory changed")
    for (name, path), expected in zip(stdlib, standard_rows, strict=True):
        engine._same(inventory.hash_file(path, name), expected, "snapshot stdlib bytes changed")
    for (name, path), expected in zip(native, native_pairs, strict=True):
        rt.require(inventory.hash_native(path, name) == expected, "snapshot native bytes or identity changed")
    engine._same(inventory.capture_sources(root, revision), sources, "snapshot source changed")
    engine._same(inventory._startup(root), startup, "snapshot startup changed")
    rt.require(inventory._windows_cpu() == cpu, "snapshot CPU changed")
    engine._same(resources.probe_runtime(root), observed, "snapshot runtime changed")
    rt.require(inventory.stdlib_paths() == stdlib and set(inventory.native_paths()) == set(native)
               and inventory.extension_paths() == extensions, "final snapshot inventory changed")
    result = {"format": FORMAT, "source_root": str(root), "revision": revision, "runtime": observed,
        "cpu": {"identity": cpu[0], "features": cpu[1], "method": "win32-processor-feature-api"},
        "startup": startup, "sources": sources, "stdlib": standard_rows,
        "loaded_native": sorted(native_rows.values(), key=lambda row: row["path"]),
        "loaded_extensions": sorted((native_rows[paths[path]] for path in extensions), key=lambda row: row["path"]),
        "native_files": sorted((identity for row, identity in native_pairs), key=lambda row: row["path"]),
        "pid": os.getpid(), "elapsed_seconds": time.monotonic() - started,
        "scope": "inspection-process-after-launcher-imports", "formal_permission": False,
        "full_runtime_inventory_complete": False}
    resources.require_start_resources(root)
    return validate(result, root, revision)
