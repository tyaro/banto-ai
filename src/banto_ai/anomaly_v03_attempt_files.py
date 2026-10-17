"""Read fixed attempt files without writing, resuming, or granting coverage.

File inspection supports every declared attempt. Independent ledger replay still
uses the existing first-six-cell contract and rejects every other chunk.
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import re

from . import anomaly_v03 as v
from . import anomaly_v03_attempt_descriptor as descriptor
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_checkpoint_evidence as evidence
from . import anomaly_v03_saved_audit as audit
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt

MAX_DESCRIPTOR_BYTES = 64 * 1024
CONTROL_LIMITS = {"marker": 1024**2, "producer_supervision": 1024**2,
                  "audit_report": 8 * 1024**2, "audit_supervision": 1024**2}
MAX_PAYLOAD_FILES = 512


def _read(path, maximum, *, links=1):
    path = rt.regular_path(path, links=links)
    rt.require(path.stat().st_size <= maximum, "attempt file byte limit")
    raw = storage.read_regular(path, links=links)
    rt.require(len(raw) <= maximum, "attempt file grew beyond limit")
    return raw


def _capture(root, plan, records, digest, pins):
    layout = descriptor.describe_layout(plan, records, **pins)["layout"]
    raw = _read(root / layout["descriptor_path"], MAX_DESCRIPTOR_BYTES)
    rt.require(storage.sha(raw) == digest, "external attempt descriptor hash mismatch")
    value = v.strict_json(raw)
    metadata = descriptor.validate_descriptor(value, plan, records, **pins)
    captured = {"descriptor": raw}
    for role, entry in value["artifacts"].items():
        path = root / layout["files"][role]
        if entry is None:
            # Inspect missing paths without following reparse points. A file that
            # has appeared since the declaration requires a new journal snapshot.
            rt.regular_path(path, missing=True, links=2 if role == "marker" else 1)
            rt.require(not path.exists(), "undeclared attempt evidence exists: " + role)
            continue
        rt.require(entry["bytes"] <= CONTROL_LIMITS[role], "declared attempt file byte limit")
        captured[role] = _read(path, CONTROL_LIMITS[role], links=2 if role == "marker" else 1)
        descriptor._same({"bytes": len(captured[role]), "sha256": storage.sha(captured[role])},
                         {key: entry[key] for key in ("bytes", "sha256")}, "attempt artifact bytes/hash mismatch: " + role)
        rt.require(type(v.strict_json(captured[role])) is dict, "attempt control JSON object required")
    return value, metadata, captured


def _payload_limits(root):
    view = storage.PayloadView(root)
    rt.require(0 < len(view) <= MAX_PAYLOAD_FILES, "attempt payload file count limit")
    sizes = [rt.regular_path(root / name).stat().st_size for name in view]
    rt.require(max(sizes) <= audit.MAX_FILE_BYTES and sum(sizes) <= audit.MAX_PAYLOAD_BYTES,
               "attempt payload byte limit")
    return sum(sizes)


def _inspect(root, plan, records, descriptor_sha256, pins, verify=None):
    rt.require(type(descriptor_sha256) is str and re.fullmatch("[0-9a-f]{64}", descriptor_sha256),
               "external attempt descriptor hash")
    layout = descriptor.describe_layout(plan, records, **pins)["layout"]
    root = rt.regular_path(root, directory=True)
    with ExitStack() as stack:
        # Hold the selected attempt chain. Other chunks and retained attempts are
        # neither traversed nor counted as input to this snapshot.
        directories = [root]
        target = root / layout["descriptor_path"]
        directories.extend(reversed([p for p in target.parents if p != root and root in p.parents]))
        bindings = []
        for directory in directories:
            binding = storage.DirectoryBinding(directory)
            stack.callback(binding.close)
            bindings.append(binding)
        value, metadata, raw = _capture(root, plan, records, descriptor_sha256, pins)
        for role in descriptor.ROLES:
            if role in raw:
                path = root / layout["files"][role]
                binding = storage.DirectoryBinding(path.parent)
                stack.callback(binding.close)
                bindings.append(binding)
        payload_bytes, publication = 0, None
        if "marker" in raw:
            payload_root = root / layout["payload_root"]
            payload_bytes = _payload_limits(payload_root)
            # Here only publication bytes/framing are checked. Do not expose the
            # helper's local_verified as a scientific/semantic verification flag.
            publication = storage.verify_local_publication(root / layout["result_root"],
                expected_marker_sha256=value["artifacts"]["marker"]["sha256"], verify_semantics=lambda files: None)
            rt.require(_payload_limits(payload_root) == payload_bytes, "attempt payload size changed")
        extra = verify(root, value, raw, payload_bytes, publication) if verify else {}
        if verify and publication is not None:
            rt.require(_payload_limits(root / layout["payload_root"]) == payload_bytes, "attempt payload size changed")
            storage.verify_local_publication(root / layout["result_root"],
                expected_marker_sha256=value["artifacts"]["marker"]["sha256"], verify_semantics=lambda files: None)
        _, _, after = _capture(root, plan, records, descriptor_sha256, pins)
        rt.require(after == raw, "attempt evidence changed during verification")
        for binding in bindings:
            binding.check()
        return {"format": "anomaly-v03-attempt-file-check-v1", "scope": "engineering-attempt-read-only",
            "status": "attempt_files_verified", "root": str(root), "journal": pins,
            "descriptor_raw_sha256": descriptor_sha256, "descriptor_path": layout["descriptor_path"],
            "chunk_index": metadata["chunk_index"], "attempt": metadata["attempt"], "state": metadata["state"],
            "artifact_roles_verified": metadata["artifact_roles_present"],
            "artifact_bytes_verified": True, "filesystem_containment_verified": True,
            "containment_scope": "selected_regular_paths_at_read_time_single_writer",
            "payload_inventory_verified": publication is not None,
            "payload_files": publication["payloads"] if publication else 0, "payload_bytes": payload_bytes,
            "evidence_body_bindings_verified": False, "saved_ledgers_revalidated": False,
            "source_checkouts_verified": False, "campaign_evaluations_credited": 0,
            "execution_authorized": False, "resume_authorized": False, "campaign_completed": False,
            "independent_s6_complete": False, "score_derivation_verified": False,
            "formal_permission": False, "performance_status": "not_evaluated", **extra}


def inspect_attempt(root, plan, records, descriptor_sha256, **pins):
    """Verify declared control bytes and marker payload inventory, not semantics."""
    return _inspect(root, plan, records, descriptor_sha256, pins)


def audit_attempt(root, plan, records, descriptor_sha256, producer_root, consumer_root, verifier_revision, **pins):
    """Recheck six saved ledgers and bind both process reports at fixed paths.

    consumer_root names the historical auditor; verifier_revision names this
    checkout. The existing fixed dev-pair contract is never silently generalized.
    """
    descriptor.describe_layout(plan, records, **pins)
    rt.require(records[-1]["chunk_index"] == 0 and records[-1]["status"] in checkpoints.VERIFIED,
               "attempt audit supports only a verified first dev chunk")

    def verify(root, value, raw, payload_bytes, publication):
        layout, bindings, hashes = value["layout"], plan["source_bindings"], records[-1]["evidence"]
        result_root = root / layout["result_root"]
        supervision_path = root / layout["files"]["producer_supervision"]
        historical = rt.capture_checkout(Path(consumer_root), bindings["consumer_revision"])
        stored = v.strict_json(raw["audit_report"])
        descriptor._same(value["audit_runtime"], {"before": stored["consumer_runtime"], "after": stored["consumer_runtime"]},
                         "descriptor audit runtime differs from report")
        manifest_path = result_root / "payload/manifest.json"
        manifest_raw = _read(manifest_path, 1024**2)
        fresh = audit.audit_saved(result_root, hashes["marker_sha256"], hashes["supervision_sha256"],
            Path(producer_root), bindings["producer_revision"], verifier_revision, supervision_path=supervision_path)
        reference = {"trial_root": str(result_root), "producer_root": str(Path(producer_root).absolute()),
            "consumer_root": str(Path(consumer_root).absolute()), "journal": pins,
            "audit_monitor_sha256": value["artifacts"]["audit_supervision"]["sha256"]}
        bound = evidence._bind_trial(plan, records[-1], reference, v.strict_json(manifest_raw),
            v.strict_json(raw["producer_supervision"]), stored, fresh, v.strict_json(raw["audit_supervision"]),
            raw["audit_report"], historical.source_descriptor(), supervision_path=supervision_path)
        descriptor._same(fresh["resources"]["input_payload_bytes"], payload_bytes, "attempt audit payload bytes")
        descriptor._same(fresh["storage_verification"], publication, "attempt audit publication differs")
        rt.require(_read(manifest_path, 1024**2) == manifest_raw, "attempt manifest changed")
        historical.recheck()
        return {"status": "attempt_saved_ledgers_verified", "evidence_body_bindings_verified": True,
            "saved_ledgers_revalidated": True, "source_checkouts_verified": True, "evaluations_checked": 6,
            "producer_revision": bound["producer_revision"], "historical_consumer_revision": bound["historical_consumer_revision"],
            "verifier_revision": bound["verifier_revision"], "historical_producer_runtime": bound["historical_producer_runtime"],
            "historical_consumer_runtime": bound["historical_consumer_runtime"], "verifier_runtime": bound["verifier_runtime"],
            "audit_resources": fresh["resources"]}

    return _inspect(root, plan, records, descriptor_sha256, pins, verify)
