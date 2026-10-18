"""CARE Farm B/C holdout logic on synthetic data (no CARE data, no model)."""
import io
import math
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'models/mini-transformer'), str(ROOT/'tools')]
import care_holdout_score as S  # noqa: E402
from care_alarm import COMMON, NATIVE  # noqa: E402
from care_training_preparation import baseline_profile, normalization, schedule  # noqa: E402


class GeneralizedPreparationTest(unittest.TestCase):
    def test_normalization_weights_each_of_k_assets_equally(self):
        pops = [[(0., 0., 0.)], [(10., 10., 10.)]*3, [(20., 20., 20.)]*9, [(30., 30., 30.)]*2]
        scales, alarm = normalization(pops)
        self.assertEqual(scales[0]['mean64'], 15.)
        self.assertTrue(math.isclose(scales[0]['variance64'], 125.))
        self.assertIn(alarm[0]['weighted_median64'], (10., 20.))

    def test_schedule_draws_over_all_train_assets(self):
        train = [('2', 12), ('5', 89), ('12', 15), ('13', 29), ('14', 85)]
        origins = {e: [128, 129] for _, e in train}
        raw, counts = schedule(train, origins)
        self.assertEqual(len(counts), 5)
        self.assertEqual(sum(counts), 4096*8)
        self.assertEqual(raw, schedule(train, origins)[0])
        self.assertTrue(all(c > 0 for c in counts))

    def test_baseline_profile_counts_k_assets(self):
        profile = baseline_profile([[(float(a), (1., 1.))]*128 for a in range(5)])
        self.assertEqual(len(profile['per_bin_asset_counts'][0]), 5)
        self.assertIn('1/(5*N_asset)', profile['weighting'])


class ClopperPearsonTest(unittest.TestCase):
    def test_known_intervals(self):
        low, high = S.clopper_pearson(3, 12)
        self.assertAlmostEqual(low, 0.0549, places=4)
        self.assertAlmostEqual(high, 0.5719, places=4)
        self.assertEqual(S.clopper_pearson(0, 10)[0], 0.)
        self.assertAlmostEqual(S.clopper_pearson(0, 10)[1], 0.3085, places=4)
        self.assertIsNone(S.clopper_pearson(0, 0))


def row(event, n, flags=COMMON | NATIVE | 1 | 8):
    """A prediction record: event, ordinal, source ID, issue, availability, flags, 2+2+2 values, 2 scores, 9 quantiles."""
    return (event, n, n, 600*n, 600*n+600, flags, 1., 1., 1., 1., 1., 1., 0., 0., *[1.]*9)


class ScoreTest(unittest.TestCase):
    """Two farms share asset ID 2: the false alarms must stay on separate assets."""

    def setUp(self):
        first = '2020-01-01T00:00:00'
        # 600 rows of 10 minutes cover 100 h, enough for an 80 h interval
        self.meta = {('B', 1): {'asset_id': '2', 'first_timestamp': first}, ('C', 1): {'asset_id': '2', 'first_timestamp': first},
                     ('C', 2): {'asset_id': '2', 'first_timestamp': first}}
        self.rows = {k: [row(1 if k[1] == 1 else 2, n) for n in range(600)] for k in self.meta}
        # anomaly interval: source IDs 0..479 -> availability 600 .. 288000 (80 h)
        end = '2020-01-04T07:50:00'
        self.truth = [{'farm': 'B', 'event_id': '1', 'event_label': 'anomaly', 'event_start': first, 'event_end': end, 'event_start_id': '0', 'event_end_id': '479'},
                      {'farm': 'C', 'event_id': '1', 'event_label': 'normal', 'event_start': first, 'event_end': end, 'event_start_id': '0', 'event_end_id': '479'},
                      {'farm': 'C', 'event_id': '2', 'event_label': 'normal', 'event_start': first, 'event_end': end, 'event_start_id': '0', 'event_end_id': '479'}]
        early = {'open': 600*10, 'close': 600*20}  # 78+ h before the end: a hit at 0, 24 and 72 h
        self.alarms = {('B', 1): {m: [early] for m in S.METHODS}, ('C', 1): {m: [] for m in S.METHODS}, ('C', 2): {m: [] for m in S.METHODS}}

    def run_score(self):
        stats, per_event, floors = S.score_events(self.truth, self.meta, self.rows, self.alarms)
        results = {m: {'pooled': S.summarize(list(stats[m].values())), 'per_asset': {k: S.summarize([s]) for k, s in stats[m].items()}} for m in S.METHODS}
        return stats, per_event, floors, results

    def test_assets_are_keyed_by_farm(self):
        stats, _, _, _ = self.run_score()
        self.assertEqual(sorted(stats['neural-common']), ['B:2', 'C:2'])
        self.assertEqual(stats['neural-common']['C:2']['normal_files'], 2)

    def test_lead_time_hits_and_pass(self):
        _, per_event, floors, results = self.run_score()
        pooled = results['neural-common']['pooled']
        self.assertEqual(pooled['hits_at'], {'0': 1, '24': 1, '72': 1, '168': 0})
        self.assertEqual(pooled['attainable_at'], {'0': 1, '24': 1, '72': 1, '168': 0})
        self.assertEqual(floors, [])
        decision = S.decide(results, floors)
        self.assertEqual(decision['outcome'], 'pass')
        self.assertFalse(per_event[0]['default_168h_interval'])

    def test_one_false_episode_on_one_asset_fails_the_per_asset_ceiling(self):
        self.alarms[('C', 1)] = {m: [{'open': 600*100, 'close': 600*110}] for m in S.METHODS}
        _, _, floors, results = self.run_score()
        decision = S.decide(results, floors)
        self.assertFalse(decision['checks']['every_asset_false_alarms_at_most_1.0_per_asset_30_days'])
        self.assertEqual(decision['outcome'], 'fail')

    def test_short_normal_asset_is_a_floor_break(self):
        self.rows[('C', 1)] = [row(1, n) for n in range(50)]  # 2 x 8.3 h of normal record time, under 24 h
        self.rows[('C', 2)] = [row(2, n) for n in range(50)]
        self.truth = self.truth[:1]+[dict(self.truth[1], event_end='2020-01-01T08:10:00', event_end_id='49'),
                                     dict(self.truth[2], event_end='2020-01-01T08:10:00', event_end_id='49')]
        _, _, floors, results = self.run_score()
        self.assertEqual(S.decide(results, floors)['outcome'], 'not established')

    def test_label_alignment_is_checked(self):
        self.truth[0]['event_end_id'] = '478'
        with self.assertRaisesRegex(ValueError, 'alignment'):
            S.score_events(self.truth, self.meta, self.rows, self.alarms)


class ArchivePinTest(unittest.TestCase):
    def test_changed_archive_stops_before_the_truth(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'a.zip'
            path.write_bytes(b'not the pinned archive')
            with mock.patch.object(S.H, 'ARCHIVE', path):
                with self.assertRaisesRegex(ValueError, 'archive differs'):
                    S.verify_archive()


def sources_zip(members):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z:
        for name, data in members.items():
            z.writestr(name, data)
    return b.getvalue()


class SameSourcesTest(unittest.TestCase):
    def test_folds_from_different_runners_are_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            roots = []
            for i, data in enumerate((b'runner', b'runner', b'changed runner')):
                root = Path(tmp)/str(i); root.mkdir(); roots.append(root)
                (root/'sources.zip').write_bytes(sources_zip({'tools/care_holdout.py': data}))
            self.assertEqual(S.same_sources(roots[:2]), S.unit_sources(roots[0]))
            with self.assertRaisesRegex(ValueError, 'different sources'):
                S.same_sources(roots)


class FrozenRootsTest(unittest.TestCase):
    """A fold, input or preparation root changed after the freeze is rejected before the truth is read."""

    def setUp(self):
        import json
        import tempfile
        from unittest import mock
        from metropt_multiday import Files, digest
        self.tmp = tempfile.TemporaryDirectory(); base = Path(self.tmp.name); self.digest = digest
        unit = base/'unit'; files = Files(unit)
        for name in ('test.bin', 'episodes.json', 'thresholds.json'):
            files.write(name, name.encode())
        files.write('sources.zip', sources_zip({'tools/care_holdout.py': b'runner'}))
        files.close('complete')
        event = base/'event'; files = Files(event); files.write('event.bin', b'rows'); files.close('complete')
        manifest = base/'manifest'; files = Files(manifest)
        files.json('dataset-manifest.json', {'files': [{'event_id': 1, 'event_root_closure_sha256': digest(event/'root-closed.json')}]}); files.close('complete')
        prep = base/'prep'; files = Files(prep); files.write('fold-0-schedule.bin', b'schedule'); files.close('complete')
        self.unit, self.event, self.manifest, self.prep = unit, event, manifest, prep
        self.frozen = {'units': [{'farm': 'B', 'fold': 0, **{k: digest(unit/n) for k, n in (('closure_sha256', 'root-closed.json'), ('test_sha256', 'test.bin'),
                                                                                         ('episodes_sha256', 'episodes.json'), ('thresholds_sha256', 'thresholds.json'))}}],
                       'input_closures': {'B': digest(manifest/'root-closed.json')}, 'preparation_closures': {'B': digest(prep/'root-closed.json')},
                       'unit_sources': S.unit_sources(unit)}
        self.patches = [mock.patch.object(S.H, 'FARMS', ('B',)), mock.patch.object(S.H, 'unit_root', lambda farm, fold: unit),
                        mock.patch.object(S.H, 'manifest_root', lambda farm: manifest), mock.patch.object(S.H, 'event_root', lambda farm, e: event),
                        mock.patch.object(S.H, 'prep_root', lambda farm: prep)]
        for p in self.patches:
            p.start()
        self.json = json

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_unchanged_roots_verify(self):
        S.verify_frozen(self.frozen)

    def test_episode_edited_after_the_freeze_is_rejected(self):
        (self.unit/'episodes.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            S.verify_frozen(self.frozen)

    def test_reclosed_fold_is_rejected(self):
        (self.unit/'episodes.json').write_bytes(b'{}')
        closed = self.json.loads((self.unit/'root-closed.json').read_bytes())
        for f in closed['files']:
            if f['name'] == 'episodes.json':
                f.update(bytes=2, sha256=self.digest(self.unit/'episodes.json'))
        (self.unit/'root-closed.json').write_text(self.json.dumps(closed))
        with self.assertRaisesRegex(ValueError, 'fold changed after the freeze'):
            S.verify_frozen(self.frozen)

    def test_input_event_or_preparation_change_is_rejected(self):
        (self.event/'event.bin').write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            S.verify_frozen(self.frozen)

    def test_changed_preparation_closure_is_rejected(self):
        frozen = dict(self.frozen, preparation_closures={'B': '0'*64})
        with self.assertRaisesRegex(ValueError, 'preparation changed'):
            S.verify_frozen(frozen)


class TruthReaderTest(unittest.TestCase):
    def test_semicolon_event_info(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w') as z:
            z.writestr('CARE_To_Compare/Wind Farm B/event_info.csv', 'event_id;event_label;event_start\n1;anomaly;2020-01-01 00:00:00\n')
        with zipfile.ZipFile(b) as z:
            self.assertEqual(S.read_truth(z, 'B'), [{'event_id': '1', 'event_label': 'anomaly', 'event_start': '2020-01-01 00:00:00'}])


if __name__ == '__main__':
    unittest.main()
