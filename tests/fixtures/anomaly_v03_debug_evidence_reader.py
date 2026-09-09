"""Offline byte-only interpretation of B1DBG001; never follows target pointers.

This reader does not open files, load images, or certify native provenance.
Only anonymous module lifetimes and redacted event fields leave the private owner.
"""

import hashlib
import json

from tests.fixtures.anomaly_v03_debug_evidence import DebugEvidence as Format
from tests.fixtures.anomaly_v03_debug_transport import DebugEvent, DebugEventTransport


def require(value):
    if not value:
        raise ValueError("startup_evidence_invalid")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


class EvidenceReading(dict):
    def __init__(self, raw, metadata):
        super().__init__(format_valid=True, provenance_verified=False, native_accepted=False,
                         bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), regions=[])
        self.private_raw = raw
        self.private_metadata = metadata


def interpret(raw):
    require(type(raw) is bytes and Format.HEADER.size <= len(raw) <= Format.CAPACITY)
    magic, length, event_size, slots, regions = Format.HEADER.unpack_from(raw)
    require((magic, event_size, slots, regions) == (Format.MAGIC, 176, 256, 2))
    require(0 < length <= Format.METADATA_LIMIT
            and len(raw) == Format.HEADER.size + length + 2 * Format.REGION_SIZE)
    offset = Format.HEADER.size + length
    try:
        metadata = json.loads(raw[Format.HEADER.size:offset].decode("ascii"),
                              object_pairs_hook=unique_object,
                              parse_constant=lambda value: require(False))
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError("startup_evidence_invalid") from None
    require(type(metadata) is dict)
    require(type(metadata.get("version")) is int and metadata["version"] == 1)
    require(metadata.get("byte_order") == "little" and type(metadata.get("pointer_bits")) is int
            and metadata["pointer_bits"] == 64)
    require(type(metadata.get("slots_per_region")) is int and metadata["slots_per_region"] == 256
            and type(metadata.get("event_size")) is int and metadata["event_size"] == 176)
    require(metadata.get("raw_scope") == "all_preallocated_slots_including_unconfirmed"
            and metadata.get("result_scope") == "before_evidence_write_flush_and_file_close")
    result = EvidenceReading(raw, metadata)
    active, next_module, pid = {}, 0, None
    for region in ("normal", "drain"):
        state = metadata.get(region)
        require(type(state) is dict)
        count = state.get("confirmed_buffers")
        require(type(count) is int and 0 <= count <= 256)
        pending = state.get("pending")
        require(pending is None or type(pending) is int and 0 <= pending < 256)
        require(type(state.get("wait_inflight")) is bool and type(state.get("continue_inflight")) is bool)
        require(type(state.get("file_closed")) is list and len(state["file_closed"]) == 256
                and all(type(value) is bool for value in state["file_closed"]))
        require(type(state.get("file_close_state")) is list and len(state["file_close_state"]) == 256
                and all(type(value) is str and value in ("not_started", "uncertain", "closed", "failed")
                        for value in state["file_close_state"]))
        rows = []
        for index in range(count):
            event = DebugEvent.from_buffer_copy(raw, offset + index * event_size)
            if pid is None and event.kind == 3 and event.pid != 0:
                pid = event.pid
            valid = 1 <= event.kind <= 9 and event.pid != 0 and event.tid != 0
            valid &= pid is not None and event.pid == pid
            if event.kind == 1:
                valid &= event.info.exception.first_chance in (0, 1) and event.info.exception.record.parameters <= 15
            row = {"slot": index, "kind": DebugEventTransport.NAMES[event.kind] if valid else "invalid",
                   "pending": index == pending}
            if valid and event.kind in (3, 6):
                base = event.info.create_process.base if event.kind == 3 else event.info.load_dll.base
                if base is not None and base not in active:
                    active[base] = next_module
                    next_module += 1
                    row["module"] = active[base]
                else:
                    if base is not None:
                        active[base] = None
                    row["module"] = None
                    row["module_ambiguous"] = True
            elif valid and event.kind == 7:
                row["module"] = active.pop(event.info.unload_base, None)
            elif valid and event.kind in (4, 5):
                row["code"] = event.info.exit_code
            elif valid and event.kind == 1:
                row["code"] = event.info.exception.record.code
                row["first_chance"] = bool(event.info.exception.first_chance)
            rows.append(row)
        tail = raw[offset + count * event_size:offset + Format.REGION_SIZE]
        result["regions"].append({"region": region, "confirmed_buffers": count,
                                  "wait_inflight": state["wait_inflight"],
                                  "continue_inflight": state["continue_inflight"],
                                  "unconfirmed_bytes_nonzero": any(tail), "events": rows})
        offset += Format.REGION_SIZE
    return result
