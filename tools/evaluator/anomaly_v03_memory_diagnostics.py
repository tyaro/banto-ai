"""External, bounded observations for the pinned v0.3 controller.

Does not import Banto, start evaluations, alter checkpoints or change OS settings.
Load this file explicitly from the saved helper checkout, keeping the pinned
checkout's src first on sys.path. Observation failures never replace audit errors.
"""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
import ctypes
from ctypes import wintypes as w
import datetime
from functools import lru_cache
import json
import os
from pathlib import Path
import threading
import time


class _Performance(ctypes.Structure):
    _fields_ = [("cb", w.DWORD)] + [(key, ctypes.c_size_t) for key in (
        "CommitTotal", "CommitLimit", "CommitPeak", "PhysicalTotal",
        "PhysicalAvailable", "SystemCache", "KernelTotal", "KernelPaged",
        "KernelNonpaged", "PageSize")] + [(key, w.DWORD) for key in (
        "HandleCount", "ProcessCount", "ThreadCount")]


class _Pagefile(ctypes.Structure):
    _fields_ = [("cb", w.DWORD), ("Reserved", w.DWORD)] + [
        (key, ctypes.c_size_t) for key in ("TotalSize", "TotalInUse", "PeakUsage")]


@lru_cache(maxsize=1)
def _memory_api():
    if os.name != "nt":
        raise OSError("Windows memory observations required")
    # Reuse ctypes types/prototypes; repeated samples must not grow type caches.
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetPerformanceInfo.argtypes = [ctypes.POINTER(_Performance), w.DWORD]
    psapi.GetPerformanceInfo.restype = w.BOOL
    callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.LPVOID, ctypes.POINTER(_Pagefile), w.LPCWSTR)
    psapi.EnumPageFilesW.argtypes = [callback_type, w.LPVOID]
    psapi.EnumPageFilesW.restype = w.BOOL
    return psapi, callback_type


def windows_memory():
    """System commit and pagefiles, in bytes; no pagefile contents are opened."""
    psapi, callback_type = _memory_api()
    value = _Performance()
    value.cb = ctypes.sizeof(value)
    if not psapi.GetPerformanceInfo(ctypes.byref(value), value.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    page = value.PageSize
    result = {"commit_total_bytes": value.CommitTotal * page,
              "commit_limit_bytes": value.CommitLimit * page,
              "commit_peak_since_boot_bytes": value.CommitPeak * page,
              "commit_headroom_bytes": (value.CommitLimit - value.CommitTotal) * page,
              "physical_available_bytes": value.PhysicalAvailable * page,
              "physical_total_bytes": value.PhysicalTotal * page,
              "page_size_bytes": page}
    entries, callback_failed = [], False

    @callback_type
    def record(_context, info, name):
        nonlocal callback_failed
        # Never let a Python exception escape a ctypes callback.
        try:
            entries.append({"name": name, "allocated_bytes": info.contents.TotalSize * page,
                            "in_use_bytes": info.contents.TotalInUse * page,
                            "peak_in_use_bytes": info.contents.PeakUsage * page})
            return True
        except Exception:
            callback_failed = True
            return False

    if not psapi.EnumPageFilesW(record, None) or callback_failed:
        result["pagefiles_error"] = "callback_failed" if callback_failed else f"winerror:{ctypes.get_last_error()}"
    else:
        result["pagefiles"] = entries
    return result


def exception_details(error):
    """Keep only bounded frame locations, never frame locals or source lines."""
    chain, seen = [], set()
    while error is not None and len(chain) < 4 and id(error) not in seen:
        seen.add(id(error))
        frames = deque(maxlen=32)
        trace = error.__traceback__
        while trace is not None:
            code = trace.tb_frame.f_code
            frames.append({"file": code.co_filename[-512:], "function": code.co_name[:128],
                           "line": trace.tb_lineno})
            trace = trace.tb_next
        try:
            message = str(error)[:512]
        except Exception:
            message = "<message unavailable>"
        chain.append({"type": type(error).__name__, "message": message, "frames": list(frames)})
        error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    return chain


class Diagnostics:
    """One exclusive JSONL file, optionally shared with a minute sampler.

    No monitor thread is created. Call sample() from the existing wrapper's
    monitor. A failed/capped log is diagnostic evidence loss, never audit success.
    Startup should require a successful sample before any long work is launched.
    """
    def __init__(self, path, *, sample_memory=windows_memory, max_bytes=16 * 1024**2):
        if type(max_bytes) is not int or not 1 <= max_bytes <= 16 * 1024**2:
            raise ValueError("diagnostic output limit must be 1..16MiB")
        self.path, self.sample_memory, self.max_bytes = Path(path), sample_memory, max_bytes
        self.lock = threading.RLock()
        self.started = time.monotonic()
        self.bytes_written = self.errors = self.dropped = 0
        self.last_error = None
        self.active_chunk = None
        self.disabled = False
        self._stream = self.path.open("xb")

    def _failure(self, error):
        try:
            self.errors += 1
            self.last_error = type(error).__name__
        except Exception:
            pass  # Even diagnostic bookkeeping may fail under real exhaustion.

    def emit(self, event, **fields):
        try:
            with self.lock:
                if self.disabled:
                    self.dropped += 1
                    return False
                row = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       "elapsed_seconds": time.monotonic() - self.started, "pid": os.getpid(),
                       "event": event, "scope": "diagnostic_observation_only", **fields}
                raw = (json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
                if len(raw) > 128 * 1024 or self.bytes_written + len(raw) > self.max_bytes:
                    self.dropped += 1
                    return False
                written = self._stream.write(raw)
                if written != len(raw):
                    raise OSError("short diagnostic write")
                self.bytes_written += written
                self._stream.flush()
                return True
        except Exception as error:
            self.disabled = True  # Do not append after a possibly partial write.
            self._failure(error)
            return False

    def sample(self, event="sample", **fields):
        selection = None
        try:
            with self.lock:
                selection = self.active_chunk
            memory = self.sample_memory()
        except Exception as error:
            self._failure(error)
            self.emit("observation_error", requested_event=event, chunk=selection,
                      error_type=type(error).__name__, **fields)
            return False
        written = self.emit(event, chunk=selection, memory=memory, **fields)
        if "pagefiles_error" in memory:
            self._failure(OSError("pagefile observation failed"))
            return False
        return written

    def failure(self, error, **fields):
        # Persist the trace before calling further OS APIs under memory pressure.
        try:
            self.emit("exception", exception_chain=exception_details(error), **fields)
            self.sample("exception_resources", **fields)
        except Exception as secondary:
            self._failure(secondary)

    @contextmanager
    def observe_controller(self, controller_type):
        """Observe _verify even when Run.run replaces its controller instance.

        For a single-writer process only. Restore the class attribute on every
        exit. Delegate the original arguments/result/error without retaining data.
        """
        original = controller_type._verify
        if getattr(original, "_banto_diagnostic_wrapper", False) is True:
            raise RuntimeError("controller diagnostics already installed")

        def verify(controller, records, pins, digest):
            with self.lock:
                previous = self.active_chunk
            selection = None
            try:
                record = records[-1]
                selection = {key: record[key] for key in ("chunk_index", "attempt", "sequence", "status")}
                with self.lock:
                    self.active_chunk = selection
            except Exception as error:
                self._failure(error)
            try:
                self.sample("audit_begin")
                try:
                    result = original(controller, records, pins, digest)
                except BaseException as error:
                    self.failure(error, chunk_at_failure=selection, phase="stored_chunk_audit")
                    raise
                self.sample("audit_end")
                return result
            finally:
                with self.lock:
                    self.active_chunk = previous

        verify._banto_diagnostic_wrapper = True
        controller_type._verify = verify
        try:
            yield
        finally:
            controller_type._verify = original

    def close(self):
        try:
            with self.lock:
                self._stream.close()
        except Exception as error:
            self._failure(error)

    @contextmanager
    def observe_launcher(self, launcher):
        """Use with the unchanged launcher's main(); includes errors it catches.

        An UnreapedWorker goes straight back to the original owner-retention
        path without any new exception-time IO or memory sampling here.
        """
        opening, continuing = launcher.open_run, launcher.continue_run

        def observe(operation, phase):
            def wrapped(*args, **kwargs):
                self.sample("phase_begin", phase=phase)
                try:
                    result = operation(*args, **kwargs)
                except launcher.processes.UnreapedWorker:
                    raise
                except BaseException as error:
                    self.failure(error, phase=phase)
                    raise
                self.sample("phase_end", phase=phase)
                return result
            return wrapped

        with self.observe_controller(launcher.native.lifecycle.Controller):
            try:
                launcher.open_run = observe(opening, "open_run")
                launcher.continue_run = observe(continuing, "continue_run")
                yield
            finally:
                launcher.open_run, launcher.continue_run = opening, continuing

    def summary(self):
        return {"bytes_written": self.bytes_written, "observation_errors": self.errors,
                "last_error": self.last_error, "dropped_events": self.dropped, "logging_disabled": self.disabled}


def self_check(output):
    """Real Windows APIs with an injected exception; no evaluation or allocation stress."""
    output = Path(output)
    output.mkdir()  # Never reuse a previous check or overwrite its records.
    log = Diagnostics(output / "events.jsonl")
    injected = MemoryError("diagnostic self-check: injected, not resource exhaustion")

    class Fixture:
        def _verify(self, records, pins, digest):
            raise injected

    original, caught = Fixture._verify, False
    try:
        if not log.sample("self_check_start", injected_failure=True):
            raise RuntimeError("initial diagnostic sample failed")
        with log.observe_controller(Fixture):
            try:
                Fixture()._verify([{"chunk_index": 0, "attempt": 1, "sequence": 3,
                                    "status": "fixture_only"}], {}, "fixture")
            except MemoryError as error:
                caught = error is injected
        if not caught or Fixture._verify is not original or log.active_chunk is not None:
            raise RuntimeError("diagnostic exception/restore contract failed")
        log.sample("self_check_end", injected_failure=True)
    finally:
        log.close()
    rows = [json.loads(row) for row in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    snapshots = [row["memory"] for row in rows if "memory" in row]
    traces = [row for row in rows if row["event"] == "exception"]
    valid = (log.errors == log.dropped == 0 and bool(traces) and bool(snapshots)
             and all(value["commit_limit_bytes"] > 0 and value["page_size_bytes"] > 0
                     and "pagefiles" in value and "pagefiles_error" not in value for value in snapshots)
             and any(frame["function"] == "_verify" for frame in traces[0]["exception_chain"][0]["frames"]))
    report = {"status": "passed" if valid else "failed", "injected_failure": True,
              "windows_api_mocks": False, "evaluation_started": False,
              "controller_fixture_only": True, "same_exception_preserved": caught,
              "method_restored": Fixture._verify is original, **log.summary()}
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Short Windows memory diagnostic self-check; no evaluation launch")
    parser.add_argument("--self-check-output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = self_check(args.self_check_output)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
