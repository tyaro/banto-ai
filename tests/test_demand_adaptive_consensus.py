import copy
import datetime as dt
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_adaptive_consensus as q


def row(origin='2014-06-18', store=6):
    values = [10.]*28+[12.]*14+[14.]*7+[16.]*7
    return {'store': store, 'origin': origin, 'scale': 10., 'matched_mean28': [13.]*14,
            'raw_prediction': [16.]*14, 'actual': [14.]*14, 'open_mask': [True]*14,
            'past_original_quantity': values, 'past_original_observed': [True]*56}


class AdaptiveChecks(unittest.TestCase):
    def test_exact_nonoverlap_hindcast_and_trend(self):
        r = row(); s = q.signals(r)
        self.assertEqual(s['blocks']['28']['residual'], 28.)
        self.assertEqual(s['blocks']['14']['residual'], 56.)
        self.assertEqual(s['trend7'], 14.)
        self.assertEqual(s['common_direction'], 1)
        self.assertEqual(s['blocks']['28']['reference_first'], str(dt.date(2014,6,18)-dt.timedelta(days=56)))
        self.assertEqual(s['blocks']['14']['actual_end_exclusive'], r['origin'])

    def test_bias_minimum_and_confirmed_raw(self):
        r = row(); forecasts, s = q.candidates(r)
        self.assertAlmostEqual(math.fsum(forecasts['consensus_bias']), 210.)
        self.assertEqual(forecasts['consensus_raw'],r['raw_prediction'])
        r['raw_prediction'] = [10.]*14
        forecasts, s = q.candidates(r)
        self.assertEqual(forecasts['consensus_raw'],r['matched_mean28'])
        self.assertTrue(s['bias_active']); self.assertFalse(s['raw_active'])

    def test_missing_block_abstains_and_zero_remains_observed(self):
        r = row(); r['past_original_quantity'][-1] = None; r['past_original_observed'][-1] = False
        forecasts, s = q.candidates(r)
        self.assertFalse(s['active']); self.assertIn('lag14_missing_actual',s['reasons'])
        self.assertEqual(forecasts['consensus_bias'],r['matched_mean28'])
        r = row(); r['past_original_quantity'][0] = 0.
        s = q.signals(r); self.assertEqual(sum(s['blocks']['28']['weekday_counts']),28)

    def test_recent_week_reversal_veto(self):
        r = row(); r['past_original_quantity'][-14:] = [16.]*7+[14.]*7
        s = q.signals(r)
        self.assertGreater(s['blocks']['14']['residual'],0.)
        self.assertGreater(s['blocks']['28']['residual'],0.)
        self.assertLess(s['trend7'],0.)
        self.assertFalse(s['active']); self.assertIn('direction_disagreement',s['reasons'])

    def test_closure_pair_support_not_imputed(self):
        r = row('2014-01-15'); r['past_original_quantity'][-14] = 0.
        s = q.signals(r)
        self.assertEqual(s['trend_pairs'],6); self.assertIn('trend_pair_support',s['reasons'])
        self.assertTrue(s['blocks']['14']['supported'])

    def test_prediction_does_not_read_current_actual(self):
        class Poison(dict):
            def __getitem__(self,key):
                if key=='actual':raise AssertionError('future target accessed')
                return super().__getitem__(key)
        p = {'shared_coefficients': {m:{'alpha':.5} for m in q.ORDER}}
        self.assertEqual(q.choices(Poison(row()),p),q.choices(row(),p))

    def test_foreign_future_metadata_rejected_before_labels(self):
        class Poison(dict):
            def __getitem__(self,key):
                if key=='actual':raise AssertionError('future label read')
                return super().__getitem__(key)
        with self.assertRaises(ValueError):q.calibrate([Poison(store=31,origin='2014-01-15')])
        with self.assertRaises(ValueError):q.calibrate([Poison(store=6,origin='2015-01-01')])

    def test_shared_alpha_uses_all_quarter_constraints(self):
        rows = [row(f'2014-{month:02d}-18',s) for month in (3,6,9,11) for s in q.FIT]
        # One quarter where the positive candidate would worsen total MSE and over-risk.
        for r in rows:
            if r['origin'].startswith('2014-11'):r['actual']=[10.]*14
        p, journal = q.calibrate(rows)
        self.assertEqual(p['shared_coefficients']['consensus_bias']['alpha'],0.)
        self.assertEqual(p['shared_coefficients']['consensus_raw']['alpha'],0.)
        self.assertTrue(all(v['complete_windows']==10 for vs in p['quarter_constraints'].values() for v in vs.values()))

    def test_shared_coefficient_and_nonnegative_horizon(self):
        r = row(); p = {'shared_coefficients':{m:{'alpha':.25} for m in q.ORDER}}
        f = q.choices(r,p); self.assertAlmostEqual(math.fsum(f['consensus_bias']),189.)
        self.assertTrue(all(v>=0 for values in f.values() for v in values))

    def test_negative_persistence_and_zero_total_floor(self):
        r = row(); r['past_original_quantity'] = [16.]*28+[14.]*14+[12.]*7+[10.]*7
        r['raw_prediction'] = [10.]*14
        forecasts, s = q.candidates(r)
        self.assertEqual(s['common_direction'],-1)
        self.assertAlmostEqual(math.fsum(forecasts['consensus_bias']),154.)
        r['matched_mean28'] = [1.]*14
        forecasts, s = q.candidates(r)
        self.assertEqual(forecasts['consensus_bias'],[0.]*14)


if __name__=='__main__':unittest.main()
