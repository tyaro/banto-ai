"""Only the newly supported real store identifiers; prior checks not repeated."""
from pathlib import Path
import datetime as dt,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_anniversary import fit_anniversaries,correct_baseline


class StoreIdentifierTests(unittest.TestCase):
    def test_real_identifiers_route_distinct_store_history(self):
        rows=[{'date':f'{y}-01-01','store':store,'sales':sales,'past_same_weekday_mean':100.,'support':4}
              for store,sales in [(5,0.),(11,100.),(12,200.)] for y in [2014,2015]]
        model=fit_anniversaries([{'month_day':'01-01','rows':rows}],stores=(5,11,12))
        self.assertEqual(set(model),{5,11,12})
        self.assertEqual([correct_baseline(model,s,dt.date(2017,1,1),100.)['prediction'] for s in (5,11,12)], [60.,100.,140.])

    def test_invalid_store_scope_rejected(self):
        for stores in [(),(5,5),(True,11),(0,12),('5',11)]:
            with self.assertRaises(ValueError):fit_anniversaries([],stores=stores)


if __name__=='__main__':unittest.main(verbosity=2)
