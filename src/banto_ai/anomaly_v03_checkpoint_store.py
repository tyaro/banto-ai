"""Non-overwriting metadata journal storage for one ordinary trusted writer.

Records remain declarations. No attempt execution, campaign credit or cleanup.
A rename is the append commit point; an externally pinned intent can recover a
lost receipt by reading that exact committed record, never by writing it again.
"""
from __future__ import annotations

from pathlib import Path

from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_engineering_contract as policy

MAX_PLAN_BYTES = 1024**2
MAX_RECORD_BYTES = 16 * 1024
MAX_JOURNAL_BYTES = 16 * 1024**2
RECEIPT_FORMAT = "anomaly-v03-checkpoint-metadata-receipt-v1"


def read_metadata(path, maximum):
    path = rt.regular_path(path)
    rt.require(path.stat().st_size <= maximum, "metadata file too large")
    raw = storage.read_regular(path)
    rt.require(len(raw) <= maximum, "metadata file grew beyond limit")
    return raw


def load_journal(plan_path, journal_dir, plan_hash, count, head_hash):
    rt.require(type(count) is int and 0 <= count <= checkpoints.MAX_RECORDS, "journal record count limit")
    plan_raw = read_metadata(plan_path, MAX_PLAN_BYTES)
    plan = v.strict_json(plan_raw)
    journal_dir = rt.regular_path(journal_dir, directory=True)
    expected = [f"{number:06d}.json" for number in range(1, count + 1)]
    rt.require(sorted(p.name for p in journal_dir.iterdir()) == expected, "journal file inventory differs")
    records, pins, total = [], [], 0
    for name in expected:
        path = journal_dir / name
        raw = read_metadata(path, MAX_RECORD_BYTES)
        total += len(raw)
        rt.require(total <= MAX_JOURNAL_BYTES, "journal byte limit")
        record = v.strict_json(raw)
        rt.require(raw == checkpoints.encode_record(record), "noncanonical or incomplete journal record")
        records.append(record)
        pins.append((path, storage.sha(raw)))
    report = checkpoints.reduce_journal(plan, records, expected_plan_sha256=plan_hash,
        expected_record_count=count, expected_head_sha256=head_hash)
    rt.require(read_metadata(plan_path, MAX_PLAN_BYTES) == plan_raw, "plan changed during inspection")
    rt.require(sorted(p.name for p in journal_dir.iterdir()) == expected, "journal changed during inspection")
    for path, digest in pins:
        rt.require(storage.sha(read_metadata(path, MAX_RECORD_BYTES)) == digest, "journal changed during inspection")
    return plan, records, report


def _layout(root, *, pending=()):
    root = rt.regular_path(root, directory=True)
    storage._local_parent(root.parent)
    policy.attempt_name(root.name)
    rt.require({p.name for p in root.iterdir()} == {"plan.json", "journal", "pending"}, "metadata store layout differs")
    rt.regular_path(root / "plan.json")
    rt.regular_path(root / "journal", directory=True)
    folder = rt.regular_path(root / "pending", directory=True)
    rt.require(sorted(p.name for p in folder.iterdir()) == sorted(pending), "pending metadata requires investigation")
    return root


def _receipt(root, plan_hash, count, head_hash):
    return {"format": RECEIPT_FORMAT, "scope": "metadata-only", "root": str(root),
        "journal": {"expected_plan_sha256": plan_hash, "expected_record_count": count,
                    "expected_head_sha256": head_hash},
        "execution_authorized": False, "resume_authorized": False,
        "campaign_completed": False, "formal_permission": False}


def validate_receipt(root, receipt):
    root = Path(root).absolute()
    rt.require(type(receipt) is dict and type(receipt.get("journal")) is dict, "metadata receipt fields")
    pins = receipt["journal"]
    rt.require(set(pins) == {"expected_plan_sha256", "expected_record_count", "expected_head_sha256"}, "receipt pins")
    expected = _receipt(root, pins["expected_plan_sha256"], pins["expected_record_count"], pins["expected_head_sha256"])
    rt.require(v.canonical_json(receipt) == v.canonical_json(expected), "receipt scope/root/fields changed")
    # Hash/count types are also checked by the journal reducer on every use.
    return pins


def _load(root, pins, *, pending=()):
    root = _layout(root, pending=pending)
    plan, records, report = load_journal(root / "plan.json", root / "journal", pins["expected_plan_sha256"],
                                       pins["expected_record_count"], pins["expected_head_sha256"])
    rt.require(read_metadata(root / "plan.json", MAX_PLAN_BYTES) == v.canonical_json(plan) + b"\n",
               "store plan is not canonical")
    return root, plan, records, report


def create_store(parent, name, plan):
    """Create a NEW metadata-only root; leave all failed/incomplete state intact."""
    checkpoints.validate_plan(plan)
    raw = v.canonical_json(plan) + b"\n"
    rt.require(len(raw) <= MAX_PLAN_BYTES, "plan byte limit")
    parent = storage._local_parent(Path(parent))
    root = parent / policy.attempt_name(name)
    rt.regular_path(root, directory=True, missing=True)
    root.mkdir()  # Existing roots, including incomplete initialization, are refused.
    (root / "journal").mkdir()
    (root / "pending").mkdir()
    pending = root / "pending/plan.json"
    storage._exclusive(pending, raw)
    storage._rename_no_replace(pending, root / "plan.json")
    return recover_initialization(root, v.canonical_sha256(plan))


def recover_initialization(root, expected_plan_sha256):
    """Read an already initialized EMPTY store if its first receipt was lost."""
    pins = {"expected_plan_sha256": expected_plan_sha256, "expected_record_count": 0,
            "expected_head_sha256": expected_plan_sha256}
    root, _, _, _ = _load(root, pins)
    return _receipt(root, expected_plan_sha256, 0, expected_plan_sha256)


def inspect_store(root, receipt):
    pins = validate_receipt(root, receipt)
    return _load(root, pins)[3]


def _intent(plan, records, record, pins):
    raw = checkpoints.encode_record(record)
    rt.require(len(raw) <= MAX_RECORD_BYTES, "record byte limit")
    rt.require(sum(len(checkpoints.encode_record(r)) for r in records) + len(raw) <= MAX_JOURNAL_BYTES,
               "journal byte limit")
    next_pins = {"expected_plan_sha256": pins["expected_plan_sha256"], "expected_record_count": len(records) + 1,
                 "expected_head_sha256": storage.sha(raw)}
    checkpoints.reduce_journal(plan, records + [record], **next_pins)
    return raw, next_pins


def append_record(root, receipt, record):
    """Validate old pins and full next history before any exclusive staged write."""
    pins = validate_receipt(root, receipt)
    root, plan, records, _ = _load(root, pins)
    raw, next_pins = _intent(plan, records, record, pins)
    name = f"{next_pins['expected_record_count']:06d}.json"
    pending = root / "pending" / name
    storage._exclusive(pending, raw)
    # Still one writer; recheck the saved prefix and staged intent before commit.
    _load(root, pins, pending=(name,))
    rt.require(storage.read_regular(pending) == raw, "staged intent changed")
    storage._rename_no_replace(pending, root / "journal" / name)
    _load(root, next_pins)
    return _receipt(root, next_pins["expected_plan_sha256"], next_pins["expected_record_count"], next_pins["expected_head_sha256"])


def recover_append(root, previous_receipt, intended_record):
    """Recover a lost receipt after commit; exact old prefix plus ONE intended row.

    Never publish pending bytes, clean partial files, choose a new head from the
    directory, or accept an extra tail. The caller retains the intended record.
    """
    pins = validate_receipt(root, previous_receipt)
    count = pins["expected_record_count"]
    rt.require(type(count) is int and 0 <= count < checkpoints.MAX_RECORDS, "previous record count")
    raw = checkpoints.encode_record(intended_record)
    rt.require(len(raw) <= MAX_RECORD_BYTES, "record byte limit")
    next_pins = {"expected_plan_sha256": pins["expected_plan_sha256"], "expected_record_count": count + 1,
                 "expected_head_sha256": storage.sha(raw)}
    root, plan, records, _ = _load(root, next_pins)
    checkpoints.reduce_journal(plan, records[:-1], **pins)
    rt.require(checkpoints.encode_record(records[-1]) == raw, "committed record is not retained intent")
    return _receipt(root, next_pins["expected_plan_sha256"], next_pins["expected_record_count"], next_pins["expected_head_sha256"])
