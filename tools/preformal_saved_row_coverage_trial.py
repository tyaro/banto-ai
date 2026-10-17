"""Prepare external pins and collect invented saved-row coverage.

The fixed one-chunk source is the retained g02/r01 fixture. ``prepare`` writes
input pins outside the new result root. ``run`` consumes those caller-pinned
bytes and cannot create 40-cluster aggregates or formal evaluation credit.
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


FORMAT = 'anomaly-v03-preformal-saved-row-coverage-input-pins-v1'
PINSET = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-coverage-pins-01/pins.json'
OUTPUT = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-coverage-02/result.json'
SOURCES = {
    'result': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/result.json',
    'rows': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/rows.json',
    'budget': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/resource-budget.json',
    'supervision': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/owned-reader/supervision.json',
    'stdout': 'artifacts/anomaly-v03-preformal-saved-row-reread-r01/owned-reader/worker/report.json',
    'manifest': 'artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json',
    'receipt': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/receipt.json',
    'report': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/report.json',
    'savepoint': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/savepoint.json',
    'outer': 'artifacts/anomaly-v03-preformal-registered-attempt-g02/owned-generator/result.json',
}
MAX_SOURCE = 1024 * 1024
MAX_PINSET = 16 * 1024
MAX_RESULT = 64 * 1024


def _pin(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _pin_arg(value: str) -> dict:
    match = re.fullmatch(r'([1-9][0-9]*):([0-9a-f]{64})', value)
    if match is None:
        raise argparse.ArgumentTypeError('expected bytes:sha256')
    return {'bytes': int(match.group(1)), 'sha256': match.group(2)}


def prepare() -> dict:
    paths.regular_path(PINSET, missing=True)
    v.require(not PINSET.parent.exists(), 'new separate pinset root required')
    files = {}
    for name, relative in sorted(SOURCES.items()):
        v.safe_relative_path(relative)
        path = paths.regular_path(ROOT / relative)
        v.require(path.stat().st_size <= MAX_SOURCE, 'bounded coverage source ' + name)
        files[name] = {'path': relative, 'pin': _pin(path.read_bytes())}
    value = {'format': FORMAT, 'invented_only': True, 'formal_permission': False,
             'entries': [{'chunk_index': 0, 'files': files}]}
    raw = v.canonical_json(value)
    v.require(len(raw) <= MAX_PINSET, 'bounded external coverage pinset')
    PINSET.parent.mkdir()
    io._exclusive(PINSET, raw)
    io._exclusive(PINSET.with_name('pins.json.sha256'),
                  (_pin(raw)['sha256'] + '\n').encode('ascii'))
    return {'status': 'prepared', 'pinset': str(PINSET), 'pinset_pin': _pin(raw),
            'invented_only': True, 'formal_permission': False}


def run(expected_pin: dict) -> dict:
    from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage

    raw = pinned.read_pinned(PINSET, expected_pin, MAX_PINSET)
    value = v.strict_json(raw)
    v.require(raw == v.canonical_json(value) and type(value) is dict and
              set(value) == {'format', 'invented_only', 'formal_permission', 'entries'} and
              value['format'] == FORMAT and value['invented_only'] is True and
              value['formal_permission'] is False,
              'pinned invented coverage input manifest')
    v.require(type(value['entries']) is list and len(value['entries']) == 1,
              'one current invented coverage entry')
    entries = []
    for declared in value['entries']:
        v.require(type(declared) is dict and set(declared) == {'chunk_index', 'files'} and
                  declared['chunk_index'] == 0 and type(declared['files']) is dict and
                  set(declared['files']) == set(SOURCES),
                  'exact invented coverage file inventory')
        item = {'expected_pins': {}}
        for name, relative in sorted(SOURCES.items()):
            descriptor = declared['files'][name]
            v.require(type(descriptor) is dict and
                      set(descriptor) == {'path', 'pin'} and
                      descriptor['path'] == relative,
                      'frozen invented coverage path ' + name)
            pin = descriptor['pin']
            item[name + '_raw'] = pinned.read_pinned(ROOT / relative, pin, MAX_SOURCE)
            item['expected_pins'][name] = pin
        entries.append(item)
    result = coverage.collect_saved_row_coverage(entries)
    result['external_pinset_pin'] = expected_pin
    output_raw = v.canonical_json(result)
    v.require(len(output_raw) <= MAX_RESULT, 'bounded partial coverage result')
    paths.regular_path(OUTPUT, missing=True)
    v.require(not OUTPUT.parent.exists(), 'new dedicated coverage result root required')
    OUTPUT.parent.mkdir()
    io._exclusive(OUTPUT, output_raw)
    return {'status': result['status'], 'output': str(OUTPUT),
            'output_pin': _pin(output_raw), 'bound_chunks': result['bound_chunks'],
            'formal_permission': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare')
    run_parser = sub.add_parser('run')
    run_parser.add_argument('--pinset-pin', type=_pin_arg, required=True)
    args = parser.parse_args()
    result = prepare() if args.command == 'prepare' else run(args.pinset_pin)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
