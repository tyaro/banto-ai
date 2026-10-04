"""Bound two pinned invented saved readers into a partial one-seed contribution.

The external pinset is a required argument, never derived from local inputs.
This read-only adapter reopens only the small retained control records, then
writes a new result root. It does not reopen saved payloads, authenticate a
historical campaign, or grant formal evaluation credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import _anomaly_v03_io as io  # noqa: E402
from banto_ai import _anomaly_v03_runtime as paths  # noqa: E402
from banto_ai import anomaly_v03 as v  # noqa: E402
from banto_ai import anomaly_v03_observation_audit as pinned  # noqa: E402
from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage  # noqa: E402
from banto_ai import anomaly_v03_preformal_saved_seed_contribution as seed  # noqa: E402
from tools import preformal_saved_row_coverage_pair as pair  # noqa: E402


MAX_RESULT = 64 * 1024
OUTPUT_NAME = re.compile(
    r'anomaly-v03-preformal-saved-seed-contribution-[a-z0-9][a-z0-9-]*\Z')


def _pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _revision(repo: Path) -> str:
    revision = paths._git(repo, 'rev-parse', 'HEAD').decode('ascii').strip()
    v.require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None and
              not paths._git(repo, 'status', '--porcelain',
                             '--untracked-files=normal'),
              'clean trial source revision')
    return revision


def _output_path(repo: Path, name: str) -> Path:
    v.require(type(name) is str and OUTPUT_NAME.fullmatch(name) is not None,
              'new saved seed contribution root name')
    repo = paths.regular_path(repo, directory=True)
    artifacts = paths.regular_path(repo / 'artifacts', directory=True)
    target = artifacts / name
    v.require(not target.exists(), 'new dedicated saved seed contribution root')
    paths.regular_path(target / 'result.json', missing=True)
    return target


def _entries(repo: Path, pinset_root: str, pinset_pin: dict) -> list[dict]:
    pinset_path = pair._root_path(repo, pinset_root, pinset=True) / 'pins.json'
    raw = pinned.read_pinned(pinset_path, pinset_pin, pair.MAX_PINSET)
    value = v.strict_json(raw)
    v.require(raw == v.canonical_json(value) and type(value) is dict and
              set(value) == {'format', 'invented_only',
                             'formal_permission', 'entries'} and
              value['format'] == pair.FORMAT and
              value['invented_only'] is True and
              value['formal_permission'] is False and
              type(value['entries']) is list and
              len(value['entries']) == len(pair.INDICES),
              'pinned invented pair input manifest')
    entries = []
    for index, declared in zip(pair.INDICES, value['entries']):
        expected = pair.source_paths(index)
        v.require(type(declared) is dict and
                  set(declared) == {'chunk_index', 'attempt', 'files'} and
                  type(declared['chunk_index']) is int and
                  declared['chunk_index'] == index and
                  type(declared['attempt']) is int and
                  declared['attempt'] == 1 and
                  type(declared['files']) is dict and
                  set(declared['files']) == set(expected),
                  'exact retained pair file inventory')
        entry = {'expected_pins': {}}
        for name, relative in sorted(expected.items()):
            descriptor = declared['files'][name]
            v.safe_relative_path(relative)
            v.require(type(descriptor) is dict and
                      set(descriptor) == {'path', 'pin'} and
                      descriptor['path'] == relative,
                      'exact retained pair path ' + name)
            pin = descriptor['pin']
            entry[name + '_raw'] = pinned.read_pinned(
                repo / relative, pin, coverage.RAW_LIMITS[name])
            entry['expected_pins'][name] = pin
        reread = v.strict_json(entry['result_raw'])
        suffix = f'c0{index}1'
        artifacts = repo / 'artifacts'
        v.require(type(reread) is dict and
                  reread.get('chunk_index') == index and
                  reread.get('source_root') == str(
                      artifacts / ('anomaly-v03-preformal-registered-attempt-' + suffix)) and
                  reread.get('output_root') == str(
                      artifacts / ('anomaly-v03-preformal-saved-row-reread-' + suffix)) and
                  reread.get('manifest_path') == str(repo / expected['manifest']) and
                  reread.get('row_projection_path') == str(repo / expected['rows']),
                  'exact retained pair reread and attempt roots')
        entries.append(entry)
    return entries


def run(pinset_root: str, pinset_pin: dict, output_root: str,
        *, repo: Path = ROOT) -> dict:
    repo = paths.regular_path(repo, directory=True)
    target = _output_path(repo, output_root)
    revision = _revision(repo)
    entries = _entries(repo, pinset_root, pinset_pin)
    result = seed.aggregate_saved_seed(entries, registered_seed_index=0)
    v.require(result['format'] == seed.FORMAT and
              result['status'] == 'partial_seed_contribution_unanchored' and
              result['invented_only'] is True and
              result['registered_seed_index'] == 0 and
              result['invented_cluster_id'] == 'invented-00' and
              result['planned_layouts'] == 12 and
              result['bound_layouts'] == 2 and
              result['layout_ids'] == [0, 1] and
              result['missing_layouts'] == list(range(2, 12)) and
              result['bound_evaluations'] == 12 and
              result['planned_evaluations_for_seed'] == 72 and
              result['cluster_contribution'] is None and
              len(result['source_chunks']) == 2 and
              all(result.get(name) == expected
                  for name, expected in seed.CLOSED.items()),
              'bounded partial invented seed contribution')
    result['external_pinset_pin'] = pinset_pin
    result['trial_source_revision'] = revision
    output_raw = v.canonical_json(result)
    v.require(0 < len(output_raw) <= MAX_RESULT,
              'bounded saved seed contribution result')
    v.require(_revision(repo) == revision, 'trial source changed')
    target.mkdir()
    io._exclusive(target / 'result.json', output_raw)
    return {'status': result['status'], 'output': str(target / 'result.json'),
            'output_pin': _pin(output_raw), 'bound_layouts': 2,
            'bound_evaluations': 12, 'formal_permission': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pinset-root', required=True)
    parser.add_argument('--pinset-pin', type=pair._pin_arg, required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.pinset_root, args.pinset_pin,
                         args.output_root), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
