import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_seasonal_influence_v2 import probe_difference

class ProbeInfluenceTests(unittest.TestCase):
    def f(self,key,x):return {'key':key,'store':6,'origin':'2014-02-15','scale':10.,'baseline':[10.]*14,'features':x,'candidate_total':'140'}
    def test_all_and_eligible_denominators_and_no_labels(self):
        r=probe_difference([self.f('eligible',[1,0,0]),self.f('fallback',None)],1,['1/10','0','0'])
        self.assertEqual(r['all_probes']['count'],2);self.assertEqual(r['all_probes']['changed'],1)
        self.assertEqual(r['eligible_probes']['count'],1);self.assertEqual(r['all_probes']['max_absolute'],'14')
        self.assertEqual(r['all_probes']['mean_square'],'98');self.assertEqual(r['eligible_probes']['mean_square'],'196')
    def test_partial_probe_survives_later_failure(self):
        progress=[];bad=self.f('bad',[1,0,0]);bad['scale']=None
        with self.assertRaises((ValueError,TypeError)):
            probe_difference([self.f('good',[1,0,0]),bad],1,['1/10','0','0'],progress)
        self.assertEqual(len(progress),1);self.assertEqual(progress[0]['key'],'good')
        self.assertEqual(progress[0]['delta_from_primary'],'14')
    def test_wrong_probe_quarter_stops(self):
        with self.assertRaises(ValueError):probe_difference([self.f('a',[1,0,0])],2,['0']*3)
    def test_no_eligible_is_not_reported_as_stable(self):
        r=probe_difference([self.f('b',None)],1,['99']*3)
        self.assertEqual(r['eligible_probes']['count'],0);self.assertIsNone(r['eligible_probes']['mean_square'])

if __name__=='__main__':unittest.main()
