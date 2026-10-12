"""Local verification evidence, independent of execution/protocol budgets.

One writer, a fresh directory, immutable parts, and a reserved failure budget.
This module does not run commands or grant any campaign/native permission.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path


class RecordLimitError(RuntimeError):
    pass


class OutputLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecordLimits:
    total_bytes: int = 16 * 1024**2
    total_files: int = 512
    part_bytes: int = 256 * 1024
    failure_bytes: int = 2 * 1024**2
    failure_files: int = 16

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in asdict(self).values()):
            raise ValueError("record limits must be positive integers")
        if not (self.failure_bytes < self.total_bytes and self.failure_files < self.total_files):
            raise ValueError("failure reserve must fit inside total limits")
        if self.part_bytes < 4096 or self.failure_bytes < 3 * self.part_bytes or self.failure_files < 6:
            raise ValueError("reserve must fit failure evidence and closure")
        if self.total_bytes > 16 * 1024**2 or self.total_files > 512 or self.part_bytes > 256 * 1024:
            raise ValueError("record limits exceed the reviewed diagnostic policy")


def _json_chunks(value):
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    for text in encoder.iterencode(value):
        for start in range(0, len(text), 16384):
            yield text[start:start + 16384].encode("utf-8")


def _pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _plain(path, directory=False):
    info = path.lstat()
    reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)
    if path.is_symlink() or reparse or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError("record path must be a regular file/directory")
    if not directory and info.st_nlink != 1:
        raise ValueError("record hard links are not supported")
    return info


def _file_pin(path, block=256 * 1024):
    _plain(path)
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(block):
            digest.update(raw)
            size += len(raw)
    return {"bytes": size, "sha256": digest.hexdigest()}


def _error(error):
    try:
        message = str(error)
        available = True
    except BaseException:
        message = "exception message could not be read"
        available = False
    return {"type": type(error).__name__, "message": message[:2048],
            "message_available": available, "message_truncated": len(message) > 2048}


class EvidenceStore:
    def __init__(self, root, limits=None):
        self.root = Path(root).absolute()
        self.limits = limits or RecordLimits()
        for parent in (self.root.parent, *self.root.parent.parents):
            _plain(parent, directory=True)
        self.root.mkdir()  # Never reopen, append to, or replace an existing root.
        info = _plain(self.root, directory=True)
        self._identity = info.st_dev, info.st_ino
        self._items, self._operations, self._errors = {}, {}, []
        self._closed = False
        self._first_recording_error = None
        self._failed = False
        self._original_error = None
        self._closing_started = False
        self._marker = None
        self.write_json("policy", {"format": "verification-records-v1", "limits": asdict(self.limits),
                                   "execution_limits_modified": False, "formal_permission": False})

    def _files(self):
        info = _plain(self.root, directory=True)
        if (info.st_dev, info.st_ino) != self._identity:
            raise ValueError("record directory identity changed")
        files = list(self.root.iterdir())
        for path in files:
            _plain(path)
        return files

    def _write(self, name, raw, emergency=False, closing=False):
        if self._closed or (self._closing_started and not closing) or (self.root / "root-closed.json").exists():
            raise RecordLimitError("record root is closed")
        if Path(name).name != name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("unsafe record filename")
        files = self._files()
        reserve_bytes = 0 if closing else (2 * self.limits.part_bytes if emergency else self.limits.failure_bytes)
        reserve_files = 0 if closing else (4 if emergency else self.limits.failure_files)
        maximum_bytes = self.limits.total_bytes - reserve_bytes
        maximum_files = self.limits.total_files - reserve_files
        if (len(raw) > self.limits.part_bytes or len(files) + 1 > maximum_files or
                sum(p.stat().st_size for p in files) + len(raw) > maximum_bytes):
            raise RecordLimitError("verification record capacity; failure reserve retained")
        with (self.root / name).open("xb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("short evidence write")
            stream.flush()
            os.fsync(stream.fileno())
        return {"path": name, **_pin(raw)}

    def _issue(self, error):
        self._failed = True
        if self._first_recording_error is None:
            self._first_recording_error = error
        self._errors.append(_error(error))

    def _item(self, label, chunks, *, source_pin=None, source_complete=True, emergency=False, register=True, closing=False):
        if self._closed:
            raise RecordLimitError("record root is closed")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", label):
            raise ValueError("unsafe record label")
        if label == "manifest" and register:
            raise ValueError("reserved record label")
        if label in self._items:
            raise FileExistsError("record label already used")
        if self._first_recording_error is not None and not emergency:
            raise self._first_recording_error
        item = {"parts": [], "status": "writing", "source_pin": source_pin,
                "source_complete": source_complete, "saved_bytes": 0}
        if register:
            self._items[label] = item
        pending, digest = bytearray(), hashlib.sha256()

        def flush():
            part = self._write(f"{label}.{len(item['parts']) + 1:06d}.part", bytes(pending), emergency, closing)
            item["parts"].append(part)
            item["saved_bytes"] += len(pending)
            digest.update(pending)
            pending.clear()

        try:
            for chunk in chunks:
                if not isinstance(chunk, (bytes, bytearray, memoryview)):
                    raise TypeError("evidence chunks must be bytes")
                view, offset = memoryview(chunk), 0
                while offset < len(view):
                    size = min(len(view) - offset, self.limits.part_bytes - len(pending))
                    pending.extend(view[offset:offset + size])
                    offset += size
                    if len(pending) == self.limits.part_bytes:
                        flush()
            if pending or not item["parts"]:
                flush()
            item["status"] = "complete"
        except BaseException as error:
            item["status"] = "partial"
            self._issue(error)
            raise
        finally:
            item["saved_pin"] = {"bytes": item["saved_bytes"], "sha256": digest.hexdigest()}
        return item

    def write_bytes(self, label, raw, *, source_complete=True, emergency=False):
        if not isinstance(raw, bytes):
            raise TypeError("raw evidence must be bytes")
        return self._item(label, (raw,), source_pin=_pin(raw), source_complete=source_complete, emergency=emergency)

    def write_json(self, label, value, *, emergency=False):
        return self._item(label, _json_chunks(value), emergency=emergency)

    def write_terminal(self, label, value):
        """Safe in finally: save terminal metadata without replacing a body error.

        A failed terminal write is latched; a normally exiting store then raises
        that recording error, so callers cannot report a successfully saved run.
        """
        try:
            return self.write_json(label, value, emergency=True)
        except BaseException as error:
            self._fallback(error)
            return None

    def operation(self, label, metadata=None):
        if self._failed or self._closed:
            raise RecordLimitError("failed/closed record store; use a fresh run ID")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", label):
            raise ValueError("unsafe operation label")
        if label in self._operations:
            raise FileExistsError("operation already recorded")
        return _Operation(self, label, metadata)

    def _fallback(self, error):
        self._issue(error)
        try:
            sys.stderr.write("verification evidence could not be saved: " + json.dumps(_error(error)) + "\n")
        except BaseException:
            pass  # Never mask the original error, including interrupts/MemoryError.

    def close(self):
        if self._closed:
            return self._marker
        if self._closing_started:
            raise RecordLimitError("closure previously failed; original prefix retained, no retry")
        self._closing_started = True
        try:
            files = {p.name: _file_pin(p) for p in self._files()}
            unfinished = any(op["status"] != "passed" for op in self._operations.values())
            state = "failed" if self._failed else ("incomplete" if unfinished else "complete")
            manifest = {"format": "verification-records-v1", "status": state, "files": files,
                        "items": self._items, "operations": self._operations, "recording_errors": self._errors,
                        "limits": asdict(self.limits), "formal_permission": False, "native_owner_recovery_claim": False}
            parts = self._item("manifest", _json_chunks(manifest), emergency=True, register=False, closing=True)
            marker = {"format": "verification-records-closure-v1", "status": state,
                      "manifest": parts, "formal_permission": False}
            raw = b"".join(_json_chunks(marker))
            self._write("root-closed.json", raw, emergency=True, closing=True)
            self._marker = marker
            self._closed = True
            return marker
        except BaseException as error:
            self._fallback(error)
            raise

    def __enter__(self):
        return self

    def __exit__(self, kind, error, tb):
        if error is not None:
            self._failed = True
            if self._original_error is None:
                operation = _Operation(self, "store", None)
                self._operations["store"] = operation.summary
                operation._failure(error)
        latched = self._original_error or self._first_recording_error
        try:
            self.close()
        except BaseException:
            if error is None:
                if latched is not None:
                    raise latched
                raise
        if error is None and latched is not None:
            raise latched
        return False


class _Operation:
    def __init__(self, store, label, metadata):
        self.store, self.label, self.metadata = store, label, metadata
        self.summary = {"status": "not_started", "returncode": None}
        self.process = None
        self._execution_error = None

    def __enter__(self):
        self.store._operations[self.label] = self.summary
        try:
            self.store.write_json(self.label + ".started", {"metadata": self.metadata})
            self.summary["status"] = "running"
            return self
        except BaseException as error:
            self._failure(error)
            raise

    def capture_process(self, result, *, stdout_limit=1024**2, stderr_limit=131072):
        """Save an already returned CompletedProcess, before checking its outcome.

        Execution remains the caller's responsibility; no subprocess is launched.
        Existing callers must pass their original output bounds unchanged.
        """
        self.process = result
        self.summary["returncode"] = result.returncode
        original = None
        if result.returncode:
            original = subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        elif len(result.stdout) > stdout_limit or len(result.stderr) > stderr_limit:
            original = OutputLimitError("execution stdout/stderr limit exceeded")
        self._execution_error = original
        try:
            self.store.write_json(self.label + ".return", {"args": result.args, "returncode": result.returncode,
                                                          "stdout_pin": _pin(result.stdout), "stderr_pin": _pin(result.stderr)})
            self.store.write_bytes(self.label + ".stdout", result.stdout)
            self.store.write_bytes(self.label + ".stderr", result.stderr)
        except BaseException as recording_error:
            if original is not None:
                raise original from recording_error
            raise
        if original is not None:
            raise original
        return result

    def _failure(self, error):
        self.store._failed = True
        if self.store._original_error is None:
            self.store._original_error = error
        self.summary.update(status="failed", error=_error(error))
        # First preserve the original exception/return, without large logs or traceback.
        try:
            self.store.write_json(self.label + ".failure", self.summary, emergency=True)
        except BaseException as secondary:
            self.store._fallback(secondary)
        # Complete returned streams, or timeout's observed partial streams, use the reserve
        # if normal storage failed. A stored prefix is never described as a full stream.
        result = self.process
        for channel in ("stdout", "stderr"):
            raw = getattr(result, channel, None) if result is not None else getattr(error, channel, None)
            original_item = self.store._items.get(self.label + "." + channel)
            if isinstance(raw, bytes) and (not original_item or original_item["status"] != "complete"):
                try:
                    self.store.write_bytes(self.label + ".failure-" + channel, raw,
                                           source_complete=result is not None, emergency=True)
                except BaseException as secondary:
                    self.store._fallback(secondary)
        try:
            self.store._item(self.label + ".traceback",
                             (text.encode("utf-8", "backslashreplace") for text in traceback.format_exception(error)),
                             emergency=True)
        except BaseException as secondary:
            self.store._fallback(secondary)

    def __exit__(self, kind, error, tb):
        if error is not None:
            self._failure(error)
            return False
        if self._execution_error is not None:
            self._failure(self._execution_error)
            raise self._execution_error
        if self.store._first_recording_error is not None:
            error = self.store._first_recording_error
            self._failure(error)
            raise error
        try:
            self.store.write_json(self.label + ".finished", {"status": "passed", "returncode": self.summary["returncode"]})
        except BaseException as error:
            self._failure(error)
            raise
        self.summary["status"] = "passed"
        return False


def verify_record(root):
    """Read a closed store and check all original parts; does not run/replay work."""
    root = Path(root).absolute()
    _plain(root, directory=True)
    marker_path = root / "root-closed.json"
    _plain(marker_path)
    if marker_path.stat().st_size > 256 * 1024:
        raise ValueError("closure marker too large")
    marker = json.loads(marker_path.read_bytes())
    if marker["format"] != "verification-records-closure-v1" or marker["manifest"]["status"] != "complete":
        raise ValueError("record closure incomplete")

    def parts_bytes(parts, maximum):
        blocks = []
        if sum(p["bytes"] for p in parts) > maximum:
            raise ValueError("record read bound")
        for part in parts:
            name = part["path"]
            if Path(name).name != name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
                raise ValueError("unsafe record reference")
            path = root / name
            if _plain(path).st_size != part["bytes"]:
                raise ValueError("record part byte count mismatch")
            if _file_pin(path) != {k: part[k] for k in ("bytes", "sha256")}:
                raise ValueError("record part pin mismatch")
            blocks.append(path.read_bytes())
        return b"".join(blocks)

    raw = parts_bytes(marker["manifest"]["parts"], 2 * 1024**2)
    if _pin(raw) != marker["manifest"]["saved_pin"]:
        raise ValueError("manifest stream differs")
    manifest = json.loads(raw)
    if manifest["format"] != "verification-records-v1" or manifest["status"] not in ("complete", "failed", "incomplete"):
        raise ValueError("invalid record status")
    limits = RecordLimits(**manifest["limits"])
    expected = set(manifest["files"]) | {p["path"] for p in marker["manifest"]["parts"]} | {"root-closed.json"}
    paths = list(root.iterdir())
    if {p.name for p in paths} != expected or len(paths) > limits.total_files:
        raise ValueError("record inventory differs")
    if sum(_plain(p).st_size for p in paths) > limits.total_bytes:
        raise ValueError("record total byte limit")
    for name, expected_pin in manifest["files"].items():
        if Path(name).name != name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("unsafe inventory reference")
        if _file_pin(root / name) != expected_pin:
            raise ValueError("record file pin mismatch")
    for item in manifest["items"].values():
        raw = parts_bytes(item["parts"], limits.total_bytes)
        if _pin(raw) != item["saved_pin"]:
            raise ValueError("record stream pin mismatch")
        if item["status"] == "complete" and item["source_pin"] is not None and _pin(raw) != item["source_pin"]:
            raise ValueError("complete stream differs from observed input")
    if marker["status"] != manifest["status"] or manifest["formal_permission"] is not False:
        raise ValueError("record state differs")
    if manifest["status"] == "complete" and any(op["status"] != "passed" for op in manifest["operations"].values()):
        raise ValueError("unfinished operation marked complete")
    if any(op["status"] == "passed" and op["returncode"] not in (0, None) for op in manifest["operations"].values()):
        raise ValueError("failed command marked passed")
    return manifest
