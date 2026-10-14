"""New calibration/interval mechanisms only; prior forecasting tests untouched."""
from pathlib import Path
import datetime as dt,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_interval import calibrate_relative_total,relative_total_interval


class IntervalTests(unittest.TestCase):
    def records(self):
        return [{'target_end':str(dt.date(2016,1,14)+dt.timedelta(days=14*i)),
                 'prediction':100.,'actual':100.+i} for i in range(25)]
    def test_hand_corrected_order_statistic_and_bounds(self):
        model=calibrate_relative_total(self.records())
        self.assertEqual(model['support'],25);self.assertEqual(model['rank'],21)
        self.assertAlmostEqual(model['radius'],.20)
        result=relative_total_interval(100.,model)
        self.assertEqual((result['lower'],result['upper']),(80.,120.))
        self.assertFalse(result['coverage_guarantee_established'])
    def test_future_poison_cannot_change_calibrated_radius(self):
        records=self.records();model=calibrate_relative_total(records)
        records.append({'target_end':'2017-01-01','prediction':object(),'actual':object()})
        later=calibrate_relative_total(records)
        self.assertEqual(model['radius'],later['radius']);self.assertEqual(model['scores'],later['scores'])
        self.assertEqual(later['excluded']['after_cutoff'],1)
    def test_observed_zero_is_a_score_not_a_missing_label(self):
        records=self.records();records[0]['actual']=0.
        model=calibrate_relative_total(records)
        self.assertEqual(model['scores'][0]['score'],1.)
        result=relative_total_interval(100.,{'radius':1.5})
        self.assertEqual(result['lower'],0.);self.assertEqual(result['upper'],250.)
        self.assertTrue(result['lower_clipped_at_zero'])
    def test_missing_zero_scale_and_insufficient_support_explicit(self):
        records=self.records();records[0]['actual']=None;records[1]['prediction']=0.
        model=calibrate_relative_total(records)
        self.assertEqual(model['support'],23)
        self.assertEqual(model['excluded']['missing_total'],1)
        self.assertEqual(model['excluded']['zero_prediction_scale'],1)
        small=calibrate_relative_total(records[:19])
        self.assertIsNone(small['radius'])
        self.assertIsNone(relative_total_interval(100.,small)['lower'])
        self.assertEqual(relative_total_interval(0.,model)['reason'],'zero_point_scale')
    def test_duplicate_cutoff_and_nonfinite_rejected(self):
        records=self.records()
        with self.assertRaises(ValueError):calibrate_relative_total(records+[records[0]])
        with self.assertRaises(ValueError):calibrate_relative_total(records,cutoff=dt.date(2018,1,1))
        with self.assertRaises(ValueError):calibrate_relative_total([{'target_end':'2015-12-31'}])
        with self.assertRaises(ValueError):relative_total_interval(float('inf'),{'radius':.2})


if __name__=='__main__':unittest.main(verbosity=2)
