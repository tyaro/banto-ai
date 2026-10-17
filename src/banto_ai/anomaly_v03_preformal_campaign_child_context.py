"""Pinned invented campaign context carried to owned fixture children.

This is a narrow lineage check. It neither owns descendants nor authorizes a
registered or formal run.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_preformal_campaign_metadata as metadata
from . import anomaly_v03_reader_evidence as observed


FIELDS = {'plan_path', 'anchor_pin', 'chunk_index', 'attempt'}


def verify_context(value, *, attempt_root, revision):
    """Reopen the exact plan bytes and bind one attempt to that plan."""
    v.require(type(value) is dict and set(value) == FIELDS,
              'exact campaign child context required')
    metadata._pin(value['anchor_pin'], 'campaign child anchor')
    v.require(type(value['chunk_index']) is int and
              0 <= value['chunk_index'] < 480 and
              type(value['attempt']) is int and
              value['attempt'] == 1,
              'bounded first campaign attempt context')
    plan_path = paths.regular_path(Path(value['plan_path']))
    raw = observed._file(plan_path, metadata.MAX_PLAN_BYTES)
    v.require(metadata.pin(raw) == value['anchor_pin'],
              'campaign child plan raw pin changed')
    plan = v.strict_json(raw)
    v.require(raw == metadata.encode_plan(plan) and
              plan_path == Path(plan['root']) / 'plan.json' and
              str(attempt_root) == metadata.attempt_root(
                  plan, value['chunk_index'], value['attempt']) and
              plan['source']['revision'] == revision and
              plan['invented_only'] is True and
              plan['formal_permission'] is False and
              plan['resume_authorized'] is False,
              'campaign child plan/slot/attempt/source binding')
    return copy.deepcopy(value)


def from_parts(plan_path, anchor_pin, chunk_index, attempt, *,
               attempt_root, revision):
    return verify_context({
        'plan_path': str(plan_path), 'anchor_pin': copy.deepcopy(anchor_pin),
        'chunk_index': chunk_index, 'attempt': attempt,
    }, attempt_root=attempt_root, revision=revision)
