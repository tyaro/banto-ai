"""Pinned invented producer counts -> complete 50,000-draw arithmetic probe.

This separate preformal bridge measures only the primary tables and an
independent arithmetic check. It consumes an owned producer's retained bound
and four projection files; it does not create a formal document, publish, read
registered observations, or complete S6. Every attempt has a new root.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import _anomaly_v03_contract as frozen
from . import _anomaly_v03_fixture_budget as primitives
from . import _anomaly_v03_engineering_runtime as resources
from . import anomaly_v03_bound_fixture_pipeline as projection
from . import anomaly_v03_inference_audit as primary
from . import anomaly_v03_owned_producer_fixture as producer
from . import anomaly_v03_platform_fixture_runtime as platform_runtime
from . import anomaly_v03_preformal_chain_budget as chain_budget
from . import anomaly_v03_preformal_draw_audit as independent
from . import anomaly_v03_preformal_draw_budget as draw_budget


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-bound-draw-bridge'
PRODUCER_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-five-role-26h2'
FORMAT = 'anomaly-v03-preformal-bound-draw-bridge-v1'
INPUT_FORMAT = FORMAT + '-input'
REPLICATES = 50000
CLUSTERS = 40
CHILD_WALL_SECONDS = 900
CHILD_PRIVATE_BYTES = 1024**3
LOG_BYTES = 256 * 1024
OUTPUT_BYTES = 256 * 1024
ROOT_LIMITS = {
    'wall_seconds': 900,
    'parent_private_bytes': 512 * 1024**2,
    'directory_bytes': 64 * 1024**2,
    'directory_entries': 64,
    'directory_depth': 4,
    'minimum_commit_headroom_bytes': 4 * 1024**3,
    'minimum_free_ram_bytes': 4 * 1024**3,
    'minimum_free_disk_bytes': 10 * 1024**3,
}
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py',
    'src/banto_ai/anomaly_v03_preformal_draw_audit.py',
    'src/banto_ai/anomaly_v03_preformal_draw_budget.py',
    'src/banto_ai/anomaly_v03_preformal_chain_budget.py',
    'src/banto_ai/anomaly_v03_inference_audit.py',
    'src/banto_ai/anomaly_v03_bound_fixture_pipeline.py',
    'src/banto_ai/anomaly_v03_owned_producer_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/_anomaly_v03_fixture_budget.py',
    'src/banto_ai/_anomaly_v03_contract.py',
)
CLOSED = {
    'registered_data_read': False, 'formal_bootstrap_performed': False,
    'formal_document_emitted': False, 'formal_document_validated': False,
    'independent_s6_complete': False, 'formal_permission': False,
    'promotion_allowed': False, 'execution_authenticated': False,
    'source_closure_complete': False, 'runtime_closure_complete': False,
    'performance_status': 'not_evaluated', 'campaign_evaluations_credited': 0,
}


def _raw(value):
    return draw_budget._raw(value)


def _pin(raw):
    return draw_budget._pin(raw)


def _read(path, expected, maximum):
    return draw_budget._read(path, expected, maximum)


def _write(path, raw):
    draw_budget._write(path, raw)
    if _read(path, _pin(raw), max(len(raw), 1)) != raw:
        raise ValueError('bridge write readback differs')
    return _pin(raw)


def _producer_root(path):
    root = Path(path).absolute()
    if (not root.is_relative_to(PRODUCER_PARENT) or root.name != 'producer' or
            root.parent.parent != PRODUCER_PARENT or
            not root.parent.name.startswith('trial-')):
        raise ValueError('retained owned producer root required')
    projection.io.regular_path(root, directory=True)
    projection.io.regular_path(root / 'output', directory=True)
    projection.io.regular_path(root / 'output' / 'projection', directory=True)
    projection.io.regular_path(root / 'output' / 'projection' / 'fixture', directory=True)
    return root


def bind_producer_counts(producer_root, expected_result_pin):
    """Reproject the actual pinned bound and compare all four saved outputs."""
    projection.evidence._pin(expected_result_pin)
    root = _producer_root(producer_root)
    result = projection.v.strict_json(_read(root / 'result.json', expected_result_pin,
                                            64 * 1024))
    for key, wanted in {
        'format': producer.FORMAT, 'mode': 'fixture', 'status': 'verified',
        'owned_producer_join_executed': True, 'worker_exit_confirmed': True,
        'real_producer_executed': False, 'registered_data_read': False,
        'new_evaluations': 0, 'formal_permission': False,
        'promotion_allowed': False,
    }.items():
        if type(result.get(key)) is not type(wanted) or result[key] != wanted:
            raise ValueError('owned producer result differs: ' + key)
    projection.evidence._digest(result['source_revision'], 40)
    bound_path = root / 'output' / 'bound.json'
    if (Path(result['bound_path']) != bound_path or
            Path(result['projection_root']) != root / 'output' / 'projection' or
            set(result['projection_pins']) != set(projection.analysis.INPUT_LIMITS)):
        raise ValueError('owned producer output inventory differs')
    bound = _read(bound_path, result['bound_pin'], 8 * 1024**2)
    prepared = projection.prepare_inputs(
        bound, expected_mode='fixture', expected_pin=result['bound_pin'],
        expected_revision=result['source_revision'], draws=[list(range(CLUSTERS))])
    files = prepared['files']
    for name in projection.analysis.INPUT_LIMITS:
        expected = result['projection_pins'][name]
        saved = _read(root / 'output' / 'projection' / name, expected,
                      projection.analysis.INPUT_LIMITS[name])
        if saved != files[name]:
            raise ValueError('owned producer projection differs: ' + name)
    fixture = projection.v.strict_json(files['fixture/input.json'])
    if fixture['draws'] != [list(range(CLUSTERS))]:
        raise ValueError('owned producer projection draw differs')
    clusters = fixture['clusters']
    primary._fixture_clusters(clusters)
    if len(clusters) != CLUSTERS:
        raise ValueError('independent audit requires forty producer clusters')
    return {
        'clusters': clusters, 'producer_result_pin': copy.deepcopy(expected_result_pin),
        'bound_pin': copy.deepcopy(result['bound_pin']),
        'projection_pins': copy.deepcopy(result['projection_pins']),
        'producer_source_revision': result['source_revision'],
        'source_root': str(root),
        'source_scope': 'caller-pinned retained owned invented producer; no producer replay',
        'external_source_logical_bytes': expected_result_pin['bytes'] +
            result['bound_pin']['bytes'] + sum(pin['bytes'] for pin in
                                              result['projection_pins'].values()),
    }


def _input(binding):
    return {'format': INPUT_FORMAT, 'invented_only': True,
            'registered_data_read': False, 'producer_result_pin':
            binding['producer_result_pin'], 'bound_pin': binding['bound_pin'],
            'projection_input_pin': binding['projection_pins']['fixture/input.json'],
            'clusters': binding['clusters']}


def _check_input(value):
    if (type(value) is not dict or set(value) != {'format', 'invented_only',
            'registered_data_read', 'producer_result_pin', 'bound_pin',
            'projection_input_pin', 'clusters'} or value['format'] != INPUT_FORMAT or
            value['invented_only'] is not True or value['registered_data_read'] is not False):
        raise ValueError('bridge invented input fields')
    for key in ('producer_result_pin', 'bound_pin', 'projection_input_pin'):
        projection.evidence._pin(value[key])
    primary._fixture_clusters(value['clusters'])
    if len(value['clusters']) != CLUSTERS:
        raise ValueError('bridge input is not forty clusters')


class BoundDrawBudget(chain_budget.PreformalChainBudget):
    """A distinct two-role, 900-second sampled cap; never a formal quota."""

    def __init__(self, root):
        super().__init__(root)
        self.limits = dict(ROOT_LIMITS)

    def close(self):
        report = super().close()
        report['format'] = FORMAT + '-resource-budget'
        report['scope'] = 'pinned-owned-producer-to-two-arithmetic-children-only'
        report['both_arithmetic_child_exits_reported'] = (
            set(self.roles) == {'analysis', 'audit'} and
            all(row['worker_exit_confirmed'] for row in self.roles.values()))
        report.pop('caller_reported_all_five_exits')
        return report


def _git_pins(revision):
    projection.evidence._digest(revision, 40)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)
    if git('rev-parse', 'HEAD').decode().strip() != revision or git('status',
                                                                    '--porcelain').strip():
        raise ValueError('bridge code must be clean at expected revision')
    pins = {}
    for name in SOURCE_NAMES:
        raw = draw_budget._bounded_file(ROOT / name, 1024**2)
        if raw != git('show', revision + ':' + name):
            raise ValueError('bridge selected source differs from Git: ' + name)
        pins[name] = _pin(raw)
    return pins


def _child(role, root, input_pin, calculation_pin=None):
    if role not in ('analysis', 'audit'):
        raise ValueError('bridge child role')
    value = json.loads(_read(root / 'input.json', input_pin, 512 * 1024))
    _check_input(value)
    clusters = value['clusters']
    if role == 'analysis':
        indices = frozen.bootstrap_indices()
        if (len(indices) != CLUSTERS * REPLICATES or
                hashlib.sha256(indices).hexdigest() != frozen.BOOTSTRAP_HASH):
            raise ValueError('frozen 50,000 draw bytes differ')
        draws = [indices[i:i + CLUSTERS] for i in range(0, len(indices), CLUSTERS)]
        output = primary.compute_fixture_tables(clusters, draws, engineering_ready=False)
        raw = _raw(output)
        if len(raw) > OUTPUT_BYTES:
            raise ValueError('bridge primary output limit')
        pin = _write(root / 'calculation.json', raw)
    else:
        if calculation_pin is None:
            raise ValueError('bridge retained calculation pin required')
        calculation = json.loads(_read(root / 'calculation.json', calculation_pin,
                                       OUTPUT_BYTES))
        draws, digest = independent.independent_draws()
        if digest != frozen.BOOTSTRAP_HASH:
            raise ValueError('independent draw bytes differ')
        output = independent.audit(clusters, calculation, draws)
        raw = _raw(output)
        if len(raw) > OUTPUT_BYTES:
            raise ValueError('bridge independent audit output limit')
        pin = _write(root / 'audit.json', raw)
    report = {'format': FORMAT + '-role', 'role': role, 'status': 'complete',
              'replicates': REPLICATES, 'draw_sha256': frozen.BOOTSTRAP_HASH,
              'output_pin': pin, 'registered_data_read': False,
              'formal_bootstrap_performed': False, 'formal_permission': False,
              'independent_s6_complete': False}
    print(_raw(report).decode('utf-8'), flush=True)


def _supervise(role, root, input_pin, calculation_pin, budget):
    argv = [sys.executable, '-B', '-m',
            'banto_ai.anomaly_v03_preformal_bound_draw_bridge', '--child', role,
            str(root), str(input_pin['bytes']), input_pin['sha256']]
    if role == 'audit':
        argv += [str(calculation_pin['bytes']), calculation_pin['sha256']]
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT / 'src')
    stdout_path = root / (role + '-stdout.json')
    stderr_path = root / (role + '-stderr.txt')
    started = time.monotonic()
    process = None
    peak = samples = 0
    reason = None
    errors = []
    with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while process.poll() is None:
                peak = max(peak, resources.memory_bytes(process._handle)['peak_private_bytes'])
                samples += 1
                reason = budget.probe()
                if time.monotonic() - started > CHILD_WALL_SECONDS:
                    reason = reason or 'bridge_child_wall_limit'
                if peak > CHILD_PRIVATE_BYTES:
                    reason = reason or 'bridge_child_private_limit'
                if stdout_path.stat().st_size + stderr_path.stat().st_size > LOG_BYTES:
                    reason = reason or 'bridge_child_log_limit'
                if reason:
                    break
                time.sleep(.25)
        except BaseException as error:
            errors.append({'stage': 'monitor', 'error_type': type(error).__name__})
            reason = reason or 'bridge_child_observation_error'
        finally:
            confirmed = False
            for attempt in range(3):
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=10)
                    confirmed = process.returncode is not None
                    if confirmed:
                        break
                except BaseException as error:
                    errors.append({'stage': 'reap', 'attempt': attempt + 1,
                                   'error_type': type(error).__name__})
            if not confirmed:
                raise draw_budget.UnreapedMeasurement(process, role,
                    {'stop_reason': reason, 'errors': errors,
                     'elapsed_seconds': time.monotonic() - started})
            try:
                peak = max(peak, resources.memory_bytes(process._handle)['peak_private_bytes'])
                process._handle.Close()
            except BaseException as error:
                errors.append({'stage': 'final_memory_or_handle',
                               'error_type': type(error).__name__})
                reason = reason or 'bridge_child_observation_error'
    reason = reason or budget.probe()
    stdout_pin = _pin(draw_budget._bounded_file(stdout_path, LOG_BYTES))
    stderr_pin = _pin(draw_budget._bounded_file(stderr_path, LOG_BYTES))
    if stdout_pin['bytes'] + stderr_pin['bytes'] > LOG_BYTES:
        reason = reason or 'bridge_child_log_limit'
    return {'format': FORMAT + '-supervision', 'role': role,
            'status': 'complete' if process.returncode == 0 and reason is None and
            not errors else 'failed', 'pid': process.pid, 'exit_code': process.returncode,
            'worker_exit_confirmed': True, 'elapsed_seconds': time.monotonic() - started,
            'peak_child_private_bytes': peak, 'samples': samples,
            'stop_reason': reason, 'observation_errors': errors,
            'stdout_pin': stdout_pin, 'stderr_pin': stderr_pin,
            'formal_permission': False}


def _verify_role(root, role, supervision, output_pin):
    if supervision['status'] != 'complete' or not supervision['worker_exit_confirmed']:
        raise ValueError(role + ' owned child failed')
    report = json.loads(_read(root / (role + '-stdout.json'),
                              supervision['stdout_pin'], LOG_BYTES))
    expected = {'format': FORMAT + '-role', 'role': role, 'status': 'complete',
                'replicates': REPLICATES, 'draw_sha256': frozen.BOOTSTRAP_HASH,
                'output_pin': output_pin, 'registered_data_read': False,
                'formal_bootstrap_performed': False, 'formal_permission': False,
                'independent_s6_complete': False}
    if (type(report) is not dict or set(report) != set(expected) or
            any(type(report[key]) is not type(value) or report[key] != value
                for key, value in expected.items())):
        raise ValueError(role + ' child report differs')


def run_bridge(*, expected_mode, producer_root, expected_producer_result_pin,
               expected_revision, receipt_name, receipt_parent=OUTPUT_PARENT):
    """Retain a bounded two-child attempt; native 50,000 draws are explicit."""
    if type(expected_mode) is not str or expected_mode != 'fixture':
        raise ValueError('bridge accepts only invented fixture mode')
    projection.evidence._pin(expected_producer_result_pin)
    projection.evidence._digest(expected_revision, 40)
    projection.v.safe_relative_path(receipt_name)
    if ('/' in receipt_name or '\\' in receipt_name or
            receipt_name.casefold().startswith('anomaly-multiseed-v0')):
        raise ValueError('new preformal bridge receipt name required')
    parent = Path(receipt_parent).absolute()
    if parent != OUTPUT_PARENT:
        raise ValueError('bridge output parent differs')
    parent.mkdir(exist_ok=True)
    projection.io.regular_path(parent, directory=True)
    root = projection.io.regular_path(parent / receipt_name, directory=True,
                                      missing=True)
    root.mkdir()
    started = time.monotonic()
    result = {'format': FORMAT, 'scope': 'owned-invented-producer-bound-to-50000-primary-arithmetic-only',
              'status': 'failed', 'reason': None, 'stage': 'preflight',
              'producer_root': str(producer_root),
              'producer_result_pin': copy.deepcopy(expected_producer_result_pin),
              'source_revision': expected_revision, 'replicates_required': REPLICATES,
              'full_end_to_end_budget_measured': False,
              'formal_50000_draw_budget_measured': False, 'new_evaluations': 0,
              'invented_50000_primary_tables_measured': False,
              'invented_50000_independent_arithmetic_matched': False,
              **CLOSED}
    budget = None
    critical = None
    try:
        budget = BoundDrawBudget(root).start()
        budget.checkpoint('preflight')
        result['source_pins_before'] = _git_pins(expected_revision)
        result['runtime_before'] = platform_runtime.probe_runtime(ROOT)
        binding = bind_producer_counts(producer_root, expected_producer_result_pin)
        result['producer_binding'] = {key: copy.deepcopy(value) for key, value in
            binding.items() if key != 'clusters'}
        input_raw = _raw(_input(binding))
        if len(input_raw) > 512 * 1024:
            raise ValueError('bridge input byte limit')
        input_pin = _write(root / 'input.json', input_raw)
        result['input_pin'] = input_pin
        for role in ('analysis', 'audit'):
            result['stage'] = role
            budget.checkpoint(role)
            calculation_pin = result.get('calculation_pin')
            supervision = _supervise(role, root, input_pin, calculation_pin, budget)
            supervision_raw = _raw(supervision)
            result[role + '_supervision_pin'] = _write(
                root / (role + '-supervision.json'), supervision_raw)
            result[role + '_supervision'] = supervision
            budget.record_role(role, supervision['status'],
                               result_pin=result[role + '_supervision_pin'],
                               worker_pid=supervision['pid'],
                               exit_confirmed=supervision['worker_exit_confirmed'])
            if supervision['status'] != 'complete':
                raise resources.ResourceStop(supervision['stop_reason'] or
                                             role + '_owned_child_failed')
            output_name = 'calculation.json' if role == 'analysis' else 'audit.json'
            output_pin = _pin(draw_budget._bounded_file(root / output_name,
                                                        OUTPUT_BYTES))
            _verify_role(root, role, supervision, output_pin)
            result['calculation_pin' if role == 'analysis' else 'audit_pin'] = output_pin
            if role == 'analysis':
                result['invented_50000_primary_tables_measured'] = True
        audit = json.loads(_read(root / 'audit.json', result['audit_pin'], OUTPUT_BYTES))
        draw_budget._verify_audit_report(audit, result['calculation_pin'])
        result['invented_50000_independent_arithmetic_matched'] = True
        result['stage'] = 'postflight'
        budget.checkpoint('postflight')
        if bind_producer_counts(producer_root, expected_producer_result_pin) != binding:
            raise ValueError('external owned producer changed after arithmetic')
        if _git_pins(expected_revision) != result['source_pins_before']:
            raise ValueError('bridge selected source changed')
        result['runtime_after'] = platform_runtime.probe_runtime(ROOT)
        if result['runtime_after'] != result['runtime_before']:
            raise ValueError('bridge runtime changed')
        for name, pin in [('input.json', input_pin),
                          ('calculation.json', result['calculation_pin']),
                          ('audit.json', result['audit_pin'])]:
            _read(root / name, pin, 512 * 1024 if name == 'input.json' else OUTPUT_BYTES)
        result['status'] = 'measured'
        result['stage'] = 'complete'
    except draw_budget.UnreapedMeasurement as error:
        result.update(reason='owned_child_exit_unconfirmed',
                      unreaped_role=error.role, worker_exit_confirmed=False)
        error.receipt = root
        critical = error
    except resources.ResourceStop as error:
        result['reason'] = error.reason
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result.update(reason='bridge_rejected', error_type=type(error).__name__,
                      detail=str(error))
    except BaseException as error:
        result.update(reason='unexpected_bridge_exception',
                      error_type=type(error).__name__)
        critical = error
    finally:
        if budget is not None and budget._thread is not None:
            try:
                report = budget.close()
                result['resource_budget_pin'] = _write(root / 'resource-budget.json',
                                                       _raw(report))
                result['shared_budget_passed'] = report['passed']
                result['both_arithmetic_child_exits_reported'] = report[
                    'both_arithmetic_child_exits_reported']
                if result['status'] == 'measured' and (not report['passed'] or
                        not report['both_arithmetic_child_exits_reported']):
                    result.update(status='failed', reason=report['stop_reason'] or
                                  'arithmetic_child_exit_missing')
            except BaseException as error:
                result.update(status='failed', reason='bridge_budget_close_failed',
                              budget_error_type=type(error).__name__)
                critical = critical or error
        result['wall_seconds'] = time.monotonic() - started
        try:
            if len(_raw(result)) > 64 * 1024:
                raise ValueError('bridge result byte limit')
            _write(root / 'result.json', _raw(result))
        except BaseException as error:
            critical = critical or error
    if critical is not None:
        raise critical
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == '--child' and len(argv) in (5, 7):
        role, root = argv[1], Path(argv[2])
        input_pin = {'bytes': int(argv[3]), 'sha256': argv[4]}
        calculation_pin = ({'bytes': int(argv[5]), 'sha256': argv[6]}
                           if len(argv) == 7 else None)
        _child(role, root, input_pin, calculation_pin)
        return 0
    if argv and argv[0] == '--measure' and len(argv) == 5:
        revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse',
                                            'HEAD'], text=True, timeout=10).strip()
        result = run_bridge(expected_mode='fixture', producer_root=Path(argv[2]),
                            expected_producer_result_pin={'bytes': int(argv[3]),
                                                          'sha256': argv[4]},
                            expected_revision=revision, receipt_name=argv[1])
        print(_raw({'status': result['status'], 'reason': result['reason'],
                    'receipt': str(OUTPUT_PARENT / argv[1])}).decode('utf-8'))
        return 0 if result['status'] == 'measured' else 2
    raise SystemExit('usage: --measure RECEIPT_NAME PRODUCER_ROOT RESULT_BYTES RESULT_SHA256')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except draw_budget.UnreapedMeasurement as owner:
        draw_budget.retain_unreaped_owner(owner)
        raise
