"""Independent frozen-plan normal/overlay/rounding verifier; stdlib only.

This reconstructs an existing dev/smoke pair in memory, one row at a time.
It does not create dataset files, run detectors, or award campaign credit.
Equations and scheduling are independently transcribed from plan sections 3.1-3.3;
Random.gauss, binary64, round and JSON are shared specified runtime primitives,
NOT independent implementations of those primitives. The caller authenticates
the completed capture and registered coordinates before invoking this module.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import random

EQUIPMENT = ('motor-01', 'conveyor-01')
KINDS = ('motor', 'conveyor')
MODES = ('stopped', 'startup', 'low_speed', 'nominal', 'high_load', 'cooldown')
RECIPES = ('stop', 'start', 'low', 'run', 'load', 'cooldown')
SIGNALS = ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature', 'load_proxy')
STRATA = ('core', 'quality-stress')
FILES = ('observations.jsonl', 'quality-mask.jsonl', 'event-ledger.jsonl', 'events.jsonl')
START_MS = 1767225600000
PRIORITY = {'machine': 0, 'sensor': 1, 'ignored': 2, 'data_quality': 3}


def need(condition, reason):
    if not condition:
        raise ValueError('generation audit: ' + reason)


def canonical_line(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def coordinate(role, seed, layout):
    need(role in ('dev', 'smoke'), 'only dev/smoke coordinates supported')
    need(type(seed) is int and 0 <= seed < 2**63, 'exact integer seed required')
    need(type(layout) is int and 0 <= layout < 12, 'layout outside frozen plan')
    return f'anomaly-v03-{role}-seed-{seed}-layout-{layout:02d}'


def normal_step(equipment_index, mode_index, previous_temperature, rng):
    """Five Gaussian draws in the prescribed equipment-dependent order."""
    speed, load = ((0., 0.), (35., 18.), (45., 32.), (70., 55.), (72., 88.), (20., 22.))[mode_index]
    sigmas = ((.08, .4, .025, .025, .45), (.004, .06, .025, .025, .45))[equipment_index]
    noises = [rng.gauss(0., sigma) for sigma in sigmas]
    current_noise, speed_noise = (noises[0], noises[1]) if equipment_index == 0 else (noises[1], noises[0])
    base, speed_weight, load_weight = ((1.2, .085, .055), (.8, .045, .035))[equipment_index]
    current = base + speed * speed_weight + load * load_weight + current_noise
    velocity = (speed if equipment_index == 0 else speed * .018) + speed_noise
    equilibrium = 24. + current * .48 + load * .025
    temperature = previous_temperature + (equilibrium - previous_temperature) * .12 + noises[2]
    return {'motor_current': current, 'conveyor_speed': velocity, 'motor_temperature': temperature,
            'vibration_feature': .18 + speed * .012 + load * .009 + abs(noises[3]),
            'load_proxy': load + noises[4]}


def normal_rows(seed):
    need(type(seed) is int and 0 <= seed < 2**63, 'exact integer seed required')
    rng = random.Random(seed)
    for ei, equipment in enumerate(EQUIPMENT):
        temperature = 24.
        for sample in range(9000):
            values = normal_step(ei, (sample // 30) % 6, temperature, rng)
            temperature = values['motor_temperature']
            yield equipment, sample, values


def event_schedule(role, seed, layout, stratum):
    pair = coordinate(role, seed, layout)
    need(stratum in STRATA, 'unknown stratum')
    ei, mode = divmod(layout, 6)
    equipment = EQUIPMENT[ei]
    specs = (('machine', 'jam_or_slip', ('motor_current', 'conveyor_speed')[ei], .55),
             ('sensor', 'spike', 'motor_temperature', 8.),
             ('data_quality', 'dropout', 'motor_temperature', 0.),
             ('ignored', 'stuck_value', 'load_proxy', 0.))
    answer = []
    for cycle in range(10):
        base = 7200 + cycle * 180 + mode * 30
        starts = [base + 7 * ((layout + k) % 4) for k in range(4)]
        if cycle == 9:
            starts[2] = starts[1] + 1
        for start, (kind, event_type, target, magnitude) in zip(starts, specs):
            answer.append({'cycle': cycle, 'dataset_id': pair + '-' + stratum,
                'enabled': kind != 'data_quality' or stratum == 'quality-stress',
                'end_ms': START_MS + (start + 3) * 1000, 'end_sample': start + 3,
                'equipment': equipment, 'event_class': kind,
                'event_id': f'{pair}-cycle-{cycle:02d}-{kind}', 'event_type': event_type,
                'full_target': equipment + '.' + target, 'magnitude': magnitude,
                'mode': MODES[mode], 'recipe': RECIPES[mode],
                'start_ms': START_MS + start * 1000, 'start_sample': start,
                'window_end_ms': START_MS + (start + 6) * 1000, 'window_end_sample': start + 6})
    return answer


def event_index(events):
    answer = {}
    for event in sorted(events, key=lambda e: PRIORITY[e['event_class']]):
        if event['enabled']:
            for sample in range(event['start_sample'], event['end_sample']):
                answer.setdefault((event['equipment'], sample), []).append(event)
    return answer


def overlay_and_round(normal, active, stuck):
    need(type(normal) is dict and set(normal) == set(SIGNALS), 'normal signal fields')
    need(all(type(x) in (int, float) and math.isfinite(x) for x in normal.values()),
         'nonfinite or nonnumeric normal before masking')
    values = normal.copy()
    quality = dict.fromkeys(SIGNALS, 'ok')
    for event in sorted(active, key=lambda e: PRIORITY[e['event_class']]):
        target = event['full_target'].split('.', 1)[1]
        kind, magnitude = event['event_class'], event['magnitude']
        if kind == 'machine':
            values[target] = max(0., values[target] * max(0., 1. - magnitude))
            values['load_proxy'] = min(100., values['load_proxy'] + abs(magnitude) * 35.)
            values['vibration_feature'] = values['vibration_feature'] + abs(magnitude) * 2.
        elif kind == 'sensor':
            values[target] = values[target] + magnitude
        elif kind == 'ignored':
            key = (event['event_id'], target)
            values[target] = stuck.setdefault(key, values[target])
        else:
            values[target], quality[target] = None, 'missing'
    output = {}
    for name in SIGNALS:
        value = values[name]
        need(value is None or math.isfinite(value), 'nonfinite overlay output')
        output[name] = None if value is None else round(float(value), 6)
    return output, quality


def observation(equipment, sample, values, quality):
    ei, mode = EQUIPMENT.index(equipment), (sample // 30) % 6
    units = ('A', 'degC', ('percent', 'm/s')[ei], 'mm/s', 'percent')
    return {'timestamp': f'2026-01-01T{sample//3600:02d}:{sample//60%60:02d}:{sample%60:02d}.000Z',
        'equipment_id': equipment, 'equipment_type': KINDS[ei],
        'operating_mode': MODES[mode], 'recipe_step': RECIPES[mode],
        'signals': {name: {'unit': unit, 'value': values[name]} for name, unit in zip(SIGNALS, units)},
        'quality': quality}


def audit_generation_pair(role, seed, layout, captures, *, expected_sha256):
    """Exact canonical bytes, including signed zero; no float tolerance.

    captures[stratum][filename] and expected_sha256 have exactly 2 x 4 entries.
    Both saved strata are checked against the same independent normal stream.
    All input hashes are checked BEFORE any seed reconstruction.
    """
    pair = coordinate(role, seed, layout)
    need(type(captures) is dict and set(captures) == set(STRATA), 'paired captures required')
    need(type(expected_sha256) is dict and set(expected_sha256) == set(STRATA), 'paired input digests required')
    for stratum in STRATA:
        need(type(captures[stratum]) is dict and set(captures[stratum]) == set(FILES), 'capture file inventory')
        need(type(expected_sha256[stratum]) is dict and set(expected_sha256[stratum]) == set(FILES), 'digest inventory')
        for name in FILES:
            raw = captures[stratum][name]
            need(type(raw) is bytes and hashlib.sha256(raw).hexdigest() == expected_sha256[stratum][name],
                 f'{stratum}/{name} input digest')
    schedules, streams, stuck = {}, {}, {s: {} for s in STRATA}
    for stratum in STRATA:
        events = event_schedule(role, seed, layout, stratum)
        for name, rows in (('event-ledger.jsonl', events), ('events.jsonl', [e for e in events if e['enabled']])):
            need(captures[stratum][name] == b''.join(map(canonical_line, rows)), f'{stratum}/{name} event schedule')
        schedules[stratum] = event_index(events)
        streams[stratum] = {name: io.BytesIO(captures[stratum][name]) for name in FILES[:2]}
    rows = missing = 0
    for equipment, sample, normal in normal_rows(seed):
        for stratum in STRATA:
            values, quality = overlay_and_round(normal, schedules[stratum].get((equipment, sample), ()), stuck[stratum])
            row = observation(equipment, sample, values, quality)
            mask = {'equipment_id': equipment, 'sample': sample, 'quality': quality}
            for name, value in zip(FILES[:2], (row, mask)):
                need(streams[stratum][name].readline() == canonical_line(value),
                     f'{stratum}/{name} bytes differ at {equipment} sample {sample}')
            missing += sum(value is None for value in values.values())
        rows += 1
    need(rows == 18000 and missing == 30, 'incomplete normal/missing inventory')
    need(all(stream.read() == b'' for files in streams.values() for stream in files.values()), 'trailing capture rows')
    return {'status': 'generation_checks_passed', 'pair_id': pair, 'role': role, 'seed': seed, 'layout': layout,
        'datasets_checked': 2, 'normal_rows_reconstructed': rows, 'observation_rows_checked': rows * 2,
        'signal_cells_checked': rows * 10, 'missing_cells_checked': missing, 'mask_rows_checked': rows * 2,
        'planned_events_checked': 80, 'enabled_events_checked': 70, 'input_sha256': expected_sha256,
        'normal_generation_verified': True, 'pre_rounding_overlay_verified': True, 'rounding_verified': True,
        'comparison': 'exact canonical UTF-8 bytes, no numeric tolerance',
        'shared_primitives': ['stdlib random.Random/gauss', 'binary64', 'builtin round', 'stdlib JSON'],
        'new_producer_evaluations': 0, 'campaign_evaluations_credited': 0,
        'independent_s6_complete': False, 'formal_permission': False, 'promotion_allowed': False,
        'performance_status': 'not_evaluated'}
