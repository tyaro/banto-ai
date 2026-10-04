"""The opt-in six-row wall remains partial, pinned, and fail closed."""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_saved_row_bridge as bridge
from banto_ai import anomaly_v03_preformal_campaign_wall_row_envelope as row_wall
from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage
from tests import test_anomaly_v03_preformal_campaign_saved_row_bridge as bridge_fixture
from tests.test_anomaly_v03_preformal_campaign_metadata import Journal


fixture = bridge_fixture.fixture


def pin(raw):
    return metadata.pin(raw)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def saved_inputs():
    args, pins, _ = fixture(real_coverage=True)
    plan = v.strict_json(args[0])
    record = v.strict_json(args[1][1])
    campaign = PureWindowsPath(plan['root'])
    controls = campaign.parent / (
        'anomaly-v03-preformal-campaign-control-' +
        campaign.name[-8:])
    attempt = PureWindowsPath(record['attempt_root'])
    code = attempt.name.removeprefix(metadata.ATTEMPT_PREFIX)
    reread = attempt.parent / ('anomaly-v03-preformal-saved-row-reread-' + code)
    manifest = attempt.parent / (
        'anomaly-v03-preformal-generated-pinsets-' + code) / 'pins.json'
    entry = args[4]
    paths = {
        'result': reread / 'result.json',
        'rows': reread / 'rows.json',
        'budget': reread / 'resource-budget.json',
        'supervision': reread / 'owned-reader/supervision.json',
        'stdout': reread / 'owned-reader/worker/report.json',
        'manifest': manifest,
        'receipt': attempt / 'saved/receipt.json',
        'report': attempt / 'saved/report.json',
        'savepoint': attempt / 'saved/savepoint.json',
        'outer': attempt / 'owned-generator/result.json',
    }
    raw = {
        str(campaign / 'plan.json'): args[0],
        str(campaign / 'journal/000001.json'): args[1][0],
        str(campaign / 'journal/000002.json'): args[1][1],
        str(controls / 'checkpoint-000001.json'): args[2],
        str(controls / 'checkpoint-000002.json'): args[3],
        str(campaign / 'control/000-1/run-budget/receipt.json'):
            pins['generation_receipt_raw'],
        str(campaign / 'control/000-1/saved-reread/receipt.json'):
            pins['saved_reread_receipt_raw'],
        **{str(path): entry[name + '_raw'] for name, path in paths.items()},
    }
    expected = {
        'expected_plan_pin': pins['expected_plan_pin'],
        'expected_started_record_pin': pin(args[1][0]),
        'expected_completed_record_pin': pin(args[1][1]),
        'expected_started_checkpoint_pin':
            pins['expected_started_checkpoint_pin'],
        'expected_terminal_checkpoint_pin':
            pins['expected_terminal_checkpoint_pin'],
        'expected_generation_receipt_pin': pin(pins['generation_receipt_raw']),
        'expected_reread_receipt_pin': pin(pins['saved_reread_receipt_raw']),
    }
    return campaign, controls, raw, expected, paths


def bind_fixture(campaign, controls, **expected):
    # The retained fixture records Windows paths even when unittest runs on
    # Ubuntu. Keep its lexical path checks in that same flavor; all reads are
    # supplied by the pinned-raw fake below.
    with patch.object(row_wall, 'Path', PureWindowsPath), \
            patch.object(row_wall, 'ROOT', campaign.parent.parent):
        return row_wall.bind_retained(campaign, controls, **expected)


def fake_pinned(raws):
    def read(path, expected_pin, maximum):
        raw = raws[str(path)]
        v.require(len(raw) <= maximum and pin(raw) == expected_pin,
                  'externally pinned retained raw')
        return raw
    return read


def campaign_child_fixture(*, wrong_anchor=False, wrong_source=False,
                           rogue_path=False, duplicate_path=False,
                           wrong_scope=False):
    class FullReaderJournal(Journal):
        def __init__(self):
            super().__init__()
            previous = self.plan
            rows = list(previous['source']['selected_files'])
            names = {row['path'] for row in rows}
            rows.extend({'path': name, 'pin': pin(name.encode())}
                        for name in bridge.saved_row_reread.SOURCE_FILES
                        if name not in names)
            source = {**previous['source'],
                      'selected_files': sorted(rows,
                                               key=lambda row: row['path'])}
            self.plan = metadata.fixed_plan(
                previous['campaign_id'], previous['root'],
                previous['path_code'], previous['registry_pin'], source,
                previous['runtime_candidate'], previous['budget_candidate'])
            self.plan_raw = metadata.encode_plan(self.plan)
            self.plan_pin = pin(self.plan_raw)

    with patch.object(bridge_fixture, 'Journal', FullReaderJournal):
        args, pins, _ = fixture(real_coverage=True)
    entry = args[4]
    plan = v.strict_json(args[0])
    stdout = v.strict_json(entry['stdout_raw'])
    stdout['format'] = coverage.CAMPAIGN_CHILD_FORMAT
    stdout['campaign_context'] = {
        'plan_path': str(PureWindowsPath(plan['root']) / 'plan.json'),
        'anchor_pin': pin(b'wrong') if wrong_anchor else pins['expected_plan_pin'],
        'chunk_index': 0, 'attempt': 1,
    }
    child_source = {
        'revision': plan['source']['revision'],
        'selected_files': [
            {'path': name,
             'pin': next(row['pin'] for row in plan['source']['selected_files']
                         if row['path'] == name)}
            for name in bridge.saved_row_reread.SOURCE_FILES],
        'scope': ('wrong-scope' if wrong_scope else plan['source']['scope']),
    }
    if wrong_source:
        child_source['selected_files'][0] = {
            **child_source['selected_files'][0], 'pin': pin(b'wrong source')}
    if rogue_path:
        child_source['selected_files'].append({
            'path': 'src/banto_ai/rogue.py', 'pin': pin(b'rogue')})
    if duplicate_path:
        child_source['selected_files'].append(
            dict(child_source['selected_files'][0]))
    stdout['source'] = child_source
    entry['stdout_raw'] = v.canonical_json(stdout) + b'\n'
    entry['expected_pins']['stdout'] = pin(entry['stdout_raw'])
    supervision = v.strict_json(entry['supervision_raw'])
    supervision['output'] = entry['expected_pins']['stdout']
    entry['supervision_raw'] = v.canonical_json(supervision)
    entry['expected_pins']['supervision'] = pin(entry['supervision_raw'])
    result = v.strict_json(entry['result_raw'])
    result['selected_current_source'] = child_source
    result['selected_current_source_after'] = child_source
    result['child_stdout_pin'] = entry['expected_pins']['stdout']
    result['reader_supervision_pin'] = entry['expected_pins']['supervision']
    entry['result_raw'] = v.canonical_json(result)
    entry['expected_pins']['result'] = pin(entry['result_raw'])
    record = v.strict_json(args[1][1])
    for name in ('result', 'stdout', 'supervision'):
        record['evidence_pins'][bridge.ENTRY_PINS[name]] = \
            entry['expected_pins'][name]
    args[1][1] = metadata.encode_record(record)
    owner = v.strict_json(pins['saved_reread_receipt_raw'])
    for name in ('fresh_reread_result', 'fresh_reread_stdout',
                 'fresh_reread_supervision'):
        owner['inner']['evidence_pins'][name] = record['evidence_pins'][name]
    owner['inner']['result_pin'] = entry['expected_pins']['result']
    pins['saved_reread_receipt_raw'] = v.canonical_json(owner) + b'\n'
    terminal = v.strict_json(args[3])
    terminal['saved_reread_receipt_pin'] = pin(pins['saved_reread_receipt_raw'])
    terminal['completed_record_pin'] = pin(args[1][1])
    terminal['head_sha256'] = terminal['completed_record_pin']['sha256']
    args[3] = v.canonical_json(terminal) + b'\n'
    pins['expected_terminal_checkpoint_pin'] = pin(args[3])
    return args, pins


class RetainedBindingTests(unittest.TestCase):
    def test_campaign_child_v2_binds_context_and_overlapping_source_pins(self):
        args, pins = campaign_child_fixture()
        source_path = bridge.saved_row_reread.SOURCE_FILES[0]
        result = bridge.bind_completed_saved_rows(*args, **pins)
        self.assertEqual(result['verified_evaluations'], 6)
        for kwargs in ({'wrong_anchor': True}, {'wrong_source': True},
                       {'rogue_path': True}, {'duplicate_path': True},
                       {'wrong_scope': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                args, pins = campaign_child_fixture(**kwargs)
                bridge.bind_completed_saved_rows(*args, **pins)
        args, pins = campaign_child_fixture(rogue_path=True)
        # Even a path listed in the hypothetical reader set cannot be absent
        # from the externally pinned plan's selected source inventory.
        with patch.object(bridge.saved_row_reread, 'SOURCE_FILES',
                          (*bridge.saved_row_reread.SOURCE_FILES,
                           'src/banto_ai/rogue.py')), \
                self.assertRaisesRegex(ValueError,
                                        'exact source pins match plan'):
            bridge.bind_completed_saved_rows(*args, **pins)

    def test_two_journal_records_and_ten_saved_raws_are_bound(self):
        campaign, controls, raws, expected, paths = saved_inputs()
        with patch.object(row_wall.store, '_pinned',
                          side_effect=fake_pinned(raws)) as reader:
            result, source_pins = bind_fixture(
                campaign, controls, **expected)
        self.assertEqual(result['status'],
                         'partial_saved_row_journal_link_only')
        self.assertEqual(result['verified_evaluations'], 6)
        self.assertEqual(set(source_pins), set(paths))
        self.assertGreaterEqual(reader.call_count, 34)
        self.assertFalse(result['formal_permission'])

    def test_journal_or_saved_raw_mutation_rejected_before_bridge(self):
        campaign, controls, raws, expected, paths = saved_inputs()
        for path in (campaign / 'journal/000002.json', paths['rows'],
                     paths['stdout']):
            changed = dict(raws)
            changed[str(path)] += b' '
            with self.subTest(path=path), patch.object(
                    row_wall.store, '_pinned',
                    side_effect=fake_pinned(changed)), \
                    patch.object(row_wall.bridge,
                                 'bind_completed_saved_rows') as binder:
                with self.assertRaises(ValueError):
                    bind_fixture(campaign, controls, **expected)
                binder.assert_not_called()

    def test_completed_attempt_root_cannot_move_to_latest_attempt_two(self):
        campaign, controls, raws, expected, _ = saved_inputs()
        changed = dict(raws)
        path = str(campaign / 'journal/000002.json')
        record = v.strict_json(changed[path])
        record['attempt_root'] = record['attempt_root'][:-1] + '2'
        changed[path] = metadata.encode_record(record)
        altered = dict(expected, expected_completed_record_pin=pin(changed[path]))
        with patch.object(row_wall.store, '_pinned',
                          side_effect=fake_pinned(changed)), \
                patch.object(row_wall.bridge,
                             'bind_completed_saved_rows') as binder:
            with self.assertRaisesRegex(ValueError, 'latest slot-0 attempt'):
                bind_fixture(campaign, controls, **altered)
            binder.assert_not_called()

    def test_bridge_rejects_latest_attempt_and_six_identity_changes(self):
        args, pins, covered = fixture()
        altered = dict(covered)
        altered['chunks'] = [dict(covered['chunks'][0], latest_attempt=2)]
        with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                          return_value=altered), self.assertRaises(ValueError):
            bridge.bind_completed_saved_rows(*args, **pins)
        args[4]['rows_raw'] = v.canonical_json({'rows': [
            {'identity': identity} for identity in
            v.evaluation_inventory('holdout')[6:12]]})
        with patch.object(bridge.coverage, 'collect_saved_row_coverage',
                          return_value=covered), self.assertRaises(ValueError):
            bridge.bind_completed_saved_rows(*args, **pins)


class OuterWallTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        artifacts = self.root / 'artifacts'
        artifacts.mkdir()
        self.campaign = artifacts / 'anomaly-v03-preformal-campaign-aaaaaaaa'
        self.controls = artifacts / 'anomaly-v03-preformal-campaign-control-aaaaaaaa'
        self.campaign.mkdir()
        self.controls.mkdir()
        self.clock = Clock()
        self.plan_pin = pin(b'plan')
        self.checkpoint_pin = pin(b'checkpoint')
        self.intention_pin = pin(b'intention')
        self.inner_pin = pin(b'inner')
        self.evidence = {name: pin(name.encode()) for name in (
            'started_record_pin', 'completed_record_pin',
            'next_checkpoint_pin', 'terminal_checkpoint_pin',
            'generation_receipt_pin', 'reread_receipt_pin')}
        self.source_pins = {name: pin(name.encode())
                            for name in row_wall.RAW_NAMES}

    def run_envelope(self, wall_seconds=10):
        with patch.object(row_wall, 'ROOT', self.root):
            return row_wall.execute(
                self.campaign, self.controls,
                expected_plan_pin=self.plan_pin,
                expected_initial_checkpoint_pin=self.checkpoint_pin,
                expected_intention_pin=self.intention_pin,
                wall_seconds=wall_seconds, clock=self.clock)

    def inner(self, *args, **kwargs):
        self.assertEqual(kwargs['wall_seconds'], 10)
        self.clock.now += 4
        return {'status': 'verified', 'evidence_pins': self.evidence}, self.inner_pin

    def binder(self, *args, **kwargs):
        self.assertEqual(kwargs['expected_completed_record_pin'],
                         self.evidence['completed_record_pin'])
        self.clock.now += 2
        return {'status': 'partial_saved_row_journal_link_only',
                'verified_chunks': 1, 'verified_evaluations': 6,
                'campaign_evaluations_credited': 0,
                'formal_permission': False}, self.source_pins

    def test_one_outer_wall_records_inner_and_ten_raw_pins_without_credit(self):
        with patch.object(row_wall.wall, 'execute', side_effect=self.inner), \
                patch.object(row_wall, 'bind_retained',
                             side_effect=self.binder):
            receipt, receipt_pin = self.run_envelope()
        self.assertEqual((receipt['status'], receipt['elapsed_seconds']),
                         ('verified', 6.0))
        self.assertEqual(receipt['inner_wall_receipt_pin'], self.inner_pin)
        self.assertEqual(receipt['saved_row_raw_pins'], self.source_pins)
        self.assertFalse(receipt['full_end_to_end_budget_measured'])
        self.assertEqual(receipt['campaign_evaluations_credited'], 0)
        outer = self.root / 'artifacts/anomaly-v03-preformal-campaign-wall-row-aaaaaaaa'
        self.assertEqual(pin((outer / 'receipt.json').read_bytes()), receipt_pin)
        self.assertEqual(set(path.name for path in outer.iterdir()),
                         {'claim.json', 'bridge-result.json', 'receipt.json'})
        with patch.object(row_wall, 'ROOT', self.root), \
                self.assertRaisesRegex(ValueError, 'fresh wall row'):
            self.run_envelope()

    def test_wall_expiry_after_inner_stops_before_row_reads_and_retains_receipt(self):
        def expired(*args, **kwargs):
            self.clock.now += 10
            return {'status': 'verified', 'evidence_pins': self.evidence}, self.inner_pin
        with patch.object(row_wall.wall, 'execute', side_effect=expired), \
                patch.object(row_wall, 'bind_retained') as binder:
            receipt, receipt_pin = self.run_envelope()
        binder.assert_not_called()
        self.assertEqual((receipt['status'], receipt['reason']),
                         ('failed', 'shared_wall_expired'))
        self.assertEqual(receipt['inner_wall_receipt_pin'], self.inner_pin)
        outer = self.root / 'artifacts/anomaly-v03-preformal-campaign-wall-row-aaaaaaaa'
        self.assertEqual(pin((outer / 'receipt.json').read_bytes()), receipt_pin)
        self.assertEqual(set(path.name for path in outer.iterdir()),
                         {'claim.json', 'receipt.json'})

    def test_bridge_failure_retains_inner_pin_without_claiming_six_rows(self):
        def broken(*args, **kwargs):
            self.clock.now += 2
            raise ValueError('saved raw pin mismatch')
        with patch.object(row_wall.wall, 'execute', side_effect=self.inner), \
                patch.object(row_wall, 'bind_retained', side_effect=broken):
            receipt, _ = self.run_envelope()
        self.assertEqual((receipt['status'], receipt['last_stage'],
                          receipt['error_type']),
                         ('failed', 'saved-row-bridge', 'ValueError'))
        self.assertEqual(receipt['inner_wall_receipt_pin'], self.inner_pin)
        self.assertIsNone(receipt['bridge_result_pin'])
        self.assertEqual(receipt['campaign_evaluations_credited'], 0)

    def test_saved_verifier_rejects_inner_elapsed_beyond_outer_elapsed(self):
        with patch.object(row_wall.wall, 'execute', side_effect=self.inner), \
                patch.object(row_wall, 'bind_retained',
                             side_effect=self.binder):
            _, receipt_pin = self.run_envelope()
        fake_inner = {
            'status': 'verified_retained', 'receipt_pin': self.inner_pin,
            'elapsed_seconds': 7.0,
        }
        with patch.object(row_wall, 'ROOT', self.root), \
                patch.object(row_wall.wall, 'verify_completed',
                             return_value=fake_inner), \
                self.assertRaisesRegex(ValueError,
                                        'inner wall completion differs'):
            row_wall.verify_retained(
                self.campaign, self.controls,
                expected_receipt_pin=receipt_pin)


if __name__ == '__main__':
    unittest.main()
