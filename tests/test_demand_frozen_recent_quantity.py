import copy
import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_frozen_recent_quantity as recent

requires_torch = unittest.skipUnless(importlib.util.find_spec('torch'), 'torch is not installed')


def packet(s, day, value=12.):
    return {'store':s,'origin':str(day),'scale':1.,'open_mean28':[10.]*14,'open_mask':[True]*14,
            'raw_features':[[1.]+[0.]*71]*14,'actual':[value]*14}


def pool(origin):
    return [packet(s,origin-dt.timedelta(days=210-14*k)) for s in recent.FIT for k in range(14)]


class RecentQuantityChecks(unittest.TestCase):
    def test_strict_label_end_and_inclusive_365_days(self):
        origin=dt.date(2015,1,1)
        rows=[packet(6,origin-dt.timedelta(days=k)) for k in (366,365,14,13,0)]
        self.assertEqual([r['origin'] for r in recent.select_recent(rows,origin)],['2014-01-01','2014-12-18'])

    def test_current_future_and_foreign_actual_not_accessed(self):
        class Forbidden(dict):
            def __getitem__(self,key):
                if key=='actual':raise AssertionError('future target read')
                return super().__getitem__(key)
        rows=[Forbidden(store=6,origin='2015-01-01'),Forbidden(store=6,origin='2015-01-13'),Forbidden(store=31,origin='INVALID')]
        self.assertEqual(recent.select_recent(rows,dt.date(2015,1,1)),[])

    @requires_torch
    def test_current_target_poison_cannot_change_past_state(self):
        origin=dt.date(2014,10,7); training=pool(origin)
        current=[packet(s,origin,0.) for s in recent.FIT]
        before,state=recent.fit_forecast(training,current)
        poisoned=[{**r,'actual':[999999.]*14} for r in current]
        after,other=recent.fit_forecast(training+poisoned,poisoned)
        self.assertEqual(before,after); self.assertEqual(state,other)
        self.assertLess(state['last_label_day'],str(origin))

    @requires_torch
    def test_equal_store_support_and_minimum_required(self):
        origin=dt.date(2014,10,7); training=pool(origin);current=[packet(s,origin) for s in recent.FIT]
        with self.assertRaises(ValueError):recent.fit_forecast(training[:-1],current)
        with self.assertRaises(ValueError):recent.fit_forecast(training[:130],current)

    def test_duplicate_eligible_past_keys_rejected(self):
        origin=dt.date(2014,10,7); training=pool(origin)
        with self.assertRaises(ValueError):recent.select_recent(training+training[:1],origin)

    def test_fixed_three_candidate_tie_and_winner(self):
        scores={name:{'joint':1.} for name in recent.ORDER}
        self.assertEqual(recent.choose(scores),'matched_mean28')
        scores['recent_gated_ridge']['joint']=.9
        self.assertEqual(recent.choose(scores),'recent_gated_ridge')
        with self.assertRaises(ValueError):recent.choose({'recent_gated_ridge':{'joint':.9}})

    @requires_torch
    def test_final_state_prediction_does_not_modify_coefficients(self):
        import torch
        origin=dt.date(2015,1,1); current=[packet(s,origin) for s in recent.FIT]
        _,journal=recent.fit_forecast(pool(origin),current)
        state={k:torch.tensor(v,dtype=torch.bool if k=='active' else torch.float64) for k,v in journal['state'].items()}
        before={k:v.clone() for k,v in state.items()}
        raw,base,u,mask=recent.tensor_inputs(current)
        recent.predict_gated(raw,base,u,mask,state)
        recent.predict_gated(raw,base+5.,u,mask,state)
        self.assertTrue(all(torch.equal(v,state[k]) for k,v in before.items()))


if __name__=='__main__':unittest.main()
