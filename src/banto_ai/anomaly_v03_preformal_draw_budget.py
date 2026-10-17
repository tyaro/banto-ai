"""Bounded resource probe for invented 40-cluster, 50,000-draw arithmetic.

This is a separate preformal measurement identity. It does not use the formal
launcher, the OS-pinned fixture worker, registered observations, or S6 claims.
Each role runs once in an owned process under a new, retained receipt root.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time

from . import _anomaly_v03_contract as frozen
from . import _anomaly_v03_fixture_budget as budget
from . import _anomaly_v03_engineering_runtime as resources

ROOT = Path(__file__).resolve().parents[2]
MEASUREMENT_PARENT = ROOT/'artifacts'
FORMAT = 'anomaly-v03-preformal-draw-budget-v1'
REPLICATES = 50000
CLUSTERS = 40
DRAW_HASH = frozen.BOOTSTRAP_HASH
WALL_SECONDS = 900
CHILD_PRIVATE_LIMIT = 1024**3
PARENT_PRIVATE_LIMIT = 512*1024**2
OUTPUT_LIMIT = 256*1024
ROOT_LIMIT = 64*1024**2
MINIMUM_HEADROOM = 4*1024**3
MINIMUM_DISK = 10*1024**3
SAMPLE_SECONDS = .25
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_preformal_draw_budget.py',
    'src/banto_ai/anomaly_v03_preformal_draw_audit.py',
    'src/banto_ai/_anomaly_v03_contract.py',
    'src/banto_ai/anomaly_v03_inference_audit.py',
)
CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
LAYERS = ('core', 'quality-stress')
TARGETS = tuple(e+'.'+s for e in ('motor-01', 'conveyor-01') for s in
                ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature'))
AVAILABILITY = tuple('availability:'+target for target in TARGETS)


def _raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _write(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)


def _read(path, expected, maximum=OUTPUT_LIMIT):
    raw = _bounded_file(path, maximum)
    if _pin(raw) != expected:
        raise ValueError('measurement file pin differs')
    return raw


def _bounded_file(path, maximum):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_nlink != 1:
        raise ValueError('measurement file inventory changed')
    if info.st_size > maximum:
        raise ValueError('measurement file exceeds limit')
    with path.open('rb') as stream:
        raw = stream.read(maximum+1)
    after = path.lstat()
    if len(raw) > maximum or len(raw) != info.st_size or (info.st_dev, info.st_ino, info.st_size) != (after.st_dev, after.st_ino, after.st_size):
        raise ValueError('measurement file exceeds limit')
    return raw


def _pin_file(path, maximum=OUTPUT_LIMIT):
    return _pin(_bounded_file(path, maximum))


def invented_clusters():
    """Small deterministic counts; IDs contain no registered seed or slot."""
    clusters = []
    for index in range(CLUSTERS):
        candidates = {}
        for candidate_index, candidate in enumerate(CANDIDATES):
            layers = {}
            for layer_index, layer in enumerate(LAYERS):
                machine = (78, 91, 89)[candidate_index] + (index+layer_index) % 7
                sensor = (76, 92, 87)[candidate_index] + (index+2*layer_index) % 6
                false = (12, 5, 7)[candidate_index] + index % 3
                clean = min(false, (5, 2, 3)[candidate_index] + index % 2)
                matched = machine+sensor
                counts = {'machine_recall': [machine, 120], 'sensor_recall': [sensor, 120],
                          'precision': [matched, matched+false],
                          'clean_rate': [clean, 40380],
                          'false_alert_burden': [false, 240]}
                counts.update({name: [20700 + candidate_index*110 + (index*13+target_index*7+layer_index*5) % 71,
                                      21600] for target_index, name in enumerate(AVAILABILITY)})
                layers[layer] = {'profile_status': 'calibrated', 'counts': counts}
            candidates[candidate] = layers
        clusters.append({'cluster_id': f'budget-invented-{index:02d}', 'candidates': candidates})
    return clusters


def _input():
    return {'format': FORMAT+'-input', 'invented_only': True,
            'registered_data_read': False, 'clusters': invented_clusters()}


def _child(role, receipt, input_pin, calculation_pin=None):
    if role not in ('calculate', 'audit') or receipt.name.startswith('anomaly-multiseed-v03-holdout'):
        raise ValueError('preformal role/root required')
    data = json.loads(_read(receipt/'input.json', input_pin, 512*1024))
    if data != _input():
        raise ValueError('invented fixture differs')
    if role == 'calculate':
        from . import anomaly_v03_inference_audit as inference
        inference._fixture_clusters(data['clusters'])
        indices = frozen.bootstrap_indices()
        if len(indices) != CLUSTERS*REPLICATES or hashlib.sha256(indices).hexdigest() != DRAW_HASH:
            raise ValueError('frozen draw digest differs')
        draws = [indices[offset:offset+CLUSTERS] for offset in range(0, len(indices), CLUSTERS)]
        calculation = inference.compute_fixture_tables(data['clusters'], draws, engineering_ready=False)
        raw = _raw(calculation)
        output = receipt/'calculation.json'
        if len(raw) > OUTPUT_LIMIT:
            raise ValueError('calculation output exceeds limit')
        _write(output, raw)
        report = {'format': FORMAT+'-role', 'role': role, 'status': 'complete',
                  'draw_sha256': DRAW_HASH, 'draw_bytes': len(indices),
                  'replicates': len(draws), 'output_pin': _pin(raw),
                  'registered_data_read': False, 'formal_bootstrap_performed': False,
                  'formal_permission': False}
    else:
        from . import anomaly_v03_preformal_draw_audit as independent
        if calculation_pin is None:
            raise ValueError('retained calculation pin required')
        calculated = json.loads(_read(receipt/'calculation.json', calculation_pin))
        draws, digest = independent.independent_draws()
        report = independent.audit(data['clusters'], calculated, draws)
        if digest != DRAW_HASH or report['calculation_sha256'] != calculation_pin['sha256']:
            raise ValueError('independent calculation binding differs')
        raw = _raw(report)
        _write(receipt/'audit.json', raw)
        report = {'format': FORMAT+'-role', 'role': role, 'status': 'complete',
                  'draw_sha256': digest, 'draw_bytes': CLUSTERS*len(draws),
                  'replicates': len(draws), 'output_pin': _pin(raw),
                  'registered_data_read': False, 'formal_bootstrap_performed': False,
                  'formal_permission': False, 'independent_s6_complete': False}
    print(_raw(report).decode('utf-8'), flush=True)


def _source_pins():
    return {name: _pin((ROOT/name).read_bytes()) for name in SOURCE_NAMES}


def _runtime():
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:
        release = winreg.QueryValueEx(key, 'DisplayVersion')[0]
        build = int(winreg.QueryValueEx(key, 'CurrentBuildNumber')[0])
        ubr = int(winreg.QueryValueEx(key, 'UBR')[0])
    return {'release': release, 'build': build, 'ubr': ubr,
            'python': platform.python_version(), 'executable_sha256': _pin(Path(sys.executable).read_bytes())['sha256'],
            'os_name': os.name}


def _check_resources(snapshot, parent, peak):
    if snapshot['commit_headroom_bytes'] < MINIMUM_HEADROOM:
        return 'commit_headroom'
    if snapshot['free_ram_bytes'] < MINIMUM_HEADROOM:
        return 'free_ram'
    if snapshot['free_disk_bytes'] < MINIMUM_DISK:
        return 'free_disk'
    if snapshot['parent_peak_private_bytes'] > PARENT_PRIVATE_LIMIT:
        return 'parent_private'
    if peak > CHILD_PRIVATE_LIMIT:
        return 'child_private'
    if _root_bytes(parent) > ROOT_LIMIT:
        return 'receipt_bytes'
    return None


def _root_bytes(parent):
    children = list(parent.iterdir())
    if len(children) > 16:
        raise ValueError('measurement receipt inventory limit')
    total = 0
    for child in children:
        info = child.lstat()
        if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_nlink != 1:
            raise ValueError('measurement receipt unsafe entry')
        total += info.st_size
    return total


def _bounded_pin(path, maximum):
    return _pin_file(path, maximum)


def _check_parent(receipt):
    parent = MEASUREMENT_PARENT.absolute()
    if receipt.parent != parent:
        raise ValueError('preformal receipt parent differs')
    for path in (ROOT, parent):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('preformal receipt parent unsafe')


def _final_pins(receipt, held):
    if {path.name for path in receipt.iterdir()} != set(held):
        raise ValueError('measurement receipt inventory differs')
    for name, pin in held.items():
        maximum = 512*1024 if name == 'input.json' else OUTPUT_LIMIT
        _read(receipt/name, pin, maximum)


def _verify_role_report(value, role, output_pin):
    fields = {'format', 'role', 'status', 'draw_sha256', 'draw_bytes',
              'replicates', 'output_pin', 'registered_data_read',
              'formal_bootstrap_performed', 'formal_permission'}
    if role == 'audit':
        fields.add('independent_s6_complete')
    if type(value) is not dict or set(value) != fields:
        raise ValueError(role+'_role_report_fields')
    expected = {'format': FORMAT+'-role', 'role': role, 'status': 'complete',
                'draw_sha256': DRAW_HASH, 'draw_bytes': 2000000,
                'replicates': REPLICATES, 'output_pin': output_pin,
                'registered_data_read': False,
                'formal_bootstrap_performed': False, 'formal_permission': False}
    if role == 'audit':
        expected['independent_s6_complete'] = False
    for key, answer in expected.items():
        if type(value[key]) is not type(answer) or value[key] != answer:
            raise ValueError(role+'_role_report_differs_'+key)


def _verify_audit_report(value, calculation_pin):
    fields = {'format', 'status', 'draw_sha256', 'clusters', 'replicates',
              'candidate_tables', 'primary_estimates', 'paired_estimates',
              'gates', 'calculation_sha256', 'registered_data_read',
              'formal_bootstrap_performed', 'independent_s6_complete',
              'formal_permission', 'promotion_allowed', 'performance_status'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('audit_report_fields')
    expected = {'format': 'anomaly-v03-preformal-draw-budget-audit-v1',
                'status': 'invented_primary_numerics_matched',
                'draw_sha256': DRAW_HASH, 'clusters': CLUSTERS,
                'replicates': REPLICATES, 'candidate_tables': 9,
                'primary_estimates': 117, 'paired_estimates': 72, 'gates': 180,
                'calculation_sha256': calculation_pin['sha256'],
                'registered_data_read': False,
                'formal_bootstrap_performed': False,
                'independent_s6_complete': False, 'formal_permission': False,
                'promotion_allowed': False, 'performance_status': 'not_evaluated'}
    for key, answer in expected.items():
        if type(value[key]) is not type(answer) or value[key] != answer:
            raise ValueError('audit_report_differs_'+key)


class UnreapedMeasurement(RuntimeError):
    def __init__(self, process, role, detail):
        self.process, self.role, self.detail = process, role, detail
        self.receipt = None
        super().__init__('owned measurement child exit unconfirmed')


def retain_unreaped_owner(error):
    """Emergency CLI owner path: never leave its still-live child unattended."""
    process = error.process
    attempts = 0
    while process.returncode is None:
        attempts += 1
        try:
            process.kill()
        except BaseException:
            pass
        try:
            process.wait(timeout=30)
        except BaseException:
            pass
        try:
            process.poll()
        except BaseException:
            pass
    try:
        process._handle.Close()
    except BaseException:
        pass
    if error.receipt is not None:
        try:
            failed_receipt_pin = _pin_file(error.receipt/'receipt.json')
        except BaseException:
            failed_receipt_pin = None
        recovery = {'format': FORMAT+'-owner-recovery', 'role': error.role,
                    'pid': process.pid, 'attempts': attempts,
                    'exit_code': process.returncode, 'worker_exit_confirmed': True,
                    'failed_receipt_pin': failed_receipt_pin,
                    'measurement_status': 'failed', 'formal_permission': False}
        try:
            _write(error.receipt/'owner-recovery.json', _raw(recovery))
        except BaseException:
            pass


def _supervise(role, receipt, input_pin, calculation_pin=None):
    argv = [sys.executable, '-B', '-m', 'banto_ai.anomaly_v03_preformal_draw_budget',
            '--child', role, str(receipt), str(input_pin['bytes']), input_pin['sha256']]
    if calculation_pin is not None:
        argv += [str(calculation_pin['bytes']), calculation_pin['sha256']]
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT/'src')
    stdout_path, stderr_path = receipt/(role+'-stdout.json'), receipt/(role+'-stderr.txt')
    started = time.monotonic()
    peak, samples, extrema, reason, process = 0, 0, {}, None, None
    errors = []
    with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while process.poll() is None:
                peak = max(peak, resources.memory_bytes(process._handle)['peak_private_bytes'])
                snap = budget.system_snapshot(receipt)
                samples += 1
                for key in ('commit_headroom_bytes', 'free_ram_bytes', 'free_disk_bytes'):
                    extrema[key] = min(extrema.get(key, snap[key]), snap[key])
                reason = _check_resources(snap, receipt, peak)
                if time.monotonic()-started > WALL_SECONDS:
                    reason = reason or 'wall_limit'
                if stdout_path.stat().st_size+stderr_path.stat().st_size > OUTPUT_LIMIT:
                    reason = reason or 'log_limit'
                if reason:
                    break
                time.sleep(SAMPLE_SECONDS)
        except BaseException as error:
            errors.append({'stage': 'monitor', 'error_type': type(error).__name__})
            reason = reason or ('interrupted' if isinstance(error, KeyboardInterrupt) else 'observation_error')
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
                    errors.append({'stage': 'reap', 'attempt': attempt+1, 'error_type': type(error).__name__})
            if not confirmed:
                raise UnreapedMeasurement(process, role, {'stop_reason': reason, 'errors': errors,
                                                            'elapsed_seconds': time.monotonic()-started})
            try:
                peak = max(peak, resources.memory_bytes(process._handle)['peak_private_bytes'])
            except BaseException as error:
                errors.append({'stage': 'final_memory', 'error_type': type(error).__name__})
                reason = reason or 'observation_error'
            try:
                process._handle.Close()
            except BaseException as error:
                errors.append({'stage': 'handle_close', 'error_type': type(error).__name__})
                reason = reason or 'observation_error'
    ended = None
    try:
        ended = budget.system_snapshot(receipt)
        reason = reason or _check_resources(ended, receipt, peak)
    except BaseException as error:
        errors.append({'stage': 'final_resources', 'error_type': type(error).__name__})
        reason = reason or 'observation_error'
    stdout_pin = stderr_pin = None
    try:
        if stdout_path.stat().st_size+stderr_path.stat().st_size > OUTPUT_LIMIT:
            reason = reason or 'log_limit'
        else:
            stdout_pin = _bounded_pin(stdout_path, OUTPUT_LIMIT)
            stderr_pin = _bounded_pin(stderr_path, OUTPUT_LIMIT-stdout_pin['bytes'])
    except BaseException as error:
        errors.append({'stage': 'logs', 'error_type': type(error).__name__})
        reason = reason or 'log_limit'
    return {'format': FORMAT+'-supervision', 'role': role,
            'status': 'complete' if process.returncode == 0 and reason is None and not errors else 'failed',
            'pid': process.pid, 'exit_code': process.returncode, 'worker_exit_confirmed': True,
            'stop_reason': reason, 'elapsed_seconds': time.monotonic()-started,
            'peak_child_private_bytes': peak, 'samples': samples, 'minimum_resources': extrema,
            'last_resources': ended, 'stdout_pin': stdout_pin, 'stderr_pin': stderr_pin,
            'observation_errors': errors, 'formal_permission': False}


def run_measurement(receipt):
    """Create a new receipt root, run both roles once, and retain any failure."""
    receipt = Path(receipt).absolute()
    if not receipt.name.startswith('anomaly-v03-preformal-draw-budget-'):
        raise ValueError('new preformal root name required')
    _check_parent(receipt)
    if not receipt.parent.is_dir() or receipt.is_symlink() or receipt.exists():
        raise ValueError('new receipt root required')
    receipt.mkdir()
    result = {'format': FORMAT, 'scope': 'invented-arithmetic-resource-probe-only',
              'status': 'failed', 'reason': None, 'receipt': str(receipt),
              'replicates_required': REPLICATES, 'registered_data_read': False,
              'formal_bootstrap_performed': False, 'independent_s6_complete': False,
              'formal_permission': False, 'promotion_allowed': False,
              'performance_status': 'not_evaluated', 'cim_observation': 'not_used',
              'source_pins_scope': 'selected-measurement-modules-only-not-full-runtime-closure'}
    held = {}
    owner_error = None
    try:
        result['source_pins_before'] = _source_pins()
        result['runtime_before'] = _runtime()
        first = budget.system_snapshot(receipt)
        result['initial_resources'] = first
        stop = _check_resources(first, receipt, 0)
        if stop:
            raise ValueError('preflight_'+stop)
        raw_input = _raw(_input())
        if len(raw_input) > 512*1024:
            raise ValueError('invented input exceeds limit')
        _write(receipt/'input.json', raw_input)
        input_pin = _pin(raw_input)
        result['input_pin'] = held['input.json'] = input_pin
        for role in ('calculate', 'audit'):
            calc_pin = held['calculation.json'] if role == 'audit' else None
            supervision = _supervise(role, receipt, input_pin, calc_pin)
            raw_supervision = _raw(supervision)
            supervision_name = role+'-supervision.json'
            _write(receipt/supervision_name, raw_supervision)
            held[supervision_name] = _pin(raw_supervision)
            result[role+'_supervision'] = supervision
            if supervision['status'] != 'complete':
                raise ValueError(role+'_supervision_failed')
            output_name = 'calculation.json' if role == 'calculate' else 'audit.json'
            output_pin = _pin_file(receipt/output_name)
            held[output_name] = output_pin
            held[role+'-stdout.json'] = supervision['stdout_pin']
            held[role+'-stderr.txt'] = supervision['stderr_pin']
            role_report = json.loads(_read(receipt/(role+'-stdout.json'), supervision['stdout_pin']))
            _verify_role_report(role_report, role, output_pin)
            result[role+'_output_pin'] = output_pin
        audit = json.loads(_read(receipt/'audit.json', result['audit_output_pin']))
        _verify_audit_report(audit, result['calculate_output_pin'])
        result['source_pins_after'] = _source_pins()
        result['runtime_after'] = _runtime()
        if result['source_pins_before'] != result['source_pins_after'] or result['runtime_before'] != result['runtime_after']:
            raise ValueError('measurement source/runtime changed')
        _final_pins(receipt, held)
        result['retained_file_pins'] = held
        result['status'] = 'measured'
    except UnreapedMeasurement as error:
        owner_error = error
        error.receipt = receipt
        result['worker_exit_confirmed'] = False
        result['unreaped_role'] = error.role
        result['unreaped_detail'] = error.detail
        result['reason'] = type(error).__name__+': '+str(error)
    except BaseException as error:
        result['reason'] = type(error).__name__+': '+str(error)
    try:
        result['final_resources'] = budget.system_snapshot(receipt)
        stop = _check_resources(result['final_resources'], receipt, 0)
        if stop and result['status'] == 'measured':
            result['status'] = 'failed'
            result['reason'] = 'final_'+stop
    except BaseException as error:
        result['status'] = 'failed'
        result['final_resource_observation_error'] = type(error).__name__
        result['reason'] = result['reason'] or 'final_resource_observation_error'
    try:
        _write(receipt/'receipt.json', _raw(result))
    except BaseException as receipt_error:
        if owner_error is not None:
            owner_error.receipt_error = receipt_error
            raise owner_error
        raise
    if owner_error is not None:
        raise owner_error
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) in (5, 7) and argv[0] == '--child':
        role, receipt = argv[1], Path(argv[2])
        input_pin = {'bytes': int(argv[3]), 'sha256': argv[4]}
        calculation_pin = {'bytes': int(argv[5]), 'sha256': argv[6]} if len(argv) == 7 else None
        _child(role, receipt, input_pin, calculation_pin)
        return 0
    if len(argv) == 2 and argv[0] == '--measure':
        result = run_measurement(Path(argv[1]))
        print(_raw({'status': result['status'], 'reason': result['reason'], 'receipt': result['receipt']}).decode('utf-8'))
        return 0 if result['status'] == 'measured' else 2
    raise SystemExit('usage: --measure NEW_RECEIPT | --child ROLE RECEIPT INPUT_BYTES INPUT_SHA [CALC_BYTES CALC_SHA]')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except UnreapedMeasurement as owner:
        retain_unreaped_owner(owner)
        raise
