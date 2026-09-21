"""One selected chunk producer core; no CLI, scheduler, or execution permission."""
from __future__ import annotations

from . import anomaly_v03 as v
from . import anomaly_v03_chunk_contract as chunk
from . import anomaly_v03_engineering as engine
from . import anomaly_v03_engineering_contract as policy


def verify_payloads(files, checkout, observed, campaign, index, attempt):
    manifest = v.strict_json(files["manifest.json"])
    report = chunk.validate_manifest(manifest, campaign, index, attempt)
    engine._verify_manifest_payloads(files, checkout, observed, manifest, chunk.new_manifest(campaign, index, attempt))
    return report


def execute_chunk(store, checkout, observed, campaign, index, attempt, started, *, boundary, sample_memory):
    """Run one owned store; caller supplies source/runtime/resource boundaries.

    Reuses producer-side generation/replay, not an independent scientific audit.
    No attempt-root creation, process launch, or journal mutation is performed here.
    """
    planned = chunk.new_manifest(campaign, index, attempt)
    policy.validate_source(checkout.source_descriptor())
    engine._same(checkout.source_descriptor()["revision"], campaign["source_bindings"]["producer_revision"],
                 "chunk producer revision differs from campaign")
    policy.validate_runtime(observed)
    return engine._execute_manifest(store, checkout, observed, planned, started,
        boundary=boundary, sample_memory=sample_memory,
        validate_manifest=lambda value: chunk.validate_manifest(value, campaign, index, attempt),
        verify_payloads=lambda files: verify_payloads(files, checkout, observed, campaign, index, attempt))
