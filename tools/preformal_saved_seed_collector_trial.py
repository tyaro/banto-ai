"""Bind retained c001/c011 controls to the unanchored forty-seed inventory.

This reopens one externally pinned partial seed result and the two manifest
records pinned by the older external c01 pinset. It does not reread payloads,
authenticate historical process execution, or authorize a formal campaign.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import _anomaly_v03_io as io  # noqa: E402
from banto_ai import _anomaly_v03_runtime as paths  # noqa: E402
from banto_ai import anomaly_v03 as v  # noqa: E402
from banto_ai import anomaly_v03_consumer_evidence as evidence  # noqa: E402
from banto_ai import anomaly_v03_observation_audit as pinned  # noqa: E402
from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage  # noqa: E402
from banto_ai import anomaly_v03_preformal_saved_seed_collector as collector  # noqa: E402
from tools import preformal_saved_row_coverage_pair as pair  # noqa: E402
from tools import preformal_saved_seed_contribution_trial as seed_trial  # noqa: E402


FORMAT = 'anomaly-v03-preformal-saved-seed-collector-trial-input-v1'
OUTPUT_NAME = re.compile(
    r'anomaly-v03-preformal-saved-seed-collector-[a-z0-9][a-z0-9-]*\Z')
MAX_OUTPUT = 64 * 1024


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _pin_arg(value):
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _revision(repo):
    revision = paths._git(repo, 'rev-parse', 'HEAD').decode('ascii').strip()
    v.require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None and
              not paths._git(repo, 'status', '--porcelain',
                             '--untracked-files=normal'),
              'clean collector trial source revision')
    return revision


def run(pinset_pin, seed_result_pin, output_root, *, repo=ROOT):
    repo = paths.regular_path(repo, directory=True)
    artifacts = paths.regular_path(repo / 'artifacts', directory=True)
    v.require(type(output_root) is str and OUTPUT_NAME.fullmatch(output_root),
              'new collector trial root name')
    target = artifacts / output_root
    v.require(not target.exists(), 'new collector trial root required')
    paths.regular_path(target / 'result.json', missing=True)
    revision = _revision(repo)

    pinset_path = (artifacts /
                   'anomaly-v03-preformal-saved-row-coverage-pins-c01' /
                   'pins.json')
    pinset_raw = pinned.read_pinned(pinset_path, pinset_pin, pair.MAX_PINSET)
    pinset = v.strict_json(pinset_raw)
    v.require(pinset_raw == v.canonical_json(pinset) and
              type(pinset) is dict and set(pinset) ==
              {'format', 'invented_only', 'formal_permission', 'entries'} and
              pinset['format'] == pair.FORMAT and
              pinset['invented_only'] is True and
              pinset['formal_permission'] is False and
              type(pinset['entries']) is list and
              len(pinset['entries']) == len(pair.INDICES),
              'external invented pair pinset')

    manifests = []
    declared_pins = []
    for index, declared in zip(pair.INDICES, pinset['entries']):
        expected = pair.source_paths(index)
        v.require(type(declared) is dict and
                  set(declared) == {'chunk_index', 'attempt', 'files'} and
                  type(declared['chunk_index']) is int and
                  declared['chunk_index'] == index and
                  type(declared['attempt']) is int and
                  declared['attempt'] == 1 and
                  type(declared['files']) is dict and
                  set(declared['files']) == set(expected),
                  'external pair chunk inventory')
        pins = {}
        for name, relative in sorted(expected.items()):
            v.safe_relative_path(relative)
            descriptor = declared['files'][name]
            v.require(type(descriptor) is dict and
                      set(descriptor) == {'path', 'pin'} and
                      descriptor['path'] == relative,
                      'external pair control path ' + name)
            evidence._pin(descriptor['pin'])
            pins[name] = descriptor['pin']
        declared_pins.append(pins)
        manifest_pin = pins['manifest']
        manifest_raw = pinned.read_pinned(
            repo / expected['manifest'], manifest_pin,
            coverage.RAW_LIMITS['manifest'])
        manifests.append({'raw': manifest_raw, 'expected_pin': manifest_pin})

    seed_result_path = (artifacts /
                        'anomaly-v03-preformal-saved-seed-contribution-c01-trial-01' /
                        'result.json')
    seed_result_raw = pinned.read_pinned(
        seed_result_path, seed_result_pin, collector.MAX_SEED_RAW)
    result = collector.collect_saved_seed_contributions([{
        'result_raw': seed_result_raw,
        'expected_result_pin': seed_result_pin,
        'manifest_entries': manifests,
    }])
    seed_result = v.strict_json(seed_result_raw)
    v.require(seed_result.get('external_pinset_pin') == pinset_pin and
              [chunk['entry_pins'] for chunk in seed_result['source_chunks']]
              == declared_pins,
              'seed result bound to all external pair control pins')
    v.require(result['format'] == collector.FORMAT and
              result['status'] == 'partial_unanchored_contribution_inventory' and
              result['seed_indices'] == [0] and
              result['missing_seed_indices'] == list(range(1, 40)) and
              result['chunk_indices'] == [0, 1] and
              result['missing_chunk_indices'] == list(range(2, 480)) and
              result['bound_seeds'] == 1 and
              result['bound_chunks'] == 2 and
              result['bound_evaluations'] == 12 and
              result['manifest_count'] == 2 and
              result['historical_manifest_anchor_consistency_checked'] is True and
              result['cross_seed_manifest_anchor_consistency_checked'] is False and
              result['unanchored_40_seed_contribution'] is None and
              all(result.get(name) == expected
                  for name, expected in collector.CLOSED.items()),
              'retained partial collector result')
    result['trial_input_format'] = FORMAT
    result['external_pinset_pin'] = pinset_pin
    result['external_seed_result_pin'] = seed_result_pin
    result['trial_source_revision'] = revision
    output_raw = v.canonical_json(result)
    v.require(0 < len(output_raw) <= MAX_OUTPUT,
              'bounded collector trial result')
    v.require(_revision(repo) == revision,
              'collector trial source changed')
    target.mkdir()
    io._exclusive(target / 'result.json', output_raw)
    return {'status': result['status'], 'output': str(target / 'result.json'),
            'output_pin': _pin(output_raw), 'bound_chunks': 2,
            'formal_permission': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pinset-pin', type=_pin_arg, required=True)
    parser.add_argument('--seed-result-pin', type=_pin_arg, required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.pinset_pin, args.seed_result_pin,
                         args.output_root), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
