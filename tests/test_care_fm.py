"""CARE foundation-model freeze logic on synthetic rows (no CARE data, no models)."""
import math
import unittest

from tools import care_fm
from tools.care_fm import COMMON, PRED, PREDICTION


def saved(event, n, t, y=(10.0, 20.0), flags=COMMON):
    """A saved test row in the CARE r1 layout: event, origin, source ID, issue, availability, flags,
    actual 2, own p50 2, baseline p50 2, own score, baseline score, 9 quantiles."""
    return (event, n, n, t-600, t, flags, *y, 0., 0., 0., 0., 0., 0., *[0.]*9)


class AssembleTest(unittest.TestCase):
    def setUp(self):
        self.rows = [saved(1, n, 600*n) for n in range(10)]

    def pack(self, ns):
        return b''.join(PRED.pack(1, n, 10., 20.) for n in ns)

    def test_complete_chunks_assemble(self):
        out = care_fm.assemble(self.rows, [self.pack(range(0, 4)), self.pack(range(4, 10))])
        self.assertEqual(len(out), 10)

    def test_missing_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            care_fm.assemble(self.rows, [self.pack(range(0, 4)), self.pack(range(5, 10))])

    def test_duplicate_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            care_fm.assemble(self.rows, [self.pack(range(0, 5)), self.pack(range(4, 10))])

    def test_extra_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'extra'):
            care_fm.assemble(self.rows, [self.pack(range(0, 10)), PRED.pack(2, 0, 1., 1.)])


class AlarmAcrossChunksTest(unittest.TestCase):
    """Three exceedances spanning a chunk boundary must still OPEN: alarms run over whole files."""

    def setUp(self):
        self.rows = [saved(1, n, 600*n) for n in range(12)]
        high = {4, 5, 6}  # rows 4 and 5 in the first chunk of 6, row 6 in the second
        self.preds = {(1, n): (10.+(5. if n in high else 0.), 20.) for n in range(12)}
        self.R = [1., 1.]

    def test_episode_spanning_the_boundary_opens(self):
        rows = care_fm.method_rows(self.rows, self.preds, self.R)
        alarms = care_fm.episodes_by_event(rows, 1.)[1]
        self.assertEqual([a['open'] for a in alarms], [600*6])

    def test_per_chunk_scoring_would_lose_it(self):
        rows = care_fm.method_rows(self.rows, self.preds, self.R)
        per_chunk = care_fm.episodes_by_event(rows[:6], 1.)[1]+care_fm.episodes_by_event(rows[6:], 1.)[1]
        self.assertEqual(per_chunk, [])

    def test_unsupported_row_is_the_inherited_gap(self):
        preds = dict(self.preds); preds[(1, 5)] = (math.nan, math.nan)
        rows = care_fm.method_rows(self.rows, preds, self.R)
        self.assertEqual(rows[5][5] & COMMON, 0)
        self.assertEqual(care_fm.episodes_by_event(rows, 1.)[1], [])

    def test_score_uses_the_saved_observation_and_R(self):
        rows = care_fm.method_rows(self.rows, self.preds, [2., 4.])
        self.assertEqual(rows[4][12], 2.5)
        self.assertEqual(rows[0][12], 0.)
        self.assertEqual(len(rows[0]), len(PREDICTION.unpack(PREDICTION.pack(*rows[0]))))
        self.assertEqual(rows[4][8:10], (15., 20.))  # the method's own p50 in the model slots
        self.assertTrue(all(math.isnan(x) for x in rows[4][14:23]))


class PracticalScoreTest(unittest.TestCase):
    """Lead-time detection, attainability and per-asset-month false alarms on a synthetic cohort."""

    def test_lead_times_attainability_and_month_rate(self):
        from tools import care_practical_score as ps
        # rows n=1..9 are available at 600*n s; the anomaly interval covers them: start 600, end 5400
        rows = {e: [saved(e, n, 600*n) for n in range(10)] for e in (1, 2)}
        first = '2020-01-01T00:00:00'
        truth = [{'event_id': 1, 'asset_key': 'A:0', 'event_label': 'anomaly', 'event_start': first,
                  'event_end': '2020-01-01T01:20:00', 'event_start_id': 1, 'event_end_id': 9},
                 {'event_id': 2, 'asset_key': 'A:0', 'event_label': 'normal', 'event_start': first,
                  'event_end': '2020-01-01T01:20:00', 'event_start_id': 1, 'event_end_id': 9}]
        meta = {1: {'first_timestamp': first}, 2: {'first_timestamp': first}}
        alarms = {1: [{'open': 1200, 'close': 1800}], 2: [{'open': 600, 'close': 1200}]}
        methods = ('neural-common', 'timesfm3')
        results, per_event = ps.score(truth, meta, {m: rows for m in methods}, {m: alarms for m in methods})
        pooled = results['timesfm3']['pooled']
        self.assertEqual(pooled['hits_at'], {'0': 1, '24': 0, '72': 0, '168': 0})  # an 80-minute interval
        self.assertEqual(per_event[0]['attainable'], {'0': True, '24': False, '72': False, '168': False})
        self.assertEqual(per_event[0]['methods']['timesfm3']['lead_proxy_hours'], (5400-1200)/3600)
        self.assertEqual(pooled['false_episodes'], 1)
        self.assertAlmostEqual(pooled['false_episodes_per_asset_30_days'], pooled['false_episodes_per_1000_record_hours']*720/1000)


class ClosedUnitTest(unittest.TestCase):
    """Closed chunks are reused (resume) or frozen only if they verify and stayed within limits."""

    def make(self, root, method='toto2', peak=500 << 20, seconds=30.):
        import json
        d = care_fm.unit_dir(root, method, 0, 'test', 0); d.mkdir(parents=True)
        (d/'predictions.bin').write_bytes(b''.join(PRED.pack(1, n, 10., 20.) for n in range(3)))
        (d/'unit.json').write_text(json.dumps({'method': method, 'fold': 0, 'segment': 'test', 'chunk': 0, 'rows': 3,
                                               'seconds': seconds, 'peak_rss_bytes': peak,
                                               'fold_root_closure_sha256': 'f', 'dataset_closure_sha256': 'd'}))
        care_fm.close(d)
        return d

    def expected(self, method='toto2'):
        return dict(method=method, fold=0, segment='test', chunk=0, rows=3, fold_closure='f', dataset_closure='d')

    def test_good_unit_verifies(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(care_fm.check_unit(self.make(tmp), **self.expected())['rows'], 3)

    def test_changed_prediction_after_closing_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self.make(tmp)
            (d/'predictions.bin').write_bytes(b''.join(PRED.pack(1, n, 15., 20.) for n in range(3)))
            with self.assertRaisesRegex(ValueError, 'closed file differs'):
                care_fm.check_unit(d, **self.expected())

    def test_over_memory_unit_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'limit'):
                care_fm.check_unit(self.make(tmp, peak=3 << 30), **self.expected())

    def test_other_unit_or_inputs_are_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self.make(tmp)
            with self.assertRaisesRegex(ValueError, 'identity'):
                care_fm.check_unit(d, **{**self.expected(), 'chunk': 1})
            with self.assertRaisesRegex(ValueError, 'inputs'):
                care_fm.check_unit(d, **{**self.expected(), 'fold_closure': 'other'})

    def test_campaign_stops_instead_of_reusing_an_over_limit_chunk(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            self.make(tmp, peak=3 << 30)
            with mock.patch.object(care_fm, 'METHODS', ('toto2',)), mock.patch.object(care_fm, 'FOLDS', (0,)), \
                    mock.patch.object(care_fm, 'SEGMENTS', ('test',)), mock.patch.object(care_fm, 'chunks', lambda k, s: [[None]*3]), \
                    mock.patch.object(care_fm, 'expected_unit', lambda *u: self.expected()):
                with self.assertRaises(SystemExit):
                    care_fm.campaign(tmp, tmp, 1, 1)
            self.assertIn('closed chunk fails verification', (care_fm.Path(tmp)/'campaign-log.jsonl').read_text())


class EnvironmentTest(unittest.TestCase):
    """A unit runs only on the pinned package/Torch versions and the pinned checkpoint bytes."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory(); root = care_fm.Path(self.tmp.name)
        model = root/'models--x'/'snapshots'/'rev1'/'model.safetensors'; model.parent.mkdir(parents=True); model.write_bytes(b'weights')
        self.pin = {'distribution': 'pkg', 'version': '1.0', 'checkpoint': 'x', 'revision': 'rev1',
                    'model_bytes': 7, 'model_sha256': care_fm.digest(b'weights')}
        self.cache = root

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self, versions, pin=None):
        from unittest import mock
        with mock.patch.dict(care_fm.ENVIRONMENT, {'toto2': pin or self.pin}), \
                mock.patch('importlib.metadata.version', lambda name: versions[name]):
            return care_fm.verify_environment('toto2', self.cache)

    def test_pinned_environment_verifies(self):
        record = self.verify({'pkg': '1.0', 'torch': care_fm.TORCH})
        self.assertEqual(record['model_sha256'], self.pin['model_sha256'])

    def test_other_package_or_torch_version_stops(self):
        with self.assertRaisesRegex(RuntimeError, 'differ from the pins'):
            self.verify({'pkg': '1.1', 'torch': care_fm.TORCH})
        with self.assertRaisesRegex(RuntimeError, 'differ from the pins'):
            self.verify({'pkg': '1.0', 'torch': '2.15.0'})

    def test_other_checkpoint_bytes_stop(self):
        with self.assertRaisesRegex(RuntimeError, 'model.safetensors'):
            self.verify({'pkg': '1.0', 'torch': care_fm.TORCH}, {**self.pin, 'model_sha256': '0'*64})
        with self.assertRaisesRegex(RuntimeError, 'one cached snapshot'):
            self.verify({'pkg': '1.0', 'torch': care_fm.TORCH}, {**self.pin, 'revision': 'rev2'})


if __name__ == '__main__':
    unittest.main()
