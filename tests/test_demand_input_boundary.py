import copy,datetime as dt,json,math,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_input_boundary as m


def legacy(origin='2014-01-15',store=6):
    o=dt.date.fromisoformat(origin);values=[10.]*56
    dates=[o-dt.timedelta(days=k) for k in range(56,0,-1)]
    target=[o+dt.timedelta(days=k) for k in range(14)];mask=[str(d)[5:] not in ('01-01','12-25') for d in target]
    return {'store':store,'origin':origin,'past_original_quantity':values,'past_original_observed':[True]*56,
            'matched_mean28':[10. if good else 0. for good in mask],'open_mask':mask,'operating_status':'unknown','actual':[12.]*14,'raw_prediction':[999.]*14,'encoded':{'future_actual':'sentinel'}}


def transform():
    return {'schema':'demand-transform-v1','policy_ref':m.POLICY,'scale_period':{'start':'2013-01-01','end':'2013-12-31'},
            'scale_usable_from':'2014-01-01','scales':{str(s):10. for s in m.FIT},'closure_period':{'start':'2013-01-01','end':'2013-12-31'},
            'closure_usable_from':'2014-01-01','month_days':['01-01','12-25'],'availability_basis':m.DAY_ASSUMPTION}

class InputBoundaryTests(unittest.TestCase):
    def test_projection_ignores_even_unreadable_labels_and_derived_features(self):
        class Bomb:
            def __iter__(self):raise AssertionError('label touched')
        r=legacy();expected=m.project_input(r);r['actual']=Bomb();r['complete_label']=Bomb();r['profile']=Bomb()
        self.assertEqual(expected,m.project_input(r))
        self.assertFalse({'actual','raw_prediction','complete_label','encoded','scale'}&set(expected))
    def test_label_values_missing_order_and_absence_do_not_change_inputs(self):
        original=legacy();base=m.canonical(m.project_input(original))
        for v in ([0.]*14,[None]*14,[1000000.]*14,list(reversed(original['actual']))):
            r=copy.deepcopy(original);r['actual']=v
            self.assertEqual(base,m.canonical(m.project_input(r)))
        del original['actual'];self.assertEqual(base,m.canonical(m.project_input(original)))
    def test_extra_or_nested_label_payload_rejected_by_input_schema(self):
        for key,value in (('actual',[0.]*14),('metadata',{'actual':1.}),('scale',10.)):
            r=m.project_input(legacy());r[key]=value
            with self.assertRaises(ValueError):m.validate_input(r)
        r=m.project_input(legacy());r['past_values'][0]={'actual':1.}
        with self.assertRaises(ValueError):m.validate_input(r)
    def test_json_duplicate_keys_and_nonfinite_constants_rejected(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":{"b":1,"b":2}}',b'[NaN]',b'[Infinity]',b'[-Infinity]'):
            with self.assertRaises(ValueError):m.strict_json(raw)
    def test_bool_nan_infinity_negative_quantities_rejected(self):
        for value in (True,float('nan'),float('inf'),-1.):
            r=m.project_input(legacy());r['past_values'][0]=value
            with self.assertRaises(ValueError):m.validate_input(r)
            l=m.project_label(legacy());l['raw_actual'][0]=value
            with self.assertRaises(ValueError):m.validate_label(l)
    def test_context_dates_lengths_masks_and_baseline_consistency(self):
        for key,value in (('past_dates',['2014-01-15']*56),('past_available_at',['2014-01-16']*56),('past_values',[10.]*55),('past_observed',[True]*55),('operating_status','closed'),('matched_mean28',[11.]*14)):
            r=m.project_input(legacy());r[key]=value
            with self.assertRaises(ValueError):m.validate_input(r)
    def test_true_zero_and_null_are_distinct(self):
        r=legacy();r['past_original_quantity'][0]=0.;r['past_original_quantity'][1]=None;r['past_original_observed'][1]=False
        p=m.project_input(r);self.assertIs(p['past_values'][1],None);self.assertEqual(p['past_values'][0],0.)
        p['past_observed'][1]=True
        with self.assertRaises(ValueError):m.validate_input(p)
    def test_store_year_target_and_identity_rejected(self):
        for store,origin in ((31,'2014-01-15'),(True,'2014-01-15'),(6,'2015-01-01'),(6,'2014-12-25')):
            with self.assertRaises(ValueError):m.identity(store,origin)
        r=m.project_input(legacy());r['target_dates'][0]='2014-01-16'
        with self.assertRaises(ValueError):m.validate_input(r)
    def test_full2013_scale_blocked_at_2013_origin_but_valid_for_2014_fit(self):
        r=m.project_input(legacy('2013-12-18'));t=transform()
        self.assertFalse(m.input_readiness(r,t)['ready'])
        self.assertTrue(m.input_readiness(r,t,asof='2014-01-01',purpose='historical_fit')['ready'])
        with self.assertRaises(ValueError):m.input_readiness(r,t,asof='2014-01-01',purpose='prediction')
    def test_transform_provenance_and_usable_from_both_checked(self):
        for k,value in (('scale_usable_from','2013-12-31'),('closure_usable_from','2014-01-02'),('scale_period',{'start':'2013-01-01','end':'2014-01-01'}),('closure_period',{'start':'2013-01-01','end':'2014-12-31'})):
            t=transform();t[k]=value
            with self.assertRaises(ValueError):m.validate_transforms(t)
    def _store(self,rr,folder):
        inputs=[m.project_input(r) for r in rr];labels=[m.project_label(r) for r in rr];payload,index=m.label_payload(labels);p=Path(folder)/'labels.jsonl';p.write_bytes(payload)
        return inputs,index,m.LabelReader(p,index,inputs,m.pin_bytes(payload))
    def test_equal_availability_allowed_and_future_rejected_before_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            inputs,index,reader=self._store([legacy('2013-12-18'),legacy('2013-12-19')],folder)
            self.assertEqual(reader.read_available(inputs[0],'2014-01-01')['available_at'],'2014-01-01')
            with patch.object(reader,'_decode',side_effect=AssertionError('future decode')) as spy:
                with self.assertRaises(ValueError):reader.read_available(inputs[1],'2014-01-01')
                spy.assert_not_called()
    def test_fit_prefix_decodes_only_past_and_excludes_missing_after_read(self):
        old=legacy('2013-12-18');missing=legacy('2013-12-18',7);missing['actual'][0]=None
        with tempfile.TemporaryDirectory() as folder:
            inputs,index,reader=self._store([old,missing,legacy('2014-01-01')],folder)
            p=m.fit_prefix(inputs,transform(),reader,'2014-01-01')
            self.assertEqual(p['accepted_keys'],[inputs[0]['key']]);self.assertEqual(len(p['decoded_keys']),2)
            self.assertIn('past_label_incomplete',[r['reason'] for r in p['excluded']])
            self.assertNotIn(inputs[2]['key'],reader.decoded_keys)
    def test_index_missing_extra_duplicate_and_forged_availability_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            inputs,index,reader=self._store([legacy()],folder);size=reader.path.stat().st_size
            for bad in ([],index+index):
                with self.assertRaises(ValueError):m.validate_index(bad,inputs,size)
            for key,value in (('available_at','2014-01-15'),('origin','2014-01-16'),('offset',True),('length',-1)):
                bad=copy.deepcopy(index);bad[0][key]=value
                with self.assertRaises(ValueError):m.validate_index(bad,inputs,size)
    def test_payload_tampering_fails_whole_file_or_row_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            inputs,index,reader=self._store([legacy()],folder);p=reader.path;expected=m.pin_file(p);p.write_bytes(p.read_bytes().replace(b'12.0',b'13.0'))
            with self.assertRaises(ValueError):m.LabelReader(p,index,inputs,expected)
            with self.assertRaises(ValueError):reader.read_available(inputs[0],'2014-02-01')
    def test_label_index_and_payload_store_date_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            inputs,index,reader=self._store([legacy()],folder)
            r=m.project_input(legacy(store=7))
            with self.assertRaises(KeyError):reader.read_available(r,'2014-02-01')
    def test_strict_input_loader_pin_and_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'input.json';r=m.project_input(legacy());p.write_bytes(m.canonical([r]));expected=m.pin_file(p)
            self.assertEqual(m.load_inputs(p,expected),[r]);p.write_bytes(m.canonical([r,r]))
            with self.assertRaises(ValueError):m.load_inputs(p,expected)
            with self.assertRaises(ValueError):m.load_inputs(p,m.pin_file(p))
    def test_schedule_does_not_accept_label_arguments(self):
        keys=m.issue_schedule();self.assertEqual(len(keys),260)
        rows=[m.project_input(legacy(o,s)) for s,o in keys];groups=m.issue_groups(rows)
        self.assertEqual(len(groups),26);self.assertTrue(all(len(v)==10 for v in groups.values()))
        with self.assertRaises(ValueError):m.issue_groups(rows[:-1])
        with self.assertRaises(ValueError):m.issue_groups(rows+[rows[0]])
    def test_missing_zero_scenario_only_closure_and_raw_preserved(self):
        r=legacy('2014-12-17');r['actual'][0]=None;r['actual'][8]=None;r['actual'][1]=0.
        inp=m.project_input(r);label=m.project_label(r);before=copy.deepcopy(label);v=m.label_scenarios(inp,label)
        self.assertEqual(v['imputed_positions'],[8]);self.assertIsNone(v['assumed_missing_zero']['actual'][0]);self.assertEqual(v['assumed_missing_zero']['actual'][8],0.)
        self.assertIsNone(v['observed']['actual'][8]);self.assertEqual(label,before)
    def test_positive_on_assumed_closure_is_not_erased(self):
        r=legacy('2014-12-17');i=m.project_input(r);l=m.project_label(r);v=m.label_scenarios(i,l)
        self.assertFalse(i['assumed_open_mask'][8]);self.assertEqual(v['assumed_missing_zero']['actual'][8],12.)
    def test_no_model_or_scoring_api(self):
        self.assertFalse(any(hasattr(m,n) for n in ('fit_model','predict','score','train')))

if __name__=='__main__':unittest.main()
