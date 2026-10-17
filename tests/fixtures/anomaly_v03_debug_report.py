"""Explicit post-run reporting only; no launch, native query or file lookup.

Flush the final driver outcome before optional details. Call only after run()
returns. This cannot recover outcomes lost by an earlier reporting process.
"""

import hashlib
import json
import ntpath


FINAL_KEYS = ("status", "resource_stop", "teardown_status", "evidence_status",
              "evidence_write_state", "evidence_flush_state", "evidence_file_closed",
              "fixture_retention", "native_accepted", "formal_permission")


def _line(stream, value):
    encoded = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    if len(encoded) > 16384:
        raise ValueError("report_size")
    count = stream.write(encoded + "\n")
    if count != len(encoded) + 1:
        raise OSError("report_partial_write")
    stream.flush()


def write_summary(owner, stream):
    """Emit two bounded JSON lines; stream IO failures propagate without retry.

The first line is authoritative only for the driver's final reported state.
Details use owned local values. Raw identities, profiles and errors stay private.
"""
    final = {key: owner.result.get(key) for key in FINAL_KEYS}
    _line(stream, {"phase": "final", "driver": final})
    if owner.resource_stop:
        _line(stream, {"phase": "details", "status": "resource_skipped"})
        return
    try:
        details = {"phase": "details", "status": "reported"}
        details["images"] = [
            {"event_slot": row.get("event_slot"), "status": row.get("status"),
             "basename": ntpath.basename(row.get("name", ""))}
            for row in owner.images.rows if row is not None]
        details["security"] = [
            {"target": row.get("target"), "status": row.get("status")}
            for row in owner.security.rows]
        if owner.memory is not None:
            details["memory"] = {key: getattr(owner.memory, key) for key in
                                 ("samples", "peak_commit", "peak_working")}
        if owner.observer is not None:
            details["observation"] = {key: owner.observer.result.get(key) for key in
                                      ("status", "events", "continued_events", "exit_code_observed")}
        if owner.evidence.capture_state == "captured":
            size = owner.evidence.size
            if type(size) is not int or not 0 < size <= owner.evidence.CAPACITY:
                raise ValueError("report_evidence_size")
            raw = owner.evidence.buffer.raw[:size]
            if len(raw) != size:
                raise ValueError("report_evidence_length")
            details["buffer_bytes"] = size
            details["buffer_sha256"] = hashlib.sha256(raw).hexdigest()
        # Validate before IO, so detail construction failure cannot erase final.
        encoded = json.dumps(details, ensure_ascii=True, allow_nan=False)
        if len(encoded) > 16384:
            raise ValueError("report_size")
    except MemoryError:
        # The final driver state was already flushed. Stop the caller before
        # another summary, hash or file write; do not format a failure detail.
        owner.resource_stop = True
        raise
    except Exception as error:
        details = {"phase": "details", "status": "failed", "error_type": type(error).__name__}
    _line(stream, details)
