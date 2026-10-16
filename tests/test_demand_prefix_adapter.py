import copy,datetime as dt,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_prefix_adapter as a
import demand_input_boundary_v2 as b
from test_demand_input_boundary import legacy,transform


def sample_batch(origin='2013-12-03',store=6):
 r=legacy(origin,store);i=b.project_input(r);l=b.project_label(r);x,why=a.input_features(i,transform())
 row={'key':i['key'],'store':store,'origin':origin,'target_dates':i['target_dates'],'label_available_at':l['available_at'],'raw_actual':l['raw_actual'],'baseline':i['matched_mean28'],'assumed_open_mask':i['assumed_open_mask'],'past14_dates':i['past_dates'][-14:],'past14_values':i['past_values'][-14:],'scale':10.,'transform_usable_from':'2014-01-01','features':x,'reasons':why}
 return {'schema':'demand-permitted-prefix-v1','cutoff':'2014-01-01','feature_spec':a.FEATURE_SPEC,'rows':[row]}

class PrefixAdapterTests(unittest.TestCase):
 def test_features_have_fixed_mean_total_units(self):
  values=[5.]*7+[10.]*7;dates=[str(dt.date(2014,2,1)+dt.timedelta(days=j)) for j in range(14)]
  x,why=a.fixed_features(values,dates,[10.]*14,[True]*14,10.)
  self.assertEqual(x,[1.,0.,.5]);self.assertEqual(why,[])
 def test_zero_valid_missing_and_closure_fallback(self):
  r=legacy('2014-02-15');r['past_original_quantity'][-1]=0.;r['matched_mean28']=[7.5 if j%7==6 else 10. for j in range(14)]
  self.assertIsNotNone(a.fixed_features([0.]*14,[str(dt.date(2014,2,1)+dt.timedelta(days=j)) for j in range(14)],[10.]*14,[True]*14,10.)[0])
  rr=sample_batch();row=rr['rows'][0];row['past14_values'][0]=None;row['features'],row['reasons']=a.fixed_features(row['past14_values'],row['past14_dates'],row['baseline'],row['assumed_open_mask'],row['scale'])
  self.assertIn('past14_missing',row['reasons']);a.validate_batch(rr)
  i=b.project_input(legacy('2014-01-15'));self.assertIn('past14_assumed_closure',a.input_features(i,transform())[1])
 def test_zero_baseline_unsupported(self):
  row=sample_batch()['rows'][0]
  x,why=a.fixed_features(row['past14_values'],row['past14_dates'],[0.]*14,row['assumed_open_mask'],10.)
  self.assertIsNone(x);self.assertIn('zero_baseline_total',why)
 def test_deliver_breaks_parent_references_and_cannot_pass_paths(self):
  batch=sample_batch();before=copy.deepcopy(batch)
  def consumer(fresh):fresh['rows'][0]['raw_actual'][0]=999.;return len(fresh['rows'])
  self.assertEqual(a.deliver(batch,consumer),1);self.assertEqual(batch,before)
  batch['source_path']='/forbidden'
  with self.assertRaises(ValueError):a.deliver(batch,consumer)
 def test_future_label_or_context_rejected(self):
  batch=sample_batch('2014-01-01')
  with self.assertRaises(ValueError):a.validate_batch(batch)
  batch=sample_batch();batch['rows'][0]['past14_dates'][-1]='2014-01-01'
  with self.assertRaises(ValueError):a.validate_batch(batch)
 def test_forged_identity_features_and_transforms_rejected(self):
  for key,value in (('key','fake'),('features',[1.,99.,0.]),('features',[True,0.,0.]),('transform_usable_from','2014-01-02'),('raw_actual',[None]*14)):
   batch=sample_batch();batch['rows'][0][key]=value
   with self.assertRaises(ValueError):a.validate_batch(batch)
 def test_duplicate_or_extra_row_field_rejected(self):
  batch=sample_batch();batch['rows'].append(copy.deepcopy(batch['rows'][0]))
  with self.assertRaises(ValueError):a.validate_batch(batch)
  batch=sample_batch();batch['rows'][0]['reader']='forbidden'
  with self.assertRaises(ValueError):a.validate_batch(batch)
 def test_support_does_not_use_target_magnitude(self):
  batch=sample_batch();before=a.feature_support(batch);batch['rows'][0]['raw_actual']=[99999.]*14
  self.assertEqual(a.feature_support(batch),before)
 def test_materialize_contains_only_authorized_concrete_rows(self):
  with tempfile.TemporaryDirectory() as folder:
   old=legacy('2013-12-03');future=legacy('2014-01-01');inputs=[b.project_input(r) for r in (old,future)];payload,index=b.label_payload([b.project_label(r) for r in (old,future)]);path=Path(folder)/'labels';path.write_bytes(payload);reader=b.LabelReader(path,index,inputs,b.pin_bytes(payload))
   batch,ledger=a.materialize(inputs,transform(),reader,'2014-01-01')
   self.assertEqual(len(batch['rows']),1);self.assertEqual(batch['rows'][0]['raw_actual'],old['actual']);self.assertNotIn(inputs[1]['key'],[r['key'] for r in batch['rows']]);self.assertFalse(ledger['model_fit_performed'])
 def test_scale_and_negative_feature_values_not_quantities(self):
  batch=sample_batch();row=batch['rows'][0];row['past14_values']=[5.]*14;row['features'],row['reasons']=a.fixed_features(row['past14_values'],row['past14_dates'],row['baseline'],row['assumed_open_mask'],row['scale']);self.assertLess(row['features'][1],0.);a.validate_batch(batch)

if __name__=='__main__':unittest.main()
