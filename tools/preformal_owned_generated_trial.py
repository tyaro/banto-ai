"""Prepare and run one invented, owned, registered-format generation trial.

The ``prepare`` phase derives pins in the caller process and retains them in
an external manifest before the owned generator is launched.  The ``run``
phase consumes only that caller-pinned manifest.  Neither phase uses a
registered holdout seed or actual registered observation bytes, and neither
grants formal credit.

Example (after committing a clean source revision)::

    python -B tools/preformal_owned_generated_trial.py prepare \
      --root artifacts/anomaly-v03-preformal-registered-attempt-g01 \
      --manifest artifacts/anomaly-v03-preformal-generated-pinsets-g01/pins.json
    python -B tools/preformal_owned_generated_trial.py run \
      --root artifacts/anomaly-v03-preformal-registered-attempt-g01 \
      --manifest artifacts/anomaly-v03-preformal-generated-pinsets-g01/pins.json \
      --manifest-sha256 <sha256 printed by prepare>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from banto_ai import _anomaly_v03_io as io  # noqa: E402
from banto_ai import _anomaly_v03_runtime as paths  # noqa: E402
from banto_ai import anomaly_v03 as v  # noqa: E402
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated  # noqa: E402
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied  # noqa: E402
from banto_ai import anomaly_v03_reader_evidence as observed  # noqa: E402
from banto_ai import _anomaly_v03_engineering_runtime as resources  # noqa: E402


FORMAT = 'anomaly-v03-preformal-owned-generated-external-pins-v1'
MAX_MANIFEST = 256 * 1024
MAX_RESULT = 256 * 1024
BUDGET_RESULT_FORMAT = 'anomaly-v03-preformal-owned-generated-two-role-budget-v1'
BUDGET_CONTROL_RESERVE = 8 * 1024**2
BUDGET_RECEIPT_MAX = 64 * 1024
MANIFEST_FIELDS = {
    'format', 'scope', 'root', 'revision', 'chunk_index', 'recipe_id',
    'source', 'source_snapshots', 'source_snapshot_pins', 'output_pins',
    'output_file_count', 'output_bytes', 'invented_only',
    'actual_registered_observations_read', 'formal_permission',
}


def _argument_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _manifest_path(value: str, root: Path, *, missing: bool) -> Path:
    path = paths.regular_path(_argument_path(value), missing=missing)
    parent = paths.regular_path(path.parent, directory=True, missing=missing)
    suffix = root.name.removeprefix(generated.fixture.PREFIX)
    v.require(root.name.startswith(generated.fixture.PREFIX) and suffix and
              parent.parent == ROOT / 'artifacts' and
              parent.name == 'anomaly-v03-preformal-generated-pinsets-' + suffix
              and parent != root,
              'matching separate dedicated external pinset directory required')
    v.require(path.name.endswith('.json'), 'JSON external manifest required')
    return path


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + '.sha256')


def _revision() -> str:
    revision = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL, timeout=10).decode('ascii').strip()
    v.require(bool(re.fullmatch(r'[0-9a-f]{40}', revision)), 'full clean HEAD required')
    return revision


def _snapshots(revision: str) -> dict[str, dict[str, bytes]]:
    rows = {}
    for name in generated.SNAPSHOT_FILES:
        working = observed._file(ROOT / name, 1024**2)
        committed = subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10)
        v.require(working == committed, 'snapshot working/Git mismatch: ' + name)
        rows[name] = working
    snapshots = {revision: rows}
    generated._validated_snapshots(snapshots, revision)
    return snapshots


def _snapshot_pins(snapshots: dict[str, dict[str, bytes]], revision: str) -> dict:
    return {name: copied._pin(raw)
            for name, raw in sorted(snapshots[revision].items())}


def prepare(root_text: str, manifest_text: str, chunk_index: int) -> int:
    root = generated._root(_argument_path(root_text), missing=True)
    v.require(not root.exists(), 'prepare requires a new generated-attempt root')
    names = generated._outputs(root, chunk_index)
    manifest_path = _manifest_path(manifest_text, root, missing=True)
    sidecar = _sidecar(manifest_path)
    paths.regular_path(sidecar, missing=True)
    v.require(not manifest_path.exists() and not sidecar.exists(),
              'external manifest and SHA sidecar must be new')

    revision = _revision()
    source = generated._source(revision)
    snapshots = _snapshots(revision)
    output = generated.build_invented_output_bytes(
        root, chunk_index=chunk_index, recipe_id=generated.RECIPE,
        source_snapshots=snapshots)
    v.require(set(output) == set(names), 'exact invented output inventory')
    pins = {name: copied._pin(raw) for name, raw in sorted(output.items())}
    generated._validate_pins(names, pins)
    manifest = {
        'format': FORMAT,
        'scope': 'invented-registered-format-owned-generator-only',
        'root': str(root), 'revision': revision,
        'chunk_index': chunk_index, 'recipe_id': generated.RECIPE,
        'source': source,
        'source_snapshots': copied._source_snapshots(snapshots),
        'source_snapshot_pins': _snapshot_pins(snapshots, revision),
        'output_pins': pins, 'output_file_count': len(pins),
        'output_bytes': sum(pin['bytes'] for pin in pins.values()),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }
    raw = v.canonical_json(manifest)
    v.require(len(raw) <= MAX_MANIFEST, 'external manifest byte bound')
    digest = hashlib.sha256(raw).hexdigest()
    manifest_path.parent.mkdir(exist_ok=True)
    io._exclusive(manifest_path, raw)
    io._exclusive(sidecar, (digest + '\n').encode('ascii'))
    print(json.dumps({
        'status': 'prepared', 'manifest': str(manifest_path),
        'manifest_sha256': digest, 'sha256_sidecar': str(sidecar),
        'root': str(root), 'revision': revision,
        'output_file_count': len(pins), 'output_bytes': manifest['output_bytes'],
        'invented_only': True, 'formal_permission': False,
    }, sort_keys=True))
    return 0


def _verified_run_inputs(root_text: str, manifest_text: str, digest: str):
    v.require(bool(re.fullmatch(r'[0-9a-f]{64}', digest)),
              'caller-supplied manifest SHA-256 required')
    root = generated._root(_argument_path(root_text), missing=True)
    manifest_path = _manifest_path(manifest_text, root, missing=False)
    raw = observed._file(manifest_path, MAX_MANIFEST)
    v.require(hashlib.sha256(raw).hexdigest() == digest,
              'caller-supplied external manifest SHA mismatch')
    sidecar = _sidecar(manifest_path)
    v.require(observed._file(sidecar, 128) == (digest + '\n').encode('ascii'),
              'external manifest SHA sidecar mismatch')
    manifest = v.strict_json(raw)
    v.require(raw == v.canonical_json(manifest) and
              type(manifest) is dict and set(manifest) == MANIFEST_FIELDS,
              'canonical exact external manifest required')
    v.require(manifest['format'] == FORMAT and
              manifest['scope'] == 'invented-registered-format-owned-generator-only'
              and manifest['root'] == str(root) and
              manifest['recipe_id'] == generated.RECIPE and
              manifest['invented_only'] is True and
              manifest['actual_registered_observations_read'] is False and
              manifest['formal_permission'] is False,
              'invented external manifest identity/scope mismatch')
    revision = _revision()
    v.require(manifest['revision'] == revision,
              'external manifest full HEAD mismatch')
    source = generated._source(revision)
    v.require(manifest['source'] == source,
              'external manifest selected source mismatch')
    snapshots = copied._decode_source_snapshots(manifest['source_snapshots'])
    generated._validated_snapshots(snapshots, revision)
    v.require(manifest['source_snapshot_pins'] ==
              _snapshot_pins(snapshots, revision),
              'external generator/materializer raw snapshot pins changed')
    names = generated._outputs(root, manifest['chunk_index'])
    pins = manifest['output_pins']
    generated._validate_pins(names, pins)
    v.require(manifest['output_file_count'] == len(names) == 22 and
              manifest['output_bytes'] ==
              sum(pin['bytes'] for pin in pins.values()),
              'external output inventory size mismatch')

    return root, manifest_path, manifest, revision, pins, snapshots


def _claim_empty_root(root: Path) -> None:
    if root.exists():
        paths.regular_path(root, directory=True)
        v.require(not any(root.iterdir()), 'generated-attempt root must be empty')
    else:
        root.mkdir()


def _checked_inner_result(root: Path, result: dict) -> None:
    saved_result = observed._file(root / 'owned-generator' / 'result.json',
                                  MAX_RESULT)
    v.require(copied._pin(saved_result) == result['result_pin'] and
              v.strict_json(saved_result) == {
                  key: value for key, value in result.items()
                  if key not in ('result_pin', 'check_directory')},
              'owned generator result retention/readback')


def run(root_text: str, manifest_text: str, digest: str) -> int:
    root, _, manifest, revision, pins, snapshots = _verified_run_inputs(
        root_text, manifest_text, digest)

    _claim_empty_root(root)
    result = generated.generate_and_read(
        root, expected_pins=pins, source_snapshots=snapshots,
        expected_revision=revision, chunk_index=manifest['chunk_index'],
        recipe_id=generated.RECIPE)
    _checked_inner_result(root, result)
    print(v.canonical_json(result).decode('utf-8'))
    return 0 if result['status'] == 'verified' else 2


def run_budget(root_text: str, manifest_text: str, digest: str) -> int:
    """Measure only pinned invented generation and its separate saved reader.

    The external ``prepare`` computation and all downstream inference,
    documentation, audit, and publication are outside this two-role interval.
    """
    from banto_ai import anomaly_v03_preformal_generated_chain_budget as chain_budget

    root, manifest_path, manifest, revision, pins, snapshots = \
        _verified_run_inputs(root_text, manifest_text, digest)
    _claim_empty_root(root)
    result = {
        'format': BUDGET_RESULT_FORMAT,
        'scope': 'invented-generated-two-role-only',
        'status': 'failed', 'reason': 'not_started',
        'root': str(root), 'source_revision': revision,
        'external_manifest': str(manifest_path),
        'external_manifest_pin': {'bytes': manifest_path.stat().st_size,
                                  'sha256': digest},
        'expected_output_file_count': manifest['output_file_count'],
        'expected_output_bytes': manifest['output_bytes'],
        'prelaunch_pin_preparation_included': False,
        'shared_budget_measured': False,
        'shared_budget_passed': False,
        'both_owned_exits_reported': False,
        'saved_role_evidence_bound': False,
        'inner_verified': False,
        'invented_only': True,
        'registered_seed_consumed': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'full_end_to_end_budget_measured': False,
        'formal_50000_draw_budget_measured': False,
        'formal_permission': False,
        'analysis_authorized': False,
        'promotion_allowed': False,
        'independent_s6_complete': False,
    }
    budget = chain_budget.GeneratedChainBudget(root)
    critical = None
    started = False
    work_verified = False
    try:
        budget.start()
        started = True
        budget.checkpoint('preflight')
        planned_bytes = manifest['output_bytes'] + BUDGET_CONTROL_RESERVE
        v.require(planned_bytes + chain_budget.RECEIPT_RESERVE_BYTES <=
                  budget.limits['directory_bytes'],
                  'generated output pins and control reserve exceed outer byte cap')
        v.require(shutil.disk_usage(root).free >=
                  budget.limits['minimum_free_disk_bytes'] + 2 * planned_bytes,
                  'two-times invented output disk headroom required')
        inner = generated.generate_and_read(
            root, expected_pins=pins, source_snapshots=snapshots,
            expected_revision=revision, chunk_index=manifest['chunk_index'],
            recipe_id=generated.RECIPE, outer_budget=budget)
        _checked_inner_result(root, inner)
        result.update(inner_status=inner['status'],
                      inner_reason=inner.get('reason'),
                      inner_result_pin=inner['result_pin'],
                      generator_pid=inner.get('owned_fixture_generator_pid'),
                      generator_exit_confirmed=inner.get(
                          'owned_fixture_generator_exit_confirmed'),
                      generator_start_token=inner.get(
                          'owned_fixture_generator_start_token'),
                      reader_pid=inner.get('owned_fixture_reader_pid'),
                      reader_exit_confirmed=inner.get(
                          'owned_fixture_reader_exit_confirmed'),
                      reader_start_token=inner.get(
                          'owned_fixture_reader_start_token'))
        if inner['status'] == 'verified':
            v.require(type(result['generator_pid']) is int and
                      type(result['reader_pid']) is int and
                      result['generator_pid'] > 0 and
                      result['reader_pid'] > 0 and
                      result['generator_pid'] != result['reader_pid'] and
                      type(result['generator_start_token']) is str and
                      type(result['reader_start_token']) is str and
                      bool(result['generator_start_token']) and
                      bool(result['reader_start_token']) and
                      result['generator_start_token'] !=
                      result['reader_start_token'] and
                      result['generator_exit_confirmed'] is True and
                      result['reader_exit_confirmed'] is True,
                      'distinct owned generator and reader exits required')
        v.require(hashlib.sha256(observed._file(
            manifest_path, MAX_MANIFEST)).hexdigest() == digest and
                  observed._file(_sidecar(manifest_path), 128) ==
                  (digest + '\n').encode('ascii'),
                  'external prelaunch manifest changed during measured roles')
        v.require(generated._source(revision) == manifest['source'],
                  'selected generated source changed after measured roles')
        budget.checkpoint('postflight')
        work_verified = inner['status'] == 'verified'
        result['inner_verified'] = work_verified
        result['reason'] = None if work_verified else (
            inner.get('reason') or 'owned_generated_chain_failed')
    except resources.ResourceStop as error:
        result.update(reason=error.reason, error_type=type(error).__name__)
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        result.update(reason='budgeted_generated_chain_rejected',
                      error_type=type(error).__name__, detail=str(error))
    except BaseException as error:
        result.update(reason='critical_budgeted_generated_chain_failure',
                      error_type=type(error).__name__)
        critical = error
    finally:
        if started:
            try:
                report = budget.close()
                raw_budget = v.canonical_json(report)
                v.require(len(raw_budget) <= BUDGET_RECEIPT_MAX,
                          'outer budget receipt byte bound')
                io._exclusive(root / 'resource-budget.json', raw_budget)
                result['resource_budget_pin'] = copied._pin(raw_budget)
                v.require(copied._pin(observed._file(
                    root / 'resource-budget.json', BUDGET_RECEIPT_MAX)) ==
                    result['resource_budget_pin'],
                    'retained outer budget receipt changed')
                result['shared_budget_measured'] = True
                result['shared_budget_passed'] = (
                    report['format'] == chain_budget.FORMAT and
                    report['scope'] ==
                    'invented-generated-attempt-to-separate-reader-only' and
                    report['root'] == str(root) and
                    type(report['samples']) is int and report['samples'] > 0 and
                    report['sampler_exit_confirmed'] is True and
                    report['stop_reason'] is None and
                    report['passed'] is True and
                    report['formal_permission'] is False and
                    report['actual_registered_observations_read'] is False and
                    report['campaign_evaluations_credited'] == 0)
                roles = report['caller_reported_roles']
                result['both_owned_exits_reported'] = (
                    report['both_owned_exits_reported'] is True and
                    type(roles) is dict and set(roles) ==
                    {'generator', 'reader'} and all(
                        roles[role]['status'] == 'complete' and
                        roles[role]['worker_exit_confirmed'] is True and
                        roles[role]['worker_pid'] == result.get(role + '_pid')
                        for role in ('generator', 'reader')))
                if work_verified and result['both_owned_exits_reported']:
                    try:
                        for role in ('generator', 'reader'):
                            control = root / ('owned-' + role)
                            saved_monitor = observed._file(
                                control / 'supervision.json', BUDGET_RECEIPT_MAX)
                            monitor = v.strict_json(saved_monitor)
                            saved_stdout = observed._file(
                                control / 'worker' / 'report.json',
                                generated.LIMITS['output_bytes'] if role ==
                                'generator' else copied.READER_LIMITS['output_bytes'])
                            v.require(copied._pin(saved_monitor) ==
                                      roles[role]['result_pin'] and
                                      monitor['status'] == 'complete' and
                                      monitor['exit_code'] == 0 and
                                      monitor['worker_exit_confirmed'] is True and
                                      monitor['worker_pid'] ==
                                      result[role + '_pid'] and
                                      copied._pin(saved_stdout) ==
                                      monitor['output'] ==
                                      inner[role + '_stdout_pin'],
                                      'retained ' + role + ' role evidence changed')
                        result['saved_role_evidence_bound'] = True
                    except (ValueError, OSError, KeyError, TypeError) as error:
                        result['role_evidence_error_type'] = type(error).__name__
                if work_verified and result['shared_budget_passed'] and \
                        result['both_owned_exits_reported'] and \
                        result['saved_role_evidence_bound']:
                    result.update(status='verified', reason=None)
                elif result['reason'] is None or result['reason'] == 'not_started':
                    result['reason'] = report['stop_reason'] or (
                        'owned_exits_not_both_reported' if not
                        result['both_owned_exits_reported'] else
                        'saved_role_evidence_changed' if not
                        result['saved_role_evidence_bound'] else
                        'owned_generated_chain_failed')
            except BaseException as error:
                result.update(status='failed', reason='outer_budget_close_or_save_failed',
                              budget_error_type=type(error).__name__)
                if critical is None:
                    critical = error
                else:
                    critical.outer_budget_error = error
        try:
            raw_result = v.canonical_json(result)
            v.require(len(raw_result) <= BUDGET_RECEIPT_MAX,
                      'budgeted result byte bound')
            io._exclusive(root / 'budgeted-result.json', raw_result)
            v.require(observed._file(root / 'budgeted-result.json',
                                     BUDGET_RECEIPT_MAX) == raw_result,
                      'retained budgeted result changed')
        except BaseException as error:
            if critical is None:
                critical = error
            else:
                critical.outer_result_error = error
    if critical is not None:
        raise critical
    print(v.canonical_json({**result, 'result_pin': copied._pin(raw_result)}).decode('utf-8'))
    return 0 if result['status'] == 'verified' else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    phases = parser.add_subparsers(dest='phase', required=True)
    before = phases.add_parser('prepare', help='save external invented output pins')
    before.add_argument('--root', required=True)
    before.add_argument('--manifest', required=True)
    before.add_argument('--chunk-index', type=int, default=0)
    after = phases.add_parser('run', help='consume a caller-pinned external manifest')
    after.add_argument('--root', required=True)
    after.add_argument('--manifest', required=True)
    after.add_argument('--manifest-sha256', required=True)
    measured = phases.add_parser(
        'run-budget', help='measure the pinned generator and separate reader')
    measured.add_argument('--root', required=True)
    measured.add_argument('--manifest', required=True)
    measured.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        if args.phase == 'prepare':
            return prepare(args.root, args.manifest, args.chunk_index)
        if args.phase == 'run-budget':
            return run_budget(args.root, args.manifest, args.manifest_sha256)
        return run(args.root, args.manifest, args.manifest_sha256)
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'rejected', 'phase': args.phase,
                          'error_type': type(error).__name__,
                          'detail': str(error), 'formal_permission': False},
                         sort_keys=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
