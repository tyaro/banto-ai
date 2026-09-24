"""Independent observation -> calibrated profile -> score audit, stdlib only.

This consumer deliberately imports no producer/contract/numerical helpers.
Only complete dev/smoke captures with a healthy normal prefix are supported.
Numerically inconclusive profiles are reconstructed, not promoted to success.
The caller authenticates both input files and the registered identity. Normal
generation, pre-rounding values, episodes, CI and formal acceptance are outside
this module's scope. Existing frozen campaign audits are not changed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import statistics

EQUIPMENT = ('motor-01', 'conveyor-01')
TARGETS = ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature')
MODES = ('stopped', 'startup', 'low_speed', 'nominal', 'high_load', 'cooldown')
RECIPES = ('stop', 'start', 'low', 'run', 'load', 'cooldown')
CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
START_MS = 1767225600000
TOLERANCE = 1e-12


class NumericalInconclusive(ValueError):
    """An observed arithmetic failure; distinct from malformed input."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def need(ok, message):
    if not ok:
        raise ValueError('score audit: ' + message)


def number(value):
    need(type(value) in (int, float), 'nonnumeric arithmetic')
    try:
        if not math.isfinite(value):
            raise NumericalInconclusive('nonfinite')
    except OverflowError as exc:
        raise NumericalInconclusive('nonfinite') from exc
    return value


def _sum(values):
    try:
        return number(math.fsum(number(v) for v in values))
    except (OverflowError, NumericalInconclusive) as exc:
        raise NumericalInconclusive('nonfinite') from exc


def reported_threshold(score, flag, limit):
    """A tolerant score comparison must never admit a contradictory saved flag."""
    if score is not None:
        number(score)
        need(score >= 0, 'negative saved score')
    need(type(flag) is bool and flag == (score is not None and score > limit), 'saved strict threshold')


def strict_json(raw):
    def pairs(entries):
        result = {}
        for key, value in entries:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def constant(_value):
        raise ValueError('score audit: nonfinite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _exact(actual, expected, path):
    need(_canonical(actual) == _canonical(expected), path + ' exact value')


def _close(actual, expected, path):
    if isinstance(expected, dict):
        need(type(actual) is dict and actual.keys() == expected.keys(), path + ' fields')
        for key in expected:
            _close(actual[key], expected[key], path + '.' + key)
    elif isinstance(expected, list):
        need(type(actual) is list and len(actual) == len(expected), path + ' length')
        for i, value in enumerate(expected):
            _close(actual[i], value, f'{path}[{i}]')
    elif type(expected) is float:
        need(type(actual) in (int, float) and math.isfinite(actual) and
             math.isclose(actual, expected, rel_tol=TOLERANCE, abs_tol=TOLERANCE), path + ' number')
    else:
        need(type(actual) is type(expected) and actual == expected, path + ' literal')


@dataclass(frozen=True, slots=True)
class Sample:
    equipment: str
    sample: int
    mode: str
    recipe: str
    values: tuple
    quality: tuple


def decode_observations(raw, expected_sha256):
    need(type(raw) is bytes and raw.endswith(b'\n') and b'\r' not in raw, 'canonical LF observations required')
    need(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}', expected_sha256), 'invalid observation digest')
    need(hashlib.sha256(raw).hexdigest() == expected_sha256, 'observation digest mismatch')
    lines = raw[:-1].split(b'\n')
    need(len(lines) == 18000, 'complete 18000-row capture required')
    answer = []
    names = (*TARGETS, 'load_proxy')
    for index, line in enumerate(lines):
        row = strict_json(line)
        need(type(row) is dict and set(row) == {'timestamp', 'equipment_id', 'equipment_type', 'operating_mode', 'recipe_step', 'signals', 'quality'}, 'observation fields')
        need(_canonical(row).encode() == line, 'noncanonical observation')
        equipment, sample = EQUIPMENT[index // 9000], index % 9000
        need(row['equipment_id'] == equipment and row['equipment_type'] == ('motor', 'conveyor')[index // 9000], 'equipment/order')
        timestamp = row['timestamp']
        need(type(timestamp) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z', timestamp), 'timestamp syntax')
        delta = datetime.fromisoformat(timestamp) - datetime(2026, 1, 1, tzinfo=timezone.utc)
        need(delta.days * 86400 + delta.seconds == sample, 'missing/duplicate/reordered sample')
        need(row['operating_mode'] in MODES and row['recipe_step'] == RECIPES[MODES.index(row['operating_mode'])], 'mode/recipe')
        need(type(row['signals']) is dict and type(row['quality']) is dict and set(row['signals']) == set(row['quality']) == set(names), 'signal/quality fields')
        for name in names:
            cell = row['signals'][name]
            need(type(cell) is dict and set(cell) == {'value', 'unit'} and type(cell['unit']) is str, 'signal cell')
            value = cell['value']
            if value is not None:
                number(value)
                need(value == round(float(value), 6), 'saved precision')
            need(row['quality'][name] in ('ok', 'missing', 'stale', 'invalid'), 'quality label')
        answer.append(Sample(equipment, sample, row['operating_mode'], row['recipe_step'],
                             tuple(row['signals'][t]['value'] for t in TARGETS), tuple(row['quality'][t] for t in TARGETS)))
    return answer


def phase_rows(observations):
    """Derive phase from observed transitions; no sample modulo for test phase."""
    previous, entry = {}, {}
    for row in observations:
        old = previous.get(row.equipment)
        if old is None or row.sample != old.sample + 1:
            entry[row.equipment] = None
        elif row.mode != old.mode:
            entry[row.equipment] = row.sample
        elif row.recipe != old.recipe:
            entry[row.equipment] = None
        start = entry.get(row.equipment)
        phase = row.sample - start if start is not None and 0 <= row.sample-start < 30 else None
        previous[row.equipment] = row
        yield row, old, phase


def exclusions(candidate, row, previous, phase, target):
    bad = lambda obs, i: obs.quality[i] != 'ok' or obs.values[i] is None
    conditions = [
        ('current_target_quality', row.quality[target] != 'ok'),
        ('current_nonfinite', row.values[target] is None),
        ('no_previous_or_gap', previous is None or row.sample != previous.sample + 1),
        ('previous_target_quality_or_nonfinite', previous is not None and bad(previous, target)),
        ('mode_recipe_or_phase', phase in (None, 0) or previous is None or (previous.mode, previous.recipe) != (row.mode, row.recipe)),
        ('peer_quality_or_nonfinite', candidate == CANDIDATES[2] and any(bad(obs, i) for obs in (previous, row) if obs is not None for i in range(4) if i != target)),
    ]
    return [name for name, active in conditions if active]


def center_scale(values):
    values = [number(v) for v in values]
    if not values:
        raise NumericalInconclusive('insufficient_points')
    center = number(float(statistics.median(values)))
    scale = number(1.4826 * statistics.median(number(abs(v-center)) for v in values))
    if scale <= 0:
        raise NumericalInconclusive('zero_scale')
    return center, scale


def inverse(matrix):
    """Independent pivoted Gauss-Jordan inversion, not producer Cholesky code."""
    need(len(matrix) == 4 and all(len(row) == 4 for row in matrix), 'matrix dimensions')
    need(all(number(matrix[i][j]) == matrix[j][i] for i in range(4) for j in range(4)), 'matrix symmetry')
    work = [list(row) + [float(i == j) for j in range(4)] for i, row in enumerate(matrix)]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda i: abs(work[i][column]))
        if work[pivot][column] == 0:
            raise NumericalInconclusive('cholesky_failure')
        work[column], work[pivot] = work[pivot], work[column]
        divisor = work[column][column]
        work[column] = [number(v/divisor) for v in work[column]]
        for i in range(4):
            if i != column:
                factor = work[i][column]
                work[i] = [number(a-factor*b) for a, b in zip(work[i], work[column])]
    result = [row[4:] for row in work]
    if any(result[i][i] <= 0 for i in range(4)):
        raise NumericalInconclusive('cholesky_failure')
    return result


def conditional_state(errors):
    need(len(errors) == 580 and all(len(row) == 4 for row in errors), '580 fit vectors required')
    pairs = [center_scale([row[j] for row in errors]) for j in range(4)]
    centers, scales = [p[0] for p in pairs], [p[1] for p in pairs]
    vectors = [[number((row[j]-centers[j])/scales[j]) for j in range(4)] for row in errors]
    mean = [number(_sum(row[j] for row in vectors)/580) for j in range(4)]
    covariance = []
    for i in range(4):
        line = []
        for j in range(4):
            sample = number(_sum((row[i]-mean[i])*(row[j]-mean[j]) for row in vectors)/579)
            line.append(number(.75*sample + (.25*sample if i == j else 0.)))
        covariance.append(line)
    return dict(centers=centers, scales=scales, mean=mean, covariance=covariance, precision=inverse(covariance))


def residual(candidate, current, previous, phase, bank, target):
    if candidate == CANDIDATES[0]:
        return number(current.values[target] - previous.values[target])
    own = [bank[current.equipment, current.mode, i] for i in range(4)]
    if candidate == CANDIDATES[1]:
        return number(current.values[target] - own[target]['phase_medians'][phase])
    state = own[target]['c2_state']
    standardized = [number((current.values[j]-own[j]['phase_medians'][phase]-state['centers'][j])/state['scales'][j]-state['mean'][j]) for j in range(4)]
    return number(_sum(state['precision'][target][j]*standardized[j] for j in range(4))/math.sqrt(state['precision'][target][target]))


def rebuild_profiles(identity, phased):
    candidate = identity['candidate_id']
    normal = [p for p in phased if 1800 <= p[0].sample < 7200]
    need(len(normal) == 10800, 'normal prefix coverage')
    for row, _, phase in normal:
        need(row.mode == MODES[(row.sample % 180)//30] and phase == row.sample % 30, 'normal phase schedule')
        need(all(q == 'ok' for q in row.quality) and all(v is not None for v in row.values), 'normal prefix quality')
    bank = {}
    for equipment in EQUIPMENT:
        for mode in MODES:
            subset = [p for p in normal if p[0].equipment == equipment and p[0].mode == mode]
            fit = [p for p in subset if p[0].sample < 5400]
            for i, target in enumerate(TARGETS):
                medians, reason = None, None
                if candidate != CANDIDATES[0]:
                    buckets = [[p[0].values[i] for p in fit if p[2] == u] for u in range(30)]
                    need(all(len(b) == 20 for b in buckets), 'phase fit coverage')
                    try:
                        medians = [number(float(statistics.median(b))) for b in buckets]
                    except (NumericalInconclusive, OverflowError) as exc:
                        reason = exc.reason if isinstance(exc, NumericalInconclusive) else 'nonfinite'
                bank[equipment, mode, i] = {'profile_id': f"{identity['evaluation_id']}-profile-{equipment}-{target}-{mode}",
                    'identity': dict(identity), 'profile_version': '0.3', 'equipment': equipment,
                    'full_target': equipment+'.'+target, 'mode': mode, 'recipe': RECIPES[MODES.index(mode)],
                    'status': 'inconclusive', 'reason': reason, 'fit_samples': [] if candidate == CANDIDATES[0] else [p[0].sample for p in fit],
                    'calibration_samples': [], 'planned_calibration_points': 290, 'minimum_calibration_points': 250,
                    'phase_medians': medians, 'c2_state': None, 'center': None, 'scale': None}
            if candidate == CANDIDATES[2]:
                reason = next((bank[equipment, mode, i]['reason'] for i in range(4) if bank[equipment, mode, i]['reason']), None)
                state = None
                if reason is None:
                    try:
                        errors = [[number(p[0].values[i]-bank[equipment, mode, i]['phase_medians'][p[2]]) for i in range(4)] for p in fit if not exclusions(candidate, *p, 0)]
                        state = conditional_state(errors)
                    except (NumericalInconclusive, OverflowError) as exc:
                        reason = exc.reason if isinstance(exc, NumericalInconclusive) else 'nonfinite'
                for i in range(4):
                    bank[equipment, mode, i]['c2_state'] = state
                    bank[equipment, mode, i]['reason'] = reason
            for i in range(4):
                profile = bank[equipment, mode, i]
                if profile['reason'] is not None:
                    continue
                calibration = [p for p in subset if p[0].sample >= 5400 and not exclusions(candidate, *p, i)]
                need(len(calibration) == 290, 'complete calibration required')
                values = []
                try:
                    for p in calibration:
                        values.append(residual(candidate, *p, bank, i))
                        profile['calibration_samples'].append(p[0].sample)
                    profile['center'], profile['scale'] = center_scale(values)
                    profile['status'] = 'calibrated'
                except (NumericalInconclusive, OverflowError) as exc:
                    profile['reason'] = exc.reason if isinstance(exc, NumericalInconclusive) else 'nonfinite'
    return bank


def _identity(identity):
    need(type(identity) is dict and set(identity) == {'role', 'seed', 'layout', 'stratum', 'candidate_id', 'pair_id', 'dataset_id', 'evaluation_id'}, 'identity fields')
    need(identity['role'] in ('dev', 'smoke'), 'dev/smoke only; holdout unsupported')
    need(type(identity['seed']) is int and 0 <= identity['seed'] < 2**63 and type(identity['layout']) is int and 0 <= identity['layout'] < 12, 'seed/layout')
    need(identity['stratum'] in ('core', 'quality-stress') and identity['candidate_id'] in CANDIDATES, 'candidate/stratum')
    pair = f"anomaly-v03-{identity['role']}-seed-{identity['seed']}-layout-{identity['layout']:02d}"
    dataset = pair + '-' + identity['stratum']
    need((identity['pair_id'], identity['dataset_id'], identity['evaluation_id']) == (pair, dataset, dataset+'-'+identity['candidate_id']), 'identity binding')


def audit_score_derivation(result, observation_bytes, *, expected_observation_sha256):
    """Rebuild every profile and test score; no inference from saved fit state."""
    identity = result['identity']
    _identity(identity)
    need(result['input_hashes']['observations'] == expected_observation_sha256, 'result observation binding')
    phased = list(phase_rows(decode_observations(observation_bytes, expected_observation_sha256)))
    bank = rebuild_profiles(identity, phased)
    expected_profiles = [bank[e, m, i] for e in EQUIPMENT for i in range(4) for m in MODES]
    _close(result['profiles'], expected_profiles, 'profiles')
    scores = result['scores']
    need(type(scores) is list and len(scores) == 14400, '14400 score rows required')
    available, cursor = 0, 0
    candidate = identity['candidate_id']
    for row, previous, phase in phased:
        if row.sample < 7200:
            continue
        for i, target in enumerate(TARGETS):
            profile = bank[row.equipment, row.mode, i]
            tags = exclusions(candidate, row, previous, phase, i)
            if profile['status'] != 'calibrated':
                tags.append('profile_inconclusive')
            h = z = None
            if not tags:
                try:
                    h = residual(candidate, row, previous, phase, bank, i)
                    z = number(abs(h-profile['center'])/profile['scale'])
                except (NumericalInconclusive, OverflowError, ZeroDivisionError):
                    tags.append('nonfinite_score')
                    h = z = None
            dependencies = [{'full_target': row.equipment+'.'+TARGETS[j], 'sample': obs.sample,
                             'timestamp_ms': START_MS+obs.sample*1000, 'quality': obs.quality[j], 'value': obs.values[j]}
                            for j in (range(4) if candidate == CANDIDATES[2] else (i,))
                            for obs in (previous, row) if obs is not None and obs.sample in (row.sample-1, row.sample)]
            expected = {'candidate_id': candidate, 'sample': row.sample, 'timestamp_ms': START_MS+row.sample*1000,
                'phase': phase, 'equipment': row.equipment, 'full_target': row.equipment+'.'+target, 'mode': row.mode,
                'recipe': row.recipe, 'residual': h, 'score': z, 'available': not tags, 'exclusion_reason': tags[0] if tags else None,
                'exclusion_tags': tags, 'threshold_exceeded': z is not None and z > (4. if candidate == CANDIDATES[0] else 6.),
                'score_id': f"{identity['evaluation_id']}-score-{row.equipment}-{target}-{row.sample:04d}",
                'dataset_id': identity['dataset_id'], 'profile_id': profile['profile_id']}
            actual = scores[cursor]
            need(type(actual) is dict and set(actual) == set(expected) | {'dependencies', 'streak', 'source_episode_id'}, 'score fields')
            reported_threshold(actual['score'], actual['threshold_exceeded'], 4. if candidate == CANDIDATES[0] else 6.)
            _close({key: actual[key] for key in expected}, expected, f'scores[{cursor}]')
            _exact(actual['dependencies'], dependencies, f'scores[{cursor}].dependencies')
            available += int(not tags)
            cursor += 1
    inconclusive = [p for p in expected_profiles if p['status'] == 'inconclusive']
    return {'status': 'observation_profile_score_checks_passed', 'identity': dict(identity),
            'evaluation_outcome': 'inconclusive' if inconclusive else 'success',
            'inconclusive_profiles': [{'profile_id': p['profile_id'], 'reason': p['reason']} for p in inconclusive],
            'observation_rows': len(phased), 'profiles_checked': 48, 'score_rows_checked': cursor,
            'available_score_rows': available, 'score_derivation_verified': True,
            'profile_derivation_verified': True, 'normal_generation_verified': False,
            'pre_rounding_overlay_verified': False, 'independent_s6_complete': False,
            'formal_permission': False, 'promotion_allowed': False, 'performance_status': 'not_evaluated',
            'numeric_tolerance': {'relative': TOLERANCE, 'absolute': TOLERANCE},
            'limits': ['complete dev/smoke captures with healthy normal prefix only', 'caller authenticates identity and both files',
                       'streak/episodes/matching/metrics require the separate ledger audit', 'no generation, CI or formal gate verification']}
