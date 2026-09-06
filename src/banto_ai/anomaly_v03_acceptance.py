"""S4-A engineering inspection contract. Pure, never a campaign authorization.

An externally supplied stable digest checks equality, not execution authenticity.
No receipt, including a self-consistent one, can complete any S4 acceptance gate.
The persisted schema is separate from the nine frozen scientific schemas.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

from . import anomaly_v03 as v
from . import _anomaly_v03_contract as c
from .manifest import ManifestValidationError, validate

SCHEMA_PATH = "schemas/anomaly-v03-engineering-inspection-v1.schema.json"
WORKFLOW = ".github/workflows/ci.yml"
ROLES = ("producer", "analysis", "audit", "worker", "workflow")
REQUIREMENTS = (
    "native-publisher", "protected-dacl", "independent-token", "windows-3.12",
    "windows-3.14.0", "linux-3.12", "linux-3.14", "linux-image-identity",
    "consumer-freeze", "runtime-closure", "dev-smoke-capacity",
)
LIMITATIONS = (
    "observation-not-runtime-closure", "environment-values-not-captured",
    "search-policy-observed-not-enforced", "no-image-attestation",
    "no-native-acceptance", "no-consumer-freeze", "no-campaign-permission",
    "no-memoryerror-root-cause-claim",
)
ENV_NAMES = ("PATH", "PYTHONHASHSEED", "PYTHONHOME", "PYTHONPATH", "PYTHONSAFEPATH", "PYTHONUSERBASE")
FLAG_NAMES = ("debug", "dev_mode", "dont_write_bytecode", "ignore_environment", "inspect", "interactive",
              "isolated", "no_site", "no_user_site", "optimize", "safe_path", "utf8_mode", "verbose")
OWN_SOURCES = ("src/banto_ai/anomaly_v03_acceptance.py", "src/banto_ai/_anomaly_v03_inventory.py",
               SCHEMA_PATH, "tests/test_anomaly_v03_acceptance.py", "tools/evaluator/inspect_anomaly_v03.py")
REQUIRED_PRODUCER_PATHS = (*c.CONFIG_PATHS, *c.SCHEMA_PATHS, c.PLAN_PATH, "src/banto_ai/generator.py", *OWN_SOURCES,
    *("src/banto_ai/"+name+".py" for name in ("anomaly_v03", "_anomaly_v03_contract", "_anomaly_v03_schema",
        "_anomaly_v03_numeric", "anomaly_v03_scoring", "anomaly_v03_episodes", "anomaly_v03_materializer",
        "anomaly_v03_runner", "_anomaly_v03_runtime", "_anomaly_v03_io")), "tools/evaluator/run_anomaly_v03.py")


def receipt_schema():
    """Fresh closed schema; no I/O, runtime probing or scientific configuration."""
    def obj(properties):
        return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
    def arr(items, minimum=0):
        return {"type": "array", "items": items, "minItems": minimum}
    def enum(*values):
        return {"type": "string", "enum": list(values)}
    def nullable(value):
        return {"anyOf": [value, {"type": "null"}]}
    text, boolean = {"type": "string", "minLength": 1}, {"type": "boolean"}
    count, number = {"type": "integer", "minimum": 0}, {"type": "number", "minimum": 0}
    digest, revision = {"type": "string", "pattern": "^[a-f0-9]{64}$"}, {"type": "string", "pattern": "^[a-f0-9]{40}$"}
    file = obj({"path": text, "raw_sha256": digest, "byte_count": count})
    source = obj({"role": enum(*ROLES), "state": enum("collected", "not_collected"),
                  "revision": nullable(revision), "files": arr(file)})
    stable = obj({
        "platform": obj({"system": enum("Windows", "Linux"), "release": text, "version": text,
            "build": nullable(count), "ubr": nullable(count), "edition": text, "architecture": text,
            "filesystem": text, "local_fixed": boolean}),
        "python": obj({"implementation": {"const": "CPython", "type": "string"}, "version": text,
            "compiler": text, "gil_disabled": boolean, "source_tag": text, "pointer_bits": {"const": 64, "type": "integer"},
            "executable": file, "loaded_python_dll": nullable(text),
            "basic_pin": enum("matches-formal-basic-pin", "compatibility-only")}),
        "cpu": obj({"architecture": text, "identity": text, "features": arr(text, 1),
                    "feature_scope": enum("win32-processor-feature-api", "linux-all-processors-intersection")}),
        "startup": obj({"flags": arr(obj({"name": enum(*FLAG_NAMES), "value": {"type": "integer"}}), 1),
            "environment": arr(obj({"name": enum(*ENV_NAMES), "present": boolean}), 1),
            "import_locations": arr(enum("source", "stdlib", "python", "cwd", "external-redacted", "missing-runtime-path")),
            "user_site_enabled": nullable(boolean), "bytecode_writes_disabled": {"const": True, "type": "boolean"}}),
        "stdlib": arr(file, 1), "loaded_native": arr(file, 1), "loaded_extensions": arr(file),
        "sources": arr(source, 5),
        "scope": obj({"phase": {"const": "post-probe-import-observation", "type": "string"},
            "closure_verified": {"const": False, "type": "boolean"},
            "stdlib_policy": {"const": "regular-tree-excluding-site-packages", "type": "string"},
            "native_method": enum("EnumProcessModulesEx", "proc-self-maps"),
            "limitations": {"const": list(LIMITATIONS), "type": "array", "items": text}}),
    })
    schema = obj({"receipt_version": {"const": "s4-a.1", "type": "string"},
        "acceptance_status": {"const": "not_completed", "type": "string"},
        "requirements": obj({name: {"const": "not_completed", "type": "string"} for name in REQUIREMENTS}),
        "stable": stable,
        "observation": obj({"pid": count, "observed_utc": text, "elapsed_seconds": number,
            "free_bytes": count, "peak_process_bytes": nullable(count),
            "system_commit_bytes": nullable(count), "token_ids": {"const": [], "type": "array", "items": text},
            "native_files": arr(obj({"path": text, "physical_path": text, "device": count,
                "inode": {"type": "integer", "minimum": 1}, "nlink": {"type": "integer", "minimum": 1},
                "trust_status": {"const": "not_accepted", "type": "string"}}), 1),
            "native_load_order": arr(text, 1)})})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://banto-ai.local/"+SCHEMA_PATH,
        "description": "S4-A inspection only; all acceptance remains incomplete; no run authority.", **schema}


def _files(rows):
    names = [row["path"] for row in rows]
    v.require(names == sorted(names) and len({name.casefold() for name in names}) == len(names), "unsorted/duplicate file inventory")
    for name in names:
        # The scientific safe-path alphabet deliberately excludes dot-prefixes.
        # Only this exact workflow exception is valid in the engineering schema.
        if name != WORKFLOW:
            v.safe_relative_path(name)


def validate_receipt(receipt, *, expected_stable_sha256: str, source_snapshots: Mapping | None = None):
    """Validate metadata against an EXTERNAL pin; never authenticate acceptance.

    Optional caller-owned snapshots verify each collected role one file at a
    time. They may be lazy mappings; this function never opens a file itself.
    Runtime file bytes are checked by the collector and bound by the external
    stable pin. Volatile observations are shape-checked but not equivalence-pinned.
    """
    v.require(type(expected_stable_sha256) is str and re.fullmatch("[a-f0-9]{64}", expected_stable_sha256), "external stable pin required")
    schema = receipt_schema()
    v.json_value(receipt)
    try:
        validate(receipt, schema)
        v._strict_literals(receipt, schema, schema)
    except (ManifestValidationError, KeyError, TypeError, ValueError, OverflowError) as exc:
        raise v.V03ValidationError("engineering schema violation") from exc
    stable = receipt["stable"]
    v.require(v.canonical_sha256(stable) == expected_stable_sha256, "external stable pin mismatch")
    for key in ("stdlib", "loaded_native", "loaded_extensions"):
        _files(stable[key])
        prefixes = ("stdlib/", "stdlib-zip/") if key == "stdlib" else ("native/",)
        v.require(all(row["path"].startswith(prefixes) for row in stable[key]), "runtime namespace mismatch")
    _files([stable["python"]["executable"]])
    v.require(stable["python"]["executable"]["path"].startswith("python/"), "executable namespace mismatch")
    v.require([s["role"] for s in stable["sources"]] == list(ROLES), "source role inventory")
    native = {row["path"]: row for row in stable["loaded_native"]}
    v.require(all(native.get(row["path"]) == row for row in stable["loaded_extensions"]), "extension missing from native inventory")
    py, host = stable["python"], stable["platform"]
    v.require(re.fullmatch(r"3\.(12|14)\.[0-9]+", py["version"]), "unsupported runtime version")
    v.require(not py["gil_disabled"] and host["local_fixed"], "unsupported runtime mode/filesystem")
    v.require(stable["cpu"]["architecture"] == host["architecture"], "CPU architecture mismatch")
    if host["system"] == "Windows":
        v.require((host["architecture"], host["release"], host["edition"], host["build"], host["ubr"], host["filesystem"]) ==
                  ("AMD64", "25H2", "Professional", 26200, 9168, "NTFS"), "unsupported Windows runtime")
        v.require(host["version"] == "10.0.26200.9168", "Windows version mismatch")
        v.require(py["loaded_python_dll"] in native, "loaded Python DLL missing")
        v.require(stable["scope"]["native_method"] == "EnumProcessModulesEx", "native method mismatch")
        if py["version"].startswith("3.14."):
            pin = c.formal_runtime()
            v.require(py["version"] == "3.14.0" and py["compiler"] == "MSC v.1944 64 bit (AMD64)"
                and py["source_tag"] == "v3.14.0:ebf955d" and py["basic_pin"] == "matches-formal-basic-pin"
                and py["executable"]["raw_sha256"] == pin["python_exe_raw_sha256"]
                and native[py["loaded_python_dll"]]["raw_sha256"] == pin["python_dll_raw_sha256"], "formal basic pin mismatch")
        else:
            v.require(py["basic_pin"] == "compatibility-only", "3.12 is not formal")
    else:
        v.require(host["architecture"] == "x86_64" and host["edition"] == "ubuntu" and host["release"] == "24.04"
            and host["filesystem"] in ("ext4", "xfs", "btrfs")
            and host["build"] is None and host["ubr"] is None and py["loaded_python_dll"] is None
            and py["basic_pin"] == "compatibility-only" and stable["scope"]["native_method"] == "proc-self-maps", "unsupported Linux runtime")
    v.require(stable["cpu"]["feature_scope"] == ("win32-processor-feature-api" if host["system"] == "Windows" else "linux-all-processors-intersection"), "CPU feature scope mismatch")
    features = stable["cpu"]["features"]
    v.require(features == sorted(set(features)), "CPU feature inventory")
    startup = stable["startup"]
    v.require([r["name"] for r in startup["flags"]] == list(FLAG_NAMES), "startup flag inventory")
    v.require([r["name"] for r in startup["environment"]] == list(ENV_NAMES), "environment policy inventory")
    order = receipt["observation"]["native_load_order"]
    v.require(len(order) == len(set(order)) and set(order) == set(native), "native observation inventory")
    identities = receipt["observation"]["native_files"]
    v.require([r["path"] for r in identities] == sorted(native), "native identity inventory")
    v.require(len({r["physical_path"].casefold() for r in identities}) == len(identities), "duplicate native physical path")
    collected = {}
    for source in stable["sources"]:
        _files(source["files"])
        if source["state"] == "not_collected":
            v.require(source["revision"] is None and not source["files"], "uncollected source has claims")
        else:
            v.require(source["revision"] is not None and source["files"], "collected source missing")
            if source["role"] == "workflow":
                v.require([r["path"] for r in source["files"]] == [WORKFLOW], "workflow source missing/extra")
            collected[source["role"]] = source
    v.require("producer" in collected and "workflow" in collected, "producer/workflow required")
    v.require(set(REQUIRED_PRODUCER_PATHS) <= {r["path"] for r in collected["producer"]["files"]}, "required producer source missing")
    v.require(_workflow_count(collected) == 1, "workflow must be separately captured")
    v.require(collected["producer"]["revision"] == collected["workflow"]["revision"], "workflow revision mismatch")
    if source_snapshots is not None:
        v.require(set(source_snapshots) == set(collected), "snapshot role inventory")
        for role, source in collected.items():
            snapshot = source_snapshots[role]
            v.require(set(snapshot) == {"revision", "files"} and snapshot["revision"] == source["revision"], "snapshot revision mismatch")
            v.require(set(snapshot["files"]) == {r["path"] for r in source["files"]}, "source snapshot inventory")
            for row in source["files"]:
                raw = snapshot["files"][row["path"]]
                v.require(type(raw) is bytes and len(raw) == row["byte_count"] and hashlib.sha256(raw).hexdigest() == row["raw_sha256"], "source snapshot bytes mismatch")
    return {"validation_status": "inspection_valid", "acceptance_status": "not_completed",
            "source_bytes_checked": source_snapshots is not None, "execution_authenticated": False,
            "formal_permission": False}


def _workflow_count(collected):
    return sum(row["path"] == WORKFLOW for source in collected.values() for row in source["files"])
