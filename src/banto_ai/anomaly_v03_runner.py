"""S3 deterministic runner and producer replay; no analysis/gates/promotion.

The fixed inventory can be inspected without generating data. The public run
entry rejects before staging until S4 acceptance/consumer/runtime freeze exists.
The private engine is exercised with fake backends and hand-observation fixtures
only. Producer replay detects forged output; it is not the independent S6 audit.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import zlib
from collections import Counter
from pathlib import Path

from . import _anomaly_v03_contract as c
from . import anomaly_v03 as v
from . import anomaly_v03_materializer as m
from . import anomaly_v03_scoring as scoring
from . import anomaly_v03_episodes as episodes
from . import _anomaly_v03_runtime as runtime
from ._anomaly_v03_io import inventory, payload_entry, read_regular
from ._anomaly_v03_schema import common_defs

LEDGERS = ("events", "profiles", "scores", "source_episodes", "equipment_episodes", "incidents")


def _status(run="not_run", engineering="not_evaluated"):
    return {"run_status": run, "engineering_status": engineering, "performance_status": "not_evaluated"}


def planned_slots(role: str) -> list:
    return [{"identity": identity, "status": "not_started", "failure_stage": None, "safe_reason": None,
             "input_hashes": None, "evidence": []} for identity in v.evaluation_inventory(role)]


def planned_metadata(role: str) -> dict:
    return {"schema_version": "0.3", "matrix_id": "anomaly-multiseed-v03", "role": role,
            "planned_counts": c.counts(role), "evaluations": planned_slots(role),
            "seed_list_canonical_sha256": c.SEED_HASH, "run_status": "not_run", "performance_status": "not_evaluated"}


def _provenance(checkout, entries):
    return {"science_revision": c.SCIENCE_REVISION, "post_audit_revision": c.STATUS_REVISION,
            "producer_revision": checkout.revision, "producer_source": checkout.source_descriptor(),
            "registry_raw_sha256": v.REGISTRY_RAW_SHA256, "inventory": entries}


def _input_entries(identity, files):
    prefix = "datasets/"+identity["dataset_id"]+"/"
    return inventory({prefix+name: raw for name, raw in files.items()})


def compute_evaluation(identity: dict, files: dict[str, bytes], checkout) -> dict:
    """S2 from verified saved bytes; never accepts raw latent arrays or GT features."""
    hashes = m.validate_dataset(identity, files)
    raw, digest = files["observations.jsonl"], hashes["observations"]
    bank = scoring.fit_profiles(identity, raw, expected_sha256=digest)
    runtime.require(not bank.normal_prefix_issues, "invalid normal prefix")
    scores, sources, equipment = episodes.build_episodes(scoring.score_test(bank, raw, expected_sha256=digest))
    rows = {"events": v.event_inventory(identity), "profiles": bank.ledger_rows(), "scores": scores,
            "source_episodes": sources, "equipment_episodes": equipment}
    rows["incidents"], rows["equipment_episodes"] = episodes.match_incidents(identity, **rows)
    metrics = episodes.account_metrics(identity, **rows)
    inconclusive = any(p["status"] != "calibrated" for p in rows["profiles"])
    result = {"schema_version": "0.3", "result_type": "event-aware-anomaly-v03", "identity": dict(identity),
              "status": _status("complete", "inconclusive" if inconclusive else "pass"),
              "provenance": _provenance(checkout, _input_entries(identity, files)), "input_hashes": hashes,
              "splits": c.config_values(c.BOOTSTRAP_HASH, c.GOLDEN_DRAWS)[0]["splits"], **rows,
              "row_counts": {key: len(rows[key]) for key in LEDGERS}, "metrics": metrics, "slices": []}
    v.validate_result_contract(result, source_snapshots=checkout.snapshots())
    return result


def _execute_candidate(identity, files, checkout):
    """Private attack-test seam; verification never trusts this return value."""
    return compute_evaluation(identity, files, checkout)


def verify_evaluation(result: dict, identity: dict, saved_files: dict, checkout) -> dict:
    """Re-fit/re-score/re-match/account every row, even if hashes were updated."""
    v.validate_result_contract(result, source_snapshots=checkout.snapshots())
    runtime.require(v.canonical_json(result["identity"]) == v.canonical_json(identity), "evaluation identity changed")
    expected = compute_evaluation(identity, saved_files, checkout)
    runtime.require(v.canonical_json(result) == v.canonical_json(expected), "evaluation numerical/ledger replay mismatch")
    return expected


class CellFailure(Exception):
    """A classified, pure candidate scoring/profile failure.

    This deliberately is not a catch-all for storage, journal, source, root or
    publication failures.  Those failures compromise the producer boundary and
    must stop the remaining inventory.
    """
    def __init__(self, stage, reason="exception", *, evidence=(), input_hashes=None):
        runtime.require(stage in ("profile", "scoring"), "ordinary failure stage is not pure candidate computation")
        self.stage, self.reason = stage, reason
        self.evidence, self.input_hashes = list(evidence), input_hashes
        super().__init__(reason)


class RunAborted(runtime.IntegrityError):
    """Carries the full ledger even when compromised paths cannot be written."""
    def __init__(self, result):
        self.result = copy.deepcopy(result)
        super().__init__("run/publication failed; attempt evidence retained, no automatic recovery")


def _coverage(slots):
    counts = Counter(row["status"] for row in slots)
    return {state: counts[state] for state in c.SLOT_STATUS}


def _matrix_status(slots, stopped):
    counts = _coverage(slots)
    if stopped or counts["partial"] or counts["failed"] or counts["not_started"]:
        engineering = "fail"
    elif counts["inconclusive"]:
        engineering = "inconclusive"
    else:
        engineering = "pass"
    return _status("failed" if stopped else "complete", engineering)


def _recovered_failure_evidence(backend, identity):
    """Return only cached, slot-local evidence; never recover by reading paths.

    A recovery hook is best-effort because a path, journal or root may already
    be unsafe.  Invalid hook output is ignored: the caller is already globally
    stopped and retains its in-memory ledger without trusting a forged fragment.
    """
    try:
        recovered = backend.failure_evidence(copy.deepcopy(identity))
        if type(recovered) is not dict or set(recovered) - {"identity", "evidence", "input_hashes"}:
            return {}
        if v.canonical_json(recovered.get("identity")) != v.canonical_json(identity):
            return {}
        result, defs = {}, common_defs()
        if "evidence" in recovered:
            v._shape(recovered["evidence"], {"type": "array", "items": {"$ref": "#/$defs/payload"}, "$defs": defs})
            prefix = "datasets/"+identity["dataset_id"]+"/"
            evaluation = "evaluations/"+identity["evaluation_id"]+".json"
            allowed = {prefix+name for name in m.DATASET_FILES} | {evaluation}
            paths = [item["path"] for item in recovered["evidence"]]
            if len(paths) != len(set(paths)) or any(path not in allowed for path in paths):
                return {}
            result["evidence"] = copy.deepcopy(recovered["evidence"])
        if "input_hashes" in recovered:
            v._shape(recovered["input_hashes"], {"$ref": "#/$defs/input_hashes", "$defs": defs})
            result["input_hashes"] = copy.deepcopy(recovered["input_hashes"])
        return result
    except BaseException:
        return {}


def _retain_recovered(slot, backend):
    """Fill only absent fields; a recovery hook can never replace known facts."""
    recovered = _recovered_failure_evidence(backend, slot["identity"])
    if not slot["evidence"] and "evidence" in recovered:
        slot["evidence"] = recovered["evidence"]
    if slot["input_hashes"] is None and "input_hashes" in recovered:
        slot["input_hashes"] = recovered["input_hashes"]


def _has_global_cause(exc):
    """A producer-boundary cause anywhere cannot become an ordinary cell error.

    ``raise ... from ...`` retains both an explicit cause and an implicit
    context.  ExceptionGroup adds further branches.  A pure ``CellFailure``
    remains ordinary only when its complete graph excludes I/O, contract and
    integrity failures, and process-control interrupts.  Traverse every edge
    iteratively so cycles and deeply nested synthetic failures remain bounded.
    """
    seen, pending = set(), [exc]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        # IntegrityError is a V03ValidationError subclass.  Keep both names in
        # this boundary declaration to make the producer/contract semantics
        # explicit if that inheritance is ever changed.
        if isinstance(current, (OSError, runtime.IntegrityError,
                                v.V03ValidationError, KeyboardInterrupt, SystemExit)):
            return True
        pending.extend((current.__cause__, current.__context__))
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
    return False


def _drive(role: str, backend, boundary):
    """Fixed inventory engine. backend is private; fake fixtures cannot publish formal.

    Every begin/done transition is journaled. A global integrity failure stops
    subsequent work; normal cell exceptions do not erase or replace other slots.
    Returns all planned slots, even on interrupt or source/path/pairing failure.
    """
    slots, stopped, paired = planned_slots(role), False, {}
    try:
        backend.begin(planned_metadata(role))
    except BaseException:
        return slots, True
    for index, slot in enumerate(slots):
        stage = "integrity"
        try:
            boundary()
            backend.started(index, copy.deepcopy(slot["identity"]))
            stage = "materialization"
            completion = backend.evaluate(index, copy.deepcopy(slot["identity"]))
            try:
                defs = common_defs()
                v._shape(completion, {**defs["slot"], "$defs": defs})
            except v.V03ValidationError as exc:
                raise runtime.IntegrityError("backend slot shape invalid") from exc
            runtime.require(v.canonical_json(completion["identity"]) == v.canonical_json(slot["identity"]), "backend changed slot identity")
            runtime.require(completion["status"] in ("success", "inconclusive"), "backend returned partial as completed")
            runtime.require(completion["input_hashes"] is not None and bool(completion["evidence"]), "completed slot lacks evidence")
            pair_key = slot["identity"]["dataset_id"]
            hashes = v.canonical_json(completion["input_hashes"])
            runtime.require(paired.setdefault(pair_key, hashes) == hashes, "candidate paired inputs differ")
            slot.update(copy.deepcopy(completion))
            stage = "integrity"
            boundary()
        except runtime.IntegrityError:
            _retain_recovered(slot, backend)
            slot.update(status="failed", failure_stage="integrity", safe_reason="input_changed")
            stopped = True
        except CellFailure as exc:
            if _has_global_cause(exc):
                _retain_recovered(slot, backend)
                slot.update(status="failed", failure_stage="integrity", safe_reason="exception")
                stopped = True
            else:
                slot.update(status="partial" if exc.evidence else "failed", failure_stage=exc.stage,
                            safe_reason=exc.reason, evidence=exc.evidence, input_hashes=exc.input_hashes)
        except (KeyboardInterrupt, SystemExit):
            _retain_recovered(slot, backend)
            slot.update(status="partial" if slot["evidence"] else "failed", failure_stage=stage, safe_reason="incomplete")
            stopped = True
        except BaseException:
            _retain_recovered(slot, backend)
            slot.update(status="failed", failure_stage="integrity", safe_reason="exception")
            stopped = True
        if stopped:
            # After a global source/root/I/O/interrupt failure do not attempt a
            # further journal write against the potentially unsafe boundary.
            break
        try:
            backend.finished(index, copy.deepcopy(slot))
        except BaseException:
            # A failed evidence write is global. The returned complete ledger is
            # still available if the path is no longer safe for persistence.
            slot.update(status="partial" if slot["evidence"] else "failed", failure_stage="publication", safe_reason="incomplete")
            stopped = True
        if stopped:
            break
    return slots, stopped


class _DiskBackend:
    def __init__(self, store, checkout):
        self.store, self.checkout = store, checkout
        self.pair_id, self.pair, self._failure = None, None, {}

    def begin(self, planned):
        self.store.write("planned.json", m.json_bytes(planned))

    def started(self, index, identity):
        self.store.write(f"journal/{index:04d}-started.json", m.json_bytes(identity))

    def finished(self, index, slot):
        self.store.write(f"journal/{index:04d}-done.json", m.json_bytes(slot))

    def failure_evidence(self, identity):
        # This is an in-memory snapshot, updated only after exclusive write
        # readback and dataset validation.  It must not perform recovery I/O.
        return copy.deepcopy(self._failure.get(identity["evaluation_id"], {"identity": dict(identity)}))

    def _remember(self, identity, evidence, hashes=None):
        saved = {"identity": dict(identity), "evidence": copy.deepcopy(evidence)}
        if hashes is not None:
            saved["input_hashes"] = copy.deepcopy(hashes)
        self._failure[identity["evaluation_id"]] = saved

    def evaluate(self, index, identity):
        self._remember(identity, [])
        if identity["pair_id"] != self.pair_id:
            self.pair_id, self.pair = identity["pair_id"], None
            try:
                pair = m.materialize_pair(identity)
                runtime.require(type(pair) is tuple and len(pair) == 2, "paired materializer returned incomplete pair")
                m.validate_pair(*pair)
                runtime.require(pair[0].identity_json == v.canonical_json(m.identity_for(identity, "core")), "materializer identity drift")
                for data in pair:
                    own = v.strict_json(data.identity_json)
                    for name, raw in data.entries:
                        self.store.write("datasets/"+own["dataset_id"]+"/"+name, raw)
                        prefix = "datasets/"+identity["dataset_id"]+"/"
                        captured = [self.store.expected[p] for p in sorted(self.store.expected) if p.startswith(prefix)]
                        self._remember(identity, captured)
                self.pair = pair
            except runtime.IntegrityError:
                raise
            except OSError as exc:
                raise runtime.IntegrityError("paired saved-input I/O failed") from exc
            except v.V03ValidationError as exc:
                raise runtime.IntegrityError("paired materialization contract failed") from exc
            except Exception as exc:
                raise runtime.IntegrityError("paired materialization failed") from exc
        prefix = "datasets/"+identity["dataset_id"]+"/"
        evidence = [self.store.expected[p] for p in sorted(self.store.expected) if p.startswith(prefix)]
        self._remember(identity, evidence)
        hashes = None
        try:
            expected = self.pair[c.STRATA.index(identity["stratum"])].files()
            # All candidates read the one persisted observation file, not a
            # regenerated per-candidate copy or the materializer's latent array.
            files = {name: self.store.read(prefix+name) for name in m.DATASET_FILES}
            runtime.require(files == expected, "candidate input bytes differ from paired saved capture")
            hashes = m.validate_dataset(identity, files)
            self._remember(identity, evidence, hashes)
        except runtime.IntegrityError:
            raise
        except OSError as exc:
            raise runtime.IntegrityError("saved input read/validation I/O failed") from exc
        except v.V03ValidationError as exc:
            raise runtime.IntegrityError("saved input validation failed") from exc
        except Exception as exc:
            raise runtime.IntegrityError("saved input validation failed") from exc
        try:
            claimed = _execute_candidate(copy.deepcopy(identity), dict(files), self.checkout)
            result = verify_evaluation(claimed, identity, files, self.checkout)
        except runtime.IntegrityError:
            raise
        except OSError as exc:
            raise runtime.IntegrityError("candidate computation I/O failed") from exc
        except v.V03ValidationError as exc:
            raise runtime.IntegrityError("candidate computation contract failed") from exc
        except Exception as exc:
            raise CellFailure("scoring", evidence=evidence, input_hashes=hashes) from exc
        try:
            runtime.require({name: self.store.read(prefix+name) for name in m.DATASET_FILES} == files, "input changed during evaluation")
            name = "evaluations/"+identity["evaluation_id"]+".json"
            self.store.write(name, m.json_bytes(result))
            evidence = [*evidence, self.store.expected[name]]
            self._remember(identity, evidence, hashes)
            inconclusive = any(p["status"] != "calibrated" for p in result["profiles"])
            return {"identity": dict(identity), "status": "inconclusive" if inconclusive else "success",
                    "failure_stage": "profile" if inconclusive else None,
                    "safe_reason": "profile_inconclusive" if inconclusive else None,
                    "input_hashes": hashes, "evidence": evidence}
        except runtime.IntegrityError:
            raise
        except OSError as exc:
            raise runtime.IntegrityError("saved input/evidence I/O failed") from exc
        except v.V03ValidationError as exc:
            raise runtime.IntegrityError("evaluation contract/replay failed") from exc
        except Exception as exc:
            raise runtime.IntegrityError("evaluation publication failed") from exc


def summary_bytes(result):
    """Deterministic progress/coverage only; no candidate metric comparisons."""
    lines = ["# Anomaly v0.3 producer", "", "- role: "+result["role"],
             "- run_status: "+result["status"]["run_status"],
             "- engineering_status: "+result["status"]["engineering_status"],
             "- performance_status: not_evaluated", "- independent consumer / native acceptance: pending", ""]
    lines.extend(f"- {state}: {result['coverage'][state]}" for state in c.SLOT_STATUS)
    return ("\n".join(lines)+"\n").encode("utf-8")


def _verify_producer_tree(files: dict[str, bytes], checkout, runtime_snapshot):
    """Read-only complete inventory and semantic replay, with trusted source input."""
    runtime.require("result.json" in files and "summary.md" in files and "planned.json" in files, "producer documents missing")
    result = v.strict_json(files["result.json"])
    v.validate_result_contract(result, source_snapshots=checkout.snapshots())
    role, slots = result["role"], result["evaluations"]
    runtime.require(result["result_type"] == "anomaly-multiseed-v03", "producer result type mismatch")
    runtime.require(files["planned.json"] == m.json_bytes(planned_metadata(role)), "planned inventory tampered")
    runtime.require(files["summary.md"] == summary_bytes(result), "summary reconstruction mismatch")
    entries = [payload_entry(name, files[name]) for name in sorted(files) if name not in ("result.json", "summary.md")]
    runtime.require(result["provenance"] == _provenance(checkout, entries), "producer provenance/inventory mismatch")
    runtime.require(result["status"] == _matrix_status(slots, result["status"]["run_status"] == "failed"), "matrix status/coverage mismatch")
    allowed, seen_stop, last_pair, regenerated = {"planned.json", "result.json", "summary.md", "runtime.json"}, False, None, None
    runtime.require("runtime.json" in files, "runtime evidence missing")
    runtime.require(files["runtime.json"] == m.json_bytes(runtime_snapshot), "runtime provenance changed")
    for index, slot in enumerate(slots):
        identity = slot["identity"]
        if slot["status"] == "not_started":
            seen_stop = True
            continue
        runtime.require(not seen_stop, "started slot follows not_started slot")
        start_name, done_name = f"journal/{index:04d}-started.json", f"journal/{index:04d}-done.json"
        allowed.update((start_name, done_name))
        runtime.require(files.get(start_name) == m.json_bytes(identity) and files.get(done_name) == m.json_bytes(slot), "transition journal mismatch")
        dataset_prefix = "datasets/"+identity["dataset_id"]+"/"
        expected_paths = {dataset_prefix+name for name in m.DATASET_FILES}
        saved = {name: files[dataset_prefix+name] for name in m.DATASET_FILES if dataset_prefix+name in files}
        allowed.update(expected_paths)
        evidence_paths = [e["path"] for e in slot["evidence"]]
        runtime.require(len(set(evidence_paths)) == len(evidence_paths), "duplicate slot evidence")
        for entry in slot["evidence"]:
            runtime.require(entry["path"] in files and payload_entry(entry["path"], files[entry["path"]]) == entry, "evidence bytes/count/hash mismatch")
        if slot["status"] in ("success", "inconclusive"):
            runtime.require(set(saved) == set(m.DATASET_FILES), "completed slot missing saved input")
            if identity["pair_id"] != last_pair:
                last_pair, regenerated = identity["pair_id"], m.materialize_pair(identity)
                m.validate_pair(*regenerated)
            expected = regenerated[c.STRATA.index(identity["stratum"])].files()
            runtime.require(saved == expected, "saved dataset differs from deterministic paired replay")
            hashes = m.validate_dataset(identity, saved)
            runtime.require(slot["input_hashes"] == hashes, "candidate input hash mismatch")
            name = "evaluations/"+identity["evaluation_id"]+".json"
            allowed.add(name)
            runtime.require(name in files and set(evidence_paths) == expected_paths | {name}, "completed evaluation evidence incomplete")
            evaluation = verify_evaluation(v.strict_json(files[name]), identity, saved, checkout)
            inconclusive = any(p["status"] != "calibrated" for p in evaluation["profiles"])
            runtime.require(slot["status"] == ("inconclusive" if inconclusive else "success"), "profile inconclusive converted to success")
        else:
            # Failure rows can preserve only already obtained input/evaluation
            # evidence. They cannot invent foreign paths or a successful metric.
            name = "evaluations/"+identity["evaluation_id"]+".json"
            allowed.add(name)
            runtime.require(set(evidence_paths) <= expected_paths | {name}, "failure evidence escaped slot")
            runtime.require(slot["input_hashes"] is None or slot["input_hashes"] == m.validate_dataset(identity, saved), "partial paired input mismatch")
    runtime.require(set(files) <= allowed, "unplanned payload/path inventory")
    return {"evaluations": len(slots), "coverage": result["coverage"], "performance_status": "not_evaluated",
            "independent_audit": "not_performed", "native_acceptance": "not_completed"}


def _run_prepared(role, store, checkout, runtime_snapshot, boundary):
    """Private S3 engine integration; caller supplies already bound fixture objects."""
    slots = planned_slots(role)
    result = {"schema_version": "0.3", "result_type": "anomaly-multiseed-v03", "role": role,
              "planned_counts": c.counts(role), "evaluations": slots, "coverage": _coverage(slots),
              "status": _status(), "provenance": _provenance(checkout, [])}
    try:
        store.write("runtime.json", m.json_bytes(runtime_snapshot))
        backend = _DiskBackend(store, checkout)
        slots, stopped = _drive(role, backend, boundary)
        result.update(evaluations=slots, coverage=_coverage(slots), status=_matrix_status(slots, stopped))
        # A stopped run may have lost its root after an I/O/interrupt boundary.
        # Return the complete in-memory ledger without reading, writing,
        # preserving, publishing, or rechecking that unsafe boundary.
        if stopped:
            return {"result": result, "publication": None}
        result["provenance"] = _provenance(checkout, [store.expected[p] for p in sorted(store.expected)])
        v.validate_result_contract(result, source_snapshots=checkout.snapshots())
        store.write("result.json", m.json_bytes(result))
        store.write("summary.md", summary_bytes(result))
        receipt = store.publish(lambda files: _verify_producer_tree(files, checkout, runtime_snapshot), boundary)
        return {"result": result, "publication": receipt}
    except BaseException as exc:
        result["status"] = _status("failed", "fail")
        try:
            store.preserve_failure(result)
        except BaseException:
            pass  # Unsafe/unwritable roots stay untouched; memory ledger survives.
        raise RunAborted(result) from exc


def run_campaign(root: Path, role: str, *, expected_head: str):
    """Fail closed before claims, generation or ACL operations until S4 freeze."""
    runtime.require(type(role) is str and role in c.ROLES, "unknown campaign role")
    # Unsupported platforms must fail first, including before output resolution.
    runtime.probe_runtime(root)
    runtime.require_campaign_acceptance()
    # The formal publisher is deliberately not connected in S3. S4 must install
    # its separately accepted Windows publisher and complete runtime inventory.


def validate_only(root: Path, role="holdout"):
    """Captured frozen-bundle validation and count oracle. No data or output."""
    root = runtime.regular_path(root, directory=True)
    snapshots = {name: read_regular(root/name) for name in (*c.CONFIG_PATHS, *c.SCHEMA_PATHS)}
    fixture = v.strict_json(read_regular(root/"tests/fixtures/anomaly-v03-plan-snapshots.json"))
    runtime.require(fixture["science_revision"] == c.SCIENCE_REVISION and fixture["status_revision"] == c.STATUS_REVISION, "plan snapshot revisions")
    report = v.validate_bundle(snapshots,
        science_plan_raw=zlib.decompress(base64.b85decode(fixture["science_zlib_base85"])),
        status_plan_raw=zlib.decompress(base64.b85decode(fixture["status_zlib_base85"])))
    return {"validation_status": report["validation_status"], "planned_counts": c.counts(role),
            "planned_slots": len(planned_slots(role)), "run_status": "not_run", "performance_status": "not_evaluated",
            "source_runtime_acceptance": runtime.acceptance_requirements(), "output_created": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Anomaly v0.3 S3 contract/count inspection; S4/S5 run is gated")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--role", choices=c.ROLES, default="holdout")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--expected-head")
    args = parser.parse_args(argv)
    try:
        if args.run:
            run_campaign(args.root, args.role, expected_head=args.expected_head)
        else:
            print(json.dumps(validate_only(args.root, args.role), ensure_ascii=False, sort_keys=True))
        return 0
    except (v.V03ValidationError, OSError, ValueError):
        print("anomaly v0.3: contract/runtime/acceptance boundary rejected; no campaign permission")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
