"""Selected dev/smoke chunk contract. No execution, coverage, or budget freeze."""
from __future__ import annotations

import copy

from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_engineering_contract as legacy
from . import anomaly_v03_saved_audit as audit

PLAN_FORMAT = "anomaly-v03-dev-smoke-chunk-plan-v1"
MANIFEST_FORMAT = "anomaly-v03-dev-smoke-chunk-result-v1"
SCOPE = "engineering-dev-smoke-chunk"


def chunk_plan(campaign, chunk_index, attempt):
    """Select exactly one registered six-slot chunk from the external plan."""
    checkpoints.validate_plan(campaign)
    v.require(type(chunk_index) is int and 0 <= chunk_index < len(campaign["chunks"]), "chunk index outside plan")
    v.require(type(attempt) is int and 1 <= attempt <= checkpoints.MAX_RECORDS, "chunk attempt number")
    chunk = campaign["chunks"][chunk_index]
    # Science, counts, and validation caps are shared. These caps do not freeze
    # the still-unset controller, campaign, producer, or consumer run budgets.
    value = legacy.fixed_plan()
    value.update(format=PLAN_FORMAT, scope=SCOPE, identities=copy.deepcopy(chunk["identities"]),
        binding={"campaign_plan_sha256": v.canonical_sha256(campaign), "chunk_index": chunk_index,
                 "attempt": attempt, "role": chunk["role"], "seed": chunk["seed"], "layout": chunk["layout"],
                 "identities_sha256": chunk["identities_sha256"]},
        source_bindings=copy.deepcopy(campaign["source_bindings"]),
        runtime_policy=copy.deepcopy(campaign["runtime_policy"]),
        limits_status="provisional_validation_caps", budgets_frozen=False, execution_authorized=False)
    return value


def new_manifest(campaign, chunk_index, attempt):
    return legacy._new_manifest("result", chunk_plan(campaign, chunk_index, attempt), MANIFEST_FORMAT)


def validate_manifest(value, campaign, chunk_index, attempt):
    plan = chunk_plan(campaign, chunk_index, attempt)
    report = legacy._validate_manifest(value, plan, MANIFEST_FORMAT, SCOPE, plan["limits"])
    legacy._exact(value["attempt_id"], "result", "chunk result name")
    if value["source"] is not None:
        legacy._exact(value["source"]["revision"], campaign["source_bindings"]["producer_revision"],
                      "chunk producer revision differs from campaign")
    return {**report, "validation_status": "chunk_manifest_contract_valid", "binding": copy.deepcopy(plan["binding"]),
        "execution_authorized": False, "budgets_frozen": False, "campaign_evaluations_credited": 0}


def audit_chunk_payloads(files, producer, campaign, chunk_index, attempt):
    """Recompute saved score ledgers for the externally selected chunk.

    The caller owns file-size limits, publication, source capture, supervision,
    and journal verification. This function never claims these were performed.
    """
    manifest = v.strict_json(files["manifest.json"])
    validate_manifest(manifest, campaign, chunk_index, attempt)
    return audit._audit_payloads(files, producer, manifest, new_manifest(campaign, chunk_index, attempt))
