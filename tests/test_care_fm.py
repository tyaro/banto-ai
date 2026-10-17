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


if __name__ == '__main__':
    unittest.main()
