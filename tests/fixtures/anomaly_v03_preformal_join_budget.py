"""Bounded, invented-only producer join and analysis-input projection probe.

This test harness exercises the pure fixture adapters.  Its 2,880 rows are
generated declarations, not executed evaluations or registered observations.
It starts no evaluation, analysis, audit, publication, or reader worker. A
short-lived Git helper reads the baseline HEAD. No formal gate is granted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import zipfile

from banto_ai import _anomaly_v03_fixture_budget as budgets
from banto_ai import anomaly_v03_bound_fixture_pipeline as projection
from banto_ai import anomaly_v03_producer_input_fixture as primary
from banto_ai import anomaly_v03_producer_slice_fixture as slices
from tests import test_anomaly_v03_producer_input_fixture as invented_primary
from tests import test_anomaly_v03_producer_slice_fixture as invented_slices


ROOT = Path(__file__).resolve().parents[2]
PARENT = ROOT / 'artifacts'
PREFIX = 'anomaly-v03-preformal-join-budget-'
FORMAT = 'anomaly-v03-preformal-join-budget-v1'
LIMITS = {**budgets.DEFAULTS, 'wall_seconds': 90,
          'parent_private_bytes': 384 * 1024**2,
          'directory_bytes': 24 * 1024**2, 'directory_entries': 32}
SOURCES = (
    'tests/fixtures/anomaly_v03_preformal_join_budget.py',
    'tests/test_anomaly_v03_producer_input_fixture.py',
    'tests/test_anomaly_v03_producer_slice_fixture.py',
    'src/banto_ai/anomaly_v03_producer_input_fixture.py',
    'src/banto_ai/anomaly_v03_producer_slice_fixture.py',
    'src/banto_ai/anomaly_v03_bound_fixture_pipeline.py',
)


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _source_pins():
    return {name: _pin((ROOT / name).read_bytes()) for name in SOURCES}


def _write(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)


def _read_pin(path, expected, maximum):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_nlink != 1:
        raise ValueError('unsafe saved probe file')
    if info.st_size > maximum:
        raise ValueError('saved probe file exceeds limit')
    raw = path.read_bytes()
    if _pin(raw) != expected or path.lstat().st_size != info.st_size:
        raise ValueError('saved probe file pin changed')
    return raw


def _new_root(name):
    if type(name) is not str or not re.fullmatch(r'anomaly-v03-preformal-join-budget-[a-z0-9-]{1,48}', name):
        raise ValueError('new preformal join budget ID required')
    parent = PARENT.absolute()
    info = parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('unsafe probe parent')
    root = parent / name
    if root.exists() or root.is_symlink():
        raise ValueError('probe root already exists')
    return root


def _archive(path, case):
    """Retain all invented input bytes in one bounded compressed file."""
    groups = (
        ('primary/manifest.json', case['primary_input']['manifest_raw']),
        ('slices/manifest.json', case['manifest_raw']),
    )
    seen = set()
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in groups:
            archive.writestr(name, raw)
            seen.add(name)
        for label, snapshots in (('primary', case['primary_input']['snapshots']),
                                 ('slices', case['snapshots'])):
            for source_name in sorted(snapshots):
                primary.v.safe_relative_path(source_name)
                if '\\' in source_name or source_name.startswith('/'):
                    raise ValueError('unsafe fixture archive path')
                name = label + '/files/' + source_name
                if name in seen:
                    raise ValueError('duplicate fixture archive path')
                archive.writestr(name, snapshots[source_name])
                seen.add(name)
    if len(seen) != 2 + 9122 + 2880:
        raise ValueError('invented archive inventory changed')
    info = path.stat()
    if info.st_size > 12 * 1024**2:
        raise ValueError('invented archive exceeds limit')
    return {'files': len(seen), 'compressed_pin': _pin(path.read_bytes())}


def _input_bytes(case):
    first, second = case['primary_input'], case
    return {'primary_snapshot_files': len(first['snapshots']),
            'primary_snapshot_bytes': sum(map(len, first['snapshots'].values())),
            'primary_manifest_pin': _pin(first['manifest_raw']),
            'slice_snapshot_files': len(second['snapshots']),
            'slice_snapshot_bytes': sum(map(len, second['snapshots'].values())),
            'slice_manifest_pin': _pin(second['manifest_raw'])}


def _phase(result, name, monitor, action):
    monitor.checkpoint()
    started = time.monotonic()
    value = action()
    elapsed = time.monotonic() - started
    monitor.checkpoint()
    result['phases'].append({'name': name, 'elapsed_seconds': elapsed})
    return value


def _head():
    value = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                    text=True, timeout=5).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('invalid source revision')
    return value


def _revision_scope(revision, source_pins):
    """Separate a baseline HEAD label from byte-identical committed sources."""
    if set(source_pins) != set(SOURCES):
        return 'baseline-head-with-selected-working-raw-pins'
    for name in SOURCES:
        try:
            committed = subprocess.check_output(
                ['git', '-C', str(ROOT), 'show', revision + ':' + name],
                stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return 'baseline-head-with-selected-working-raw-pins'
        if _pin(committed) != source_pins[name]:
            return 'baseline-head-with-selected-working-raw-pins'
    return 'selected-working-raw-matches-head-blobs'


def run_measurement(name):
    """Save one new receipt for a bounded contiguous pure-fixture measurement."""
    target = _new_root(name)
    target.mkdir()
    started = time.monotonic()
    result = {'format': FORMAT, 'status': 'failed', 'reason': None,
              'scope': 'invented-declarations-and-pure-joins-through-one-draw-projection',
              'root': str(target), 'source_pin_scope': 'selected-fixture-files-only',
              'source_revision_scope': 'head-plus-selected-working-raw-pins-not-git-closure',
              'phases': [], 'new_evaluations': 0, 'registered_data_read': False,
              'real_producer_executed': False, 'registered_saved_reader_used': False,
              'owned_analysis_executed': False, 'owned_audit_executed': False,
              'publication_executed': False, 'bootstrap_replicates': 0,
              'independent_s6_complete': False, 'formal_permission': False,
              'promotion_allowed': False}
    monitor = budgets.FixtureBudget(target, LIMITS)
    saved = {}
    try:
        result['source_pins_before'] = _source_pins()
        result['source_revision'] = _head()
        result['source_revision_scope'] = _revision_scope(
            result['source_revision'], result['source_pins_before'])
        monitor.start()

        case = _phase(result, 'invented_input_generation', monitor,
                      lambda: invented_slices.example(invented_primary.example(40)))
        counts = _input_bytes(case)
        if counts['primary_snapshot_files'] != 9122 or counts['slice_snapshot_files'] != 2880:
            raise ValueError('invented fixture file counts changed')
        result['invented_inputs'] = counts
        archive = _phase(result, 'invented_input_retention', monitor,
                         lambda: _archive(target / 'invented-inputs.zip', case))
        result['input_archive'] = archive
        saved['invented-inputs.zip'] = archive['compressed_pin']

        bound = _phase(result, 'pure_primary_and_slice_join', monitor,
                       lambda: slices.bind_producer_slices(**case))
        if (bound['status'] != 'fixture_slices_bound' or
                bound['verified_slice_files'] != 2880 or
                bound['primary']['planned_evaluations'] != 2880 or
                not bound['complete_for_aggregation'] or
                bound['registered_data_read'] or bound['formal_permission']):
            raise ValueError('invented join scope changed')
        bound_raw = primary.v.canonical_json(bound)
        if len(bound_raw) > 8 * 1024**2:
            raise ValueError('invented bound output exceeds limit')
        _write(target / 'bound.json', bound_raw)
        saved['bound.json'] = _pin(bound_raw)
        result['joined_slices'] = bound['verified_slice_files']
        result['bound_pin'] = saved['bound.json']

        prepared = _phase(result, 'one_draw_analysis_input_projection', monitor,
                          lambda: projection.prepare_inputs(
                              bound_raw, expected_mode='fixture', expected_pin=saved['bound.json'],
                              expected_revision=result['source_revision'], draws=[list(range(40))]))
        projected = target / 'projection'
        projected.mkdir()
        (projected / 'fixture').mkdir()
        for name, raw in prepared['files'].items():
            if name not in projection.analysis.INPUT_LIMITS:
                raise ValueError('unexpected projected file')
            _write(projected / name, raw)
            saved['projection/' + name] = _pin(raw)
        if set(prepared['files']) != set(projection.analysis.INPUT_LIMITS):
            raise ValueError('projected file set changed')
        result['projected_input_files'] = len(prepared['files'])
        result['projected_input_bytes'] = sum(map(len, prepared['files'].values()))
        result['projected_input_pins'] = prepared['binding']['worker_input_pins']

        for name, pin in saved.items():
            _read_pin(target / name, pin, 12 * 1024**2)
        result['saved_file_pins'] = saved
        result['source_pins_after'] = _source_pins()
        if result['source_pins_before'] != result['source_pins_after']:
            raise ValueError('fixture source changed during probe')
        monitor.checkpoint()
        result['status'] = 'measured'
    except BaseException as error:
        result['reason'] = type(error).__name__ + ': ' + str(error)
    finally:
        report = monitor.close()
        result['wall_seconds'] = time.monotonic() - started
        result['resource_budget_passed'] = report['passed']
        if not report['passed']:
            result['status'] = 'failed'
            result['reason'] = result['reason'] or report['stop_reason'] or 'monitor_unclosed'
        report_raw = primary.v.canonical_json(report)
        if len(report_raw) > 32 * 1024:
            raise ValueError('probe monitor receipt exceeds reserve')
        _write(target / 'resource-budget.json', report_raw)
        result['resource_budget_pin'] = _pin(report_raw)
        raw = primary.v.canonical_json(result)
        if len(raw) > 32 * 1024:
            raise ValueError('probe result receipt exceeds reserve')
        _write(target / 'receipt.json', raw)
        if not report['monitor_exit_confirmed']:
            raise budgets.UnclosedMonitor(monitor, report)
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != '--measure':
        raise SystemExit('usage: --measure NEW_PREformal_JOIN_BUDGET_ID')
    result = run_measurement(argv[1])
    print(json.dumps({'status': result['status'], 'reason': result['reason'],
                      'receipt': str(Path(result['root']) / 'receipt.json')}))
    return 0 if result['status'] == 'measured' else 2


if __name__ == '__main__':
    raise SystemExit(main())
