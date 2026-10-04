"""Collect pinned saved-row coverage for the retained invented c001/c011 pair.

``prepare`` writes the small input-file pins in a new root. ``run`` needs the
pin of that external file and writes a separate, bounded result. This adapter
only reopens the ten small control records per chunk; the saved payloads were
reopened by the retained reread receipts, not by this command. It does not
authenticate one producer campaign or grant formal evaluation credit.
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


FORMAT = 'anomaly-v03-preformal-saved-row-coverage-pair-input-pins-v1'
INDICES = (0, 1)
MAX_PINSET = 16 * 1024
MAX_RESULT = 64 * 1024
PINSET_NAME = re.compile(r'anomaly-v03-preformal-saved-row-coverage-pins-[a-z0-9][a-z0-9-]*\Z')
OUTPUT_NAME = re.compile(r'anomaly-v03-preformal-saved-row-coverage-[a-z0-9][a-z0-9-]*\Z')


def _pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _pin_arg(value: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None or int(match.group(1)) > MAX_PINSET:
        raise argparse.ArgumentTypeError('expected bounded bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def _root_name(value: str, *, pinset: bool) -> str:
    pattern = PINSET_NAME if pinset else OUTPUT_NAME
    v.require(type(value) is str and pattern.fullmatch(value) is not None,
              'new coverage root name')
    if not pinset:
        v.require(not value.startswith('anomaly-v03-preformal-saved-row-coverage-pins-'),
                  'result root distinct from pinset')
    return value


def source_paths(chunk_index: int) -> dict[str, str]:
    """Derive the exact attempt-1 source and reread control-file inventory."""
    v.require(type(chunk_index) is int and chunk_index in INDICES,
              'retained invented pair chunk index')
    suffix = f'c0{chunk_index}1'
    attempt = 'artifacts/anomaly-v03-preformal-registered-attempt-' + suffix
    reread = 'artifacts/anomaly-v03-preformal-saved-row-reread-' + suffix
    manifest = 'artifacts/anomaly-v03-preformal-generated-pinsets-' + suffix
    return {
        'result': reread + '/result.json',
        'rows': reread + '/rows.json',
        'budget': reread + '/resource-budget.json',
        'supervision': reread + '/owned-reader/supervision.json',
        'stdout': reread + '/owned-reader/worker/report.json',
        'manifest': manifest + '/pins.json',
        'receipt': attempt + '/saved/receipt.json',
        'report': attempt + '/saved/report.json',
        'savepoint': attempt + '/saved/savepoint.json',
        'outer': attempt + '/owned-generator/result.json',
    }


def _root_path(repo: Path, name: str, *, pinset: bool) -> Path:
    repo = paths.regular_path(repo, directory=True)
    artifacts = paths.regular_path(repo / 'artifacts', directory=True)
    return artifacts / _root_name(name, pinset=pinset)


def prepare(pinset_root: str, *, repo: Path = ROOT) -> dict:
    target_root = _root_path(repo, pinset_root, pinset=True)
    v.require(not target_root.exists(), 'new external pinset root required')
    paths.regular_path(target_root / 'pins.json', missing=True)
    entries = []
    for index in INDICES:
        files = {}
        for name, relative in sorted(source_paths(index).items()):
            v.safe_relative_path(relative)
            source = paths.regular_path(repo / relative)
            limit = coverage.RAW_LIMITS[name]
            v.require(0 < source.stat().st_size <= limit,
                      'bounded pair coverage source ' + name)
            source_raw = source.read_bytes()
            v.require(0 < len(source_raw) <= limit,
                      'bounded read pair coverage source ' + name)
            files[name] = {'path': relative, 'pin': _pin(source_raw)}
        entries.append({'chunk_index': index, 'attempt': 1, 'files': files})
    value = {'format': FORMAT, 'invented_only': True,
             'formal_permission': False, 'entries': entries}
    raw = v.canonical_json(value)
    v.require(len(raw) <= MAX_PINSET, 'bounded external pair pinset')
    target_root.mkdir()
    io._exclusive(target_root / 'pins.json', raw)
    io._exclusive(target_root / 'pins.json.sha256',
                  (_pin(raw)['sha256'] + '\n').encode('ascii'))
    return {'status': 'prepared', 'pinset': str(target_root / 'pins.json'),
            'pinset_pin': _pin(raw), 'chunk_indices': list(INDICES),
            'invented_only': True, 'formal_permission': False}


def run(pinset_root: str, pinset_pin: dict, output_root: str,
        *, repo: Path = ROOT) -> dict:
    pinset_path = _root_path(repo, pinset_root, pinset=True) / 'pins.json'
    result_root = _root_path(repo, output_root, pinset=False)
    v.require(not result_root.exists(), 'new dedicated pair coverage result root required')
    paths.regular_path(result_root / 'result.json', missing=True)
    raw = pinned.read_pinned(pinset_path, pinset_pin, MAX_PINSET)
    value = v.strict_json(raw)
    v.require(raw == v.canonical_json(value) and type(value) is dict and
              set(value) == {'format', 'invented_only', 'formal_permission', 'entries'} and
              value['format'] == FORMAT and value['invented_only'] is True and
              value['formal_permission'] is False and
              type(value['entries']) is list and len(value['entries']) == len(INDICES),
              'pinned invented pair input manifest')
    entries = []
    for index, declared in zip(INDICES, value['entries']):
        expected = source_paths(index)
        v.require(type(declared) is dict and
                  set(declared) == {'chunk_index', 'attempt', 'files'} and
                  type(declared['chunk_index']) is int and
                  declared['chunk_index'] == index and
                  type(declared['attempt']) is int and declared['attempt'] == 1 and
                  type(declared['files']) is dict and
                  set(declared['files']) == set(expected),
                  'exact retained pair file inventory')
        entry = {'expected_pins': {}}
        for name, relative in sorted(expected.items()):
            descriptor = declared['files'][name]
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
        v.require(type(reread) is dict and reread.get('chunk_index') == index and
                  reread.get('source_root') == str(
                      artifacts / ('anomaly-v03-preformal-registered-attempt-' + suffix)) and
                  reread.get('output_root') == str(
                      artifacts / ('anomaly-v03-preformal-saved-row-reread-' + suffix)) and
                  reread.get('manifest_path') == str(repo / expected['manifest']) and
                  reread.get('row_projection_path') == str(repo / expected['rows']),
                  'exact retained pair reread and attempt roots')
        entries.append(entry)
    result = coverage.collect_saved_row_coverage(entries)
    v.require(result['format'] == coverage.FORMAT and
              result['status'] == 'partial_coverage_unanchored' and
              result['invented_only'] is True and
              result['chunk_indices'] == list(INDICES) and
              result['bound_chunks'] == len(INDICES) and
              result['bound_evaluations'] == 6 * len(INDICES) and
              result['missing_chunk_indices'] == list(range(2, 480)) and
              result['registered_observations_read'] is False and
              result['actual_registered_observations_read'] is False and
              result['campaign_coherence_authenticated'] is False and
              result['campaign_evaluations_credited'] == 0 and
              result['formal_permission'] is False and
              result['producer_campaign_anchor'] is None and
              result['clusters'] is None and result['diagnostics'] is None and
              result['slice_source'] is None and
              result['analysis_authorized'] is False and
              result['promotion_allowed'] is False and
              result['independent_s6_complete'] is False,
              'bounded unanchored pair coverage')
    result['external_pinset_pin'] = pinset_pin
    output_raw = v.canonical_json(result)
    v.require(len(output_raw) <= MAX_RESULT, 'bounded pair coverage result')
    result_root.mkdir()
    io._exclusive(result_root / 'result.json', output_raw)
    return {'status': result['status'], 'output': str(result_root / 'result.json'),
            'output_pin': _pin(output_raw), 'bound_chunks': result['bound_chunks'],
            'formal_permission': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare_parser = sub.add_parser('prepare')
    prepare_parser.add_argument('--pinset-root', required=True)
    run_parser = sub.add_parser('run')
    run_parser.add_argument('--pinset-root', required=True)
    run_parser.add_argument('--pinset-pin', type=_pin_arg, required=True)
    run_parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    result = prepare(args.pinset_root) if args.command == 'prepare' else run(
        args.pinset_root, args.pinset_pin, args.output_root)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
