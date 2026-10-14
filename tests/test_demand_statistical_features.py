from pathlib import Path
import sys,datetime as dt,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_statistical_overlay import describe_history
from demand_statistical_features import encode_profile
ORIGIN=dt.date(2025,3,1)


class StatisticalFeatureChecks(unittest.TestCase):
    def test_scale_invariance_and_distinct_zero_vs_missing(self):
        h={ORIGIN-dt.timedelta(days=k):100.+(20. if k<=7 else 0.) for k in range(1,57)}
        a=encode_profile(describe_history(h,ORIGIN),ORIGIN,100)
        b=encode_profile(describe_history({d:v*10 for d,v in h.items()},ORIGIN),ORIGIN,1000)
        for x,y in zip(a['features'],b['features']):self.assertAlmostEqual(x,y)
        zero=encode_profile(describe_history({d:0. for d in h},ORIGIN),ORIGIN,100)
        missing=encode_profile(describe_history({},ORIGIN),ORIGIN,100)
        self.assertEqual(zero['features'][:4],[0.]*4);self.assertEqual(missing['features'][:4],[0.]*4)
        self.assertEqual(zero['features'][6],1);self.assertEqual(missing['features'][6],0)
        self.assertFalse(a['point_changed'])

    def test_header_rejects_future_profile_before_numeric_payload(self):
        class HeadersOnly(dict):
            def __getitem__(self,key):
                if key not in ('origin','past_end'):raise AssertionError('future statistics read')
                return super().__getitem__(key)
        future=HeadersOnly(origin=str(ORIGIN+dt.timedelta(days=1)),past_end=str(ORIGIN))
        with self.assertRaisesRegex(ValueError,'cutoff'):
            encode_profile(future,ORIGIN,100)

    def test_weekday_raw_variation_and_error_sigma_are_different(self):
        h={ORIGIN-dt.timedelta(days=k):20.+10*(ORIGIN-dt.timedelta(days=k)).weekday() for k in range(1,57)}
        self.assertGreater(max(h.values())-min(h.values()),0)
        profile=describe_history(h,ORIGIN)
        encoded=encode_profile(profile,ORIGIN,100)
        self.assertEqual(encoded['features'][3],0)
        self.assertEqual(encoded['features'][6],1)

    def test_staleness_masks_zero_scale_and_inconsistent_support(self):
        h={ORIGIN-dt.timedelta(days=k):100. for k in range(1,57)}
        h[ORIGIN-dt.timedelta(days=1)]=None
        profile=describe_history(h,ORIGIN);e=encode_profile(profile,ORIGIN,100)
        self.assertAlmostEqual(e['features'][5],1/28);self.assertEqual(e['features'][7],1)
        self.assertFalse(encode_profile(profile,ORIGIN,0)['branch_available'])
        invalid=dict(profile,support=0)
        with self.assertRaises(ValueError):encode_profile(invalid,ORIGIN,100)


if __name__=='__main__':unittest.main()
