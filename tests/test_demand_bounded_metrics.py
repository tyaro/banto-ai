import math,sys,unittest
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_bounded_metrics as m

class BoundedMetricsTests(unittest.TestCase):
    def test_new_entry(self):self.assertEqual(m.P,192);self.assertEqual(m.__name__,'demand_bounded_metrics')
    def test_negative_floor_ceil(self):
        r=m.enclosure([F(-1,3)],m.Arithmetic());self.assertEqual(int(r['lower_numerator']),(-m.S)//3)
        self.assertEqual(int(r['upper_numerator']),-((m.S)//3));self.assertEqual(r['decision'],'decreased')
    def test_exact_structural_zero(self):
        r=m.enclosure([F(0)]*20,m.Arithmetic());self.assertEqual(r['decision'],'equal');self.assertEqual(r['width_units'],0)
    def test_cancellation_may_be_unresolved(self):
        r=m.enclosure([F(1,3),F(-1,3)],m.Arithmetic());self.assertEqual(r['decision'],'unresolved')
        r=m.enclosure([F(1),F(-1)],m.Arithmetic());self.assertEqual(r['decision'],'equal');self.assertEqual(r['nonzero_terms'],2)
    def test_touch_zero_not_strict_improvement(self):
        r=m.enclosure([F(-1,2*m.S)],m.Arithmetic());self.assertEqual(r['upper_numerator'],'0');self.assertEqual(r['decision'],'nonincreased')
    def test_tiny_positive_not_epsilon_pass(self):
        r=m.enclosure([F(1,2*m.S)],m.Arithmetic());self.assertEqual(r['decision'],'unresolved')
    def test_known_signs(self):
        self.assertEqual(m.enclosure([F(1,3)],m.Arithmetic())['decision'],'increased')
        self.assertEqual(m.enclosure([F(-1,3)],m.Arithmetic())['decision'],'decreased')
    def test_limits_refuse_not_fallback(self):
        with self.assertRaises(m.BoundFailure):m.Arithmetic().value(1<<8192)
        with self.assertRaises(m.BoundFailure):m.enclosure([F(1<<8100)],m.Arithmetic())
        with self.assertRaises(m.BoundFailure):m.enclosure((F(0) for _ in range(8193)),m.Arithmetic())
        with self.assertRaises(ValueError):m.enclosure([],m.Arithmetic())
    def test_many_denominators_no_common_fraction(self):
        exponents=(257,263,269,271,277,281,283,293,307,311,313,317,331,337,347,349,353,359,367,373,379,383,389,397,401,409,419,421,431,433,439,443)
        den=[(1<<p)-1 for p in exponents]
        self.assertTrue(all(math.gcd(x,y)==1 for i,x in enumerate(den) for y in den[i+1:]))
        self.assertGreater(sum(p-1 for p in exponents),8192)
        a=m.Arithmetic();r=m.enclosure([F(1,d) for d in den],a)
        self.assertEqual(r['lower_numerator'],'0');self.assertEqual(int(r['upper_numerator']),len(den));self.assertLess(a.max_bits,8192)
    def f(self,store,missing=False):
        mask=[True]*14;b=[10.]*14;c=['11']*14;actual=[10.]*14
        if missing:mask[-1]=False;b[-1]=0.;c[-1]='0';actual[-1]=None
        return {'store':store,'scale':10.,'baseline':b,'candidate_daily_exact':c,'baseline_total':str(F(math.fsum(b))),
            'candidate_total':str(sum(map(F,c))),'assumed_open_mask':mask},actual
    def test_unequal_support_and_missing_modes(self):
        rows=[]
        for s in m.FIT:
            f,y=self.f(s);rows.append({'forecast':f,'observed':y,'assumed_missing_zero':y})
        f,y=self.f(6,True);f['candidate_daily_exact']=['12']*13+['0'];f['candidate_total']='156';rows.append({'forecast':f,'observed':y,'assumed_missing_zero':y[:-1]+[0.]})
        obs=m.score_group(rows,'observed',m.Arithmetic());imp=m.score_group(rows,'assumed_missing_zero',m.Arithmetic())
        self.assertEqual(obs['candidate']['store_support']['6']['total_MSE'],1)
        self.assertEqual(imp['candidate']['store_support']['6']['total_MSE'],2)
        self.assertEqual(obs['candidate']['store_support']['6']['daily_MSE'],27)
        self.assertEqual(imp['candidate']['store_support']['6']['daily_MSE'],28)
        self.assertEqual(obs['candidate']['store_support']['6']['quantity_MSE'],27)
        r=obs['paired']['macro']['total_MSE'];self.assertLessEqual(F(int(r['lower_numerator']),m.S),F(1,100))
        self.assertGreaterEqual(F(int(r['upper_numerator']),m.S),F(1,100))
        expected=(9*F(1,100)+(F(1,100)+F(169,4900))/2)/10
        r=imp['paired']['macro']['total_MSE']
        self.assertLessEqual(F(int(r['lower_numerator']),m.S),expected);self.assertGreaterEqual(F(int(r['upper_numerator']),m.S),expected)
    def test_canonical_total_not_daily_resum(self):
        f,y=self.f(6);f['baseline_total']='140';f['candidate_total']='141';f['candidate_daily_exact']=['10']*14
        r=m.atoms(f,y,m.Arithmetic());self.assertEqual(r['daily_MSE'][0],(0,0));self.assertEqual(r['total_MSE'][0],(0,F(1,19600)))

if __name__=='__main__':unittest.main()
