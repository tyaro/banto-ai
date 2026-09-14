"""Bounded pre-publication evidence barrier, using an injected private sink.

No native writer, acquisition, DACL proof, or acceptance entrypoint. Trusted
observations describe a toy fixture; a successful sink response is not a proof
of persistence. Native save/readback/flush and ownership need separate checks.
"""
import base64
from dataclasses import dataclass
import hashlib
import json

from . import anomaly_v03_publication_model as model
from . import anomaly_v03_rename_adapter as rename
from . import anomaly_v03_handle_owner as owned

MAX_EVIDENCE_BYTES = 512 * 1024
MAX_ATTEMPT_BYTES = 3 * MAX_EVIDENCE_BYTES
MAX_DESCRIPTOR_BYTES = 2048


def _need(condition):
    if not condition:
        raise owned.OwnershipError("invalid_prepublication_evidence")


@dataclass(frozen=True)
class Observation:
    pin: rename.ObjectPin
    descriptor: bytes


@dataclass(frozen=True)
class EvidenceRecord:
    step: str
    raw: bytes
    sha256: str


def build_evidence(step, *, source_revision, files, marker, observations):
    """Freeze exact bytes before releasing handles; no path or exception text.

    Descriptors are bounded raw observations, not parsed or authenticated DACLs.
    The caller must establish their native meaning and correspondence to files.
    """
    _need(type(step) is str and step in owned.RELEASE_STEPS)
    expected = model.marker_bytes(source_revision, files)  # Enforces toy limits/paths.
    _need(type(marker) is bytes and marker == expected)
    _need(type(observations) is tuple and 0 < len(observations) <= owned.MAX_HANDLES)
    observed, identities, handles = [], set(), set()
    for observation in observations:
        _need(type(observation) is Observation)
        rename._pin(observation.pin)
        _need(type(observation.descriptor) is bytes and 0 < len(observation.descriptor) <= MAX_DESCRIPTOR_BYTES)
        pin = observation.pin
        identity = (pin.volume, pin.file_id)
        _need(identity not in identities and pin.handle not in handles)
        identities.add(identity)
        handles.add(pin.handle)
        observed.append({"slot": len(observed), "volume": pin.volume, "file_id": pin.file_id.hex(),
                         "directory": pin.directory, "content_sha256": pin.content_sha256,
                         "descriptor_b64": base64.b64encode(observation.descriptor).decode("ascii")})
    envelope = {
        "version": "s4-b2-prepublication.1", "step": step, "source_revision": source_revision,
        "marker_b64": base64.b64encode(marker).decode("ascii"),
        "marker_sha256": hashlib.sha256(marker).hexdigest(),
        "files": [{"path": name, "bytes_b64": base64.b64encode(files[name]).decode("ascii"),
                   "raw_sha256": hashlib.sha256(files[name]).hexdigest()} for name in sorted(files)],
        "observations": observed, "native_observations_authenticated": False,
        "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False,
    }
    raw = (json.dumps(envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    _need(len(raw) <= MAX_EVIDENCE_BYTES)
    return EvidenceRecord(step, raw, hashlib.sha256(raw).hexdigest())


class EvidenceBarrier:
    """Persist one record per phase before a selected group can be released.

    protected indices belong to the retained root/rename handles. This object
    never deletes or overwrites an old record, retries a sink, or resumes a
    stopped attempt. Native sink ownership and permissions remain unimplemented.
    """

    def __init__(self, backend, *, owner, protected):
        _need(type(owner) is owned.HandleOwner)
        owner._indices(protected)
        self._backend, self._owner, self._protected = backend, owner, protected
        self._states = ["not_started"] * len(owned.RELEASE_STEPS)
        self._hashes = [None] * len(owned.RELEASE_STEPS)
        self._used_bytes = 0
        self._failed = self._busy = False

    def _validate_record(self, record):
        # Reconstruct the bounded canonical record, including false acceptance
        # flags, and bind the marker to the journal's independent expected hash.
        data = json.loads(record.raw)
        _need(type(data) is dict and type(data["files"]) is list
              and 0 < len(data["files"]) <= model.MAX_FILES)
        def decode(value):
            _need(type(value) is str)
            return base64.b64decode(value, validate=True)
        files = {row["path"]: decode(row["bytes_b64"]) for row in data["files"]}
        _need(len(files) == len(data["files"]))
        marker = decode(data["marker_b64"])
        _need(hashlib.sha256(marker).hexdigest() == self._owner._journal.snapshot()["marker_sha256"])
        _need(type(data["observations"]) is list and len(data["observations"]) == len(self._owner._slots))
        observations = []
        for index, row in enumerate(data["observations"]):
            pin = self._owner._slots[index].pin
            _need(row["slot"] == index and row["volume"] == pin.volume
                  and row["file_id"] == pin.file_id.hex() and row["directory"] is pin.directory
                  and row["content_sha256"] == pin.content_sha256)
            observations.append(Observation(pin, decode(row["descriptor_b64"])))
        expected = build_evidence(record.step, source_revision=data["source_revision"], files=files,
                                  marker=marker, observations=tuple(observations))
        _need(record.raw == expected.raw)

    def save_and_release(self, record, indices):
        entered, phase = False, None
        try:
            _need(not self._failed and not self._busy)
            self._owner._usable()
            self._owner._indices(indices)
            self._owner._indices(self._protected)
            _need(not any(index in self._protected for index in indices))
            _need(type(record) is EvidenceRecord and type(record.step) is str and record.step in owned.RELEASE_STEPS)
            phase = owned.RELEASE_STEPS.index(record.step)
            _need(self._states[phase] == "not_started")
            state = self._owner._journal.snapshot()
            _need(any(row["step"] == record.step and row["state"] == "pending" for row in state["steps"]))
            _need(type(record.raw) is bytes and 0 < len(record.raw) <= MAX_EVIDENCE_BYTES)
            _need(type(record.sha256) is str and hashlib.sha256(record.raw).hexdigest() == record.sha256)
            self._validate_record(record)
            _need(self._used_bytes + len(record.raw) <= MAX_ATTEMPT_BYTES)
            # Reserve before the sink can have an effect. A lost reply consumes
            # this attempt's byte budget and is never a reason to save again.
            self._used_bytes += len(record.raw)
            self._hashes[phase] = record.sha256
            self._states[phase] = "pending"
            self._busy = entered = True
            def save(_pins):
                result = self._backend.persist_evidence(record.step, record.raw, record.sha256)
                _need(result is None)
                _need(not self._failed)
            self._owner.borrowed(indices, save)
            self._states[phase] = "saved"
            self._owner.release_before_publish(record.step, indices)
            self._states[phase] = "released"
        except BaseException as error:
            self._failed = True
            if phase is not None and self._states[phase] == "pending":
                self._states[phase] = "unknown"
            self._owner._record(error)
            self._owner._stop_safely()
            raise
        finally:
            if entered:
                self._busy = False

    def snapshot(self):
        return {
            "steps": [{"step": step, "state": self._states[index], "sha256": self._hashes[index]}
                      for index, step in enumerate(owned.RELEASE_STEPS)],
            "reserved_bytes": self._used_bytes, "stopped": self._failed,
            "retry_permitted": False, "cleanup_permitted": False,
            "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False,
        }
