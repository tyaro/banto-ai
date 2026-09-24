"""Independent hand checks + nonregistered-seed differential fixtures only."""
import ast
import copy
import hashlib
import inspect
import json
import math
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as registry
from banto_ai import anomaly_v03_generation_audit as audit
from banto_ai import anomaly_v03_materializer as producer
from banto_ai import generator

SEED = 123456  # Never instantiate a registered dev/smoke/holdout RNG in CI.


def digests(captures):
    return {s: {n: hashlib.sha256(raw).hexdigest() for n, raw in files.items()} for s, files in captures.items()}


def fixture():
    original = registry.evaluation_inventory('dev')[0]
    pair = audit.coordinate('dev', SEED, 0)
    events, captures, stuck = {}, {}, {s: {} for s in audit.STRATA}
    for s in audit.STRATA:
        identity = producer.identity_for(original, s)
        raw = json.dumps(registry.event_inventory(identity)).replace(original['pair_id'], pair)
        events[s] = json.loads(raw)
        captures[s] = {n: bytearray() for n in audit.FILES[:2]}
        captures[s]['event-ledger.jsonl'] = producer.jsonl(events[s])
        captures[s]['events.jsonl'] = producer.jsonl(e for e in events[s] if e['enabled'])
    for equipment, sample, values in producer.normal_stream(SEED):
        kind = 'motor' if equipment == 'motor-01' else 'conveyor'
        mode = (sample % 180) // 30
        for s in audit.STRATA:
            output, quality = producer.overlay_sample(values, equipment, sample, events[s], stuck[s])
            row = {'equipment_id': equipment, 'equipment_type': kind,
                'timestamp': f'2026-01-01T{sample//3600:02d}:{sample//60%60:02d}:{sample%60:02d}.000Z',
                'operating_mode': audit.MODES[mode], 'recipe_step': audit.RECIPES[mode],
                'signals': {name: {'value': output[name], 'unit': generator._unit(kind, name)} for name in audit.SIGNALS},
                'quality': quality}
            captures[s]['observations.jsonl'].extend(producer.json_bytes(row))
            captures[s]['quality-mask.jsonl'].extend(producer.json_bytes({'equipment_id': equipment, 'sample': sample, 'quality': quality}))
    return {s: {n: bytes(raw) for n, raw in files.items()} for s, files in captures.items()}


class GenerationPrimitiveTests(unittest.TestCase):
    def test_consumer_imports_only_stdlib(self):
        tree = ast.parse(inspect.getsource(audit))
        allowed = {'__future__', 'hashlib', 'io', 'json', 'math', 'random'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(a.name in allowed for a in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertIn(node.module, allowed)

    def test_scripted_draw_order_and_hand_arithmetic(self):
        class Scripted:
            def __init__(self):
                self.calls = []
                self.values = iter((.1, -.2, .03, -.04, .5))
            def gauss(self, mean, sigma):
                self.calls.append((mean, sigma))
                return next(self.values)
        for ei, sigmas, current, speed in ((0, (.08,.4,.025,.025,.45), 10.275, 69.8),
                (1, (.004,.06,.025,.025,.45), 5.675, 1.36)):
            rng = Scripted()
            row = audit.normal_step(ei, 3, 24., rng)
            self.assertEqual(rng.calls, [(0., s) for s in sigmas])
            self.assertAlmostEqual(row['motor_current'], current)
            self.assertAlmostEqual(row['conveyor_speed'], speed)
            self.assertAlmostEqual(row['motor_temperature'], 24. + (current * .48 + 55 * .025) * .12 + .03)
            self.assertAlmostEqual(row['vibration_feature'], 1.555)
            self.assertEqual(row['load_proxy'], 55.5)

    def test_shared_rng_equipment_reset_and_unrounded_latent_carry(self):
        token, seen, previous = object(), [], [24.]
        def step(ei, mode, temperature, rng):
            self.assertIs(rng, token)
            if len(seen) % 9000 == 0:
                self.assertEqual(temperature, 24.)
            else:
                self.assertEqual(temperature, previous[0])
            seen.append((ei, mode))
            previous[0] = temperature + .00000049
            return dict.fromkeys(audit.SIGNALS, previous[0])
        with patch.object(audit.random, 'Random', return_value=token) as random, patch.object(audit, 'normal_step', side_effect=step):
            rows = list(audit.normal_rows(SEED))
        random.assert_called_once_with(SEED)
        self.assertEqual(len(rows), 18000)
        self.assertEqual(rows[9000][:2], ('conveyor-01', 0))
        self.assertEqual(seen[29:31], [(0,0), (0,1)])
        self.assertEqual(seen[8999:9001], [(0,5), (1,0)])

    def test_all_layout_schedules_against_registered_metadata_without_rng(self):
        with patch.object(audit.random, 'Random', side_effect=AssertionError('no registered seed computation')):
            for role in ('dev', 'smoke'):
                seen = set()
                for identity in registry.evaluation_inventory(role):
                    key = (identity['layout'], identity['stratum'])
                    if key in seen:
                        continue
                    seen.add(key)
                    events = audit.event_schedule(role, identity['seed'], *key)
                    self.assertEqual(events, registry.event_inventory(identity))
                    index = audit.event_index(events)
                    quality, sensor = events[-2], events[-3]
                    self.assertEqual(quality['start_sample'], sensor['start_sample'] + 1)
                    for event in events:
                        self.assertNotIn(event, index.get((event['equipment'], event['end_sample']), []))
                self.assertEqual(len(seen), 24)

    def test_overlay_order_raw_capture_and_normal_unchanged(self):
        normal = dict.fromkeys(audit.SIGNALS, 1.0000014)
        events = audit.event_schedule('dev', SEED, 0, 'quality-stress')[:4]
        before, stuck = normal.copy(), {}
        values, quality = audit.overlay_and_round(normal, list(reversed(events)), stuck)
        self.assertEqual(values['motor_current'], .450001)
        self.assertEqual(values['vibration_feature'], 2.100001)
        self.assertIsNone(values['motor_temperature'])
        self.assertEqual(quality['motor_temperature'], 'missing')
        self.assertEqual(stuck[(events[3]['event_id'], 'load_proxy')], 1.0000014 + .55 * 35.)
        self.assertEqual(normal, before)
        other = dict.fromkeys(audit.SIGNALS, 2.)
        held, _ = audit.overlay_and_round(other, events, stuck)
        self.assertEqual(held['load_proxy'], values['load_proxy'])

    def test_spike_rounding_and_clamps(self):
        normal = dict.fromkeys(audit.SIGNALS, 1.)
        normal['motor_temperature'] = 24.123456789
        events = audit.event_schedule('dev', SEED, 0, 'core')
        values, _ = audit.overlay_and_round(normal, [events[1]], {})
        self.assertEqual(values['motor_temperature'], 32.123457)
        normal['motor_current'], normal['load_proxy'] = -1., 99.
        values, _ = audit.overlay_and_round(normal, [events[0]], {})
        self.assertEqual(values['motor_current'], 0.)
        self.assertEqual(values['load_proxy'], 100.)

    def test_binary64_ties_and_signed_zero(self):
        normal = dict.fromkeys(audit.SIGNALS, .0078125)
        normal['motor_temperature'], normal['load_proxy'] = .0234375, -.0000004
        values, quality = audit.overlay_and_round(normal, [], {})
        self.assertEqual(values['motor_current'], .007812)
        self.assertEqual(values['motor_temperature'], .023438)
        self.assertEqual(math.copysign(1., values['load_proxy']), -1.)
        self.assertIn(b'"value":-0.0', audit.canonical_line(audit.observation('motor-01', 0, values, quality)))

    def test_bad_normal_rejected_even_if_masked(self):
        event = audit.event_schedule('dev', SEED, 0, 'quality-stress')[2]
        for value in (None, True, float('nan'), float('inf')):
            normal = dict.fromkeys(audit.SIGNALS, 1.)
            normal['motor_temperature'] = value
            with self.assertRaisesRegex(ValueError, 'before masking'):
                audit.overlay_and_round(normal, [event], {})


class GenerationCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.captures = fixture()
        cls.hashes = digests(cls.captures)

    @classmethod
    def tearDownClass(cls):
        del cls.captures, cls.hashes

    def call(self, captures=None, hashes=None, **kwargs):
        return audit.audit_generation_pair(**({'role': 'dev', 'seed': SEED, 'layout': 0,
            'captures': captures or self.captures, 'expected_sha256': hashes or self.hashes} | kwargs))

    def test_full_nonregistered_pair_passes_without_producer_helpers(self):
        with patch.object(producer, 'normal_stream', side_effect=AssertionError('producer called')), \
                patch.object(generator, '_base_values', side_effect=AssertionError('physics helper called')), \
                patch.object(producer, 'overlay_sample', side_effect=AssertionError('overlay helper called')):
            result = self.call()
        self.assertEqual(result['observation_rows_checked'], 36000)
        self.assertEqual(result['missing_cells_checked'], 30)
        for key in ('formal_permission', 'promotion_allowed', 'independent_s6_complete'):
            self.assertIs(result[key], False)

    def test_all_input_hashes_checked_before_rng(self):
        hashes = copy.deepcopy(self.hashes)
        hashes['quality-stress']['events.jsonl'] = 'f' * 64
        with patch.object(audit.random, 'Random', side_effect=AssertionError('too early')):
            with self.assertRaisesRegex(ValueError, 'input digest'):
                self.call(hashes=hashes)

    def test_forged_pair_with_new_hashes_still_rejected(self):
        for field in ('value', 'unit', 'load', 'timestamp', 'mask'):
            captures = {s: files.copy() for s, files in self.captures.items()}
            for s in audit.STRATA:
                name = 'quality-mask.jsonl' if field == 'mask' else 'observations.jsonl'
                line, rest = captures[s][name].split(b'\n', 1)
                row = json.loads(line)
                if field == 'value':
                    row['signals']['motor_current']['value'] += .001
                elif field == 'unit':
                    row['signals']['conveyor_speed']['unit'] = 'm/s'
                elif field == 'load':
                    row['signals']['load_proxy']['value'] += .001
                elif field == 'timestamp':
                    row['timestamp'] = '2026-01-01T00:00:01.000Z'
                else:
                    row['quality']['motor_current'] = 'missing'
                captures[s][name] = audit.canonical_line(row) + rest
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'bytes differ'):
                self.call(captures, digests(captures))

    def test_changed_ledger_or_enabled_events_rejected_before_rng(self):
        for name in ('event-ledger.jsonl', 'events.jsonl'):
            captures = {s: files.copy() for s, files in self.captures.items()}
            captures['core'][name] = captures['core'][name].replace(b'"magnitude":0.55', b'"magnitude":0.56', 1)
            with patch.object(audit.random, 'Random', side_effect=AssertionError('too early')):
                with self.assertRaisesRegex(ValueError, 'event schedule'):
                    self.call(captures, digests(captures))

    def test_extra_rows_and_noncanonical_bytes_rejected(self):
        for change in ('append', 'crlf', 'truncate'):
            captures = {s: files.copy() for s, files in self.captures.items()}
            raw = captures['core']['observations.jsonl']
            captures['core']['observations.jsonl'] = {'append': raw + b'{}\n',
                'crlf': raw.replace(b'\n', b'\r\n', 1), 'truncate': raw[:100]}[change]
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.call(captures, digests(captures))

    def test_invalid_coordinate_or_wrong_seed_rejected(self):
        for kwargs in ({'role': 'holdout'}, {'seed': True}, {'layout': True}, {'layout': 12}, {'seed': SEED+1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.call(**kwargs)


if __name__ == '__main__':
    unittest.main()
