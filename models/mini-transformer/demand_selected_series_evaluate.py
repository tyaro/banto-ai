"""One fixed cross-series evaluation of internally selected weights; no fitting."""
import time
STARTED=time.monotonic()
from pathlib import Path
import argparse,csv,datetime as dt,io,json,math,sys,traceback
import torch
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO/'tools'))
from verification_records import verify_record
from store_sales_final import private_memory
from demand_training_adequacy import fit_scales
from demand_statistical_feature_model import StatisticalFeatureMean
from demand_statistical_feature_train import model_inputs,without_features
from demand_statistical_feature_validate import AsOfHistory
from demand_calendar_train import Files,pin,item,error_metrics
from demand_public_calendar import build_inputs
from demand_statistical_overlay import describe_history
from demand_statistical_features import encode_profile


def run(output):
    root=Path(output).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():raise ValueError('fresh output root required')
    files=Files(root);status,stage,peak='failed','freeze-before-quantity',0;rows=[];profiles=[]
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory())
        if peak>2*1024**3 or time.monotonic()-STARTED>870:raise RuntimeError('execution checkpoint; preserve and stop')
    try:
        stores=[4,8,16,20,24,28];active=[4,8,16,24,28];zero=[20]
        dates=[dt.date(2015,1,13)+dt.timedelta(days=14*k) for k in range(25)]
        prior=REPO/'artifacts/representative-demand-training-adequacy-20261014'
        closed_raw=(prior/'root-closed.json').read_bytes();closed=json.loads(closed_raw);assert closed['status']=='complete'
        summary_raw=(prior/'summary.json').read_bytes();assert pin(summary_raw)==closed['files']['summary.json'];summary=json.loads(summary_raw)
        assert summary['status']=='complete' and summary['train_windows']==450 and summary['validation_windows']==180
        source_paths=list(summary['source_pins'])+['models/mini-transformer/demand_selected_series_evaluate.py',
          'docs/research/demand-selected-series-evaluation-design-2026-10-14.md']
        sources={p:(REPO/p).read_bytes() for p in source_paths}
        for p,expected in summary['source_pins'].items():assert pin(sources[p])==expected
        weights={}
        for mode in ('feature_off','feature_on'):
            assert summary['models'][mode]['best_step']==1664
            raw=(prior/(mode+'-best.pt')).read_bytes()
            assert pin(raw)==closed['files'][mode+'-best.pt']==summary['models'][mode]['best_weight_pin'];weights[mode]=raw
        split_raw=(prior/'split-scale-and-support.json').read_bytes();assert pin(split_raw)==closed['files']['split-scale-and-support.json']
        support=json.loads(split_raw)['support'];assert sum(support['enabled'])==42
        files.json('sources.json',{p:r.decode('utf-8') for p,r in sources.items()})
        files.json('frozen-before-quantity.json',{'stores':stores,'positive_scale_expected':active,'baseline_only_expected':zero,
          'origins':[str(d) for d in dates],'source_pins':{p:pin(r) for p,r in sources.items()},
          'best_weight_pins':{m:pin(r) for m,r in weights.items()},'prior_closure_pin':pin(closed_raw),'prior_summary_pin':pin(summary_raw),
          'support_pin':pin(split_raw),'best_step_both':1664,'new_training':False,
          'main_rule':'each NN below mean28 overall and in >=4/5 fixed positive stores',
          'feature_rule':'feature_on below both controls overall and in >=4/5 fixed positive stores',
          'compute_parent_head':'1da73d7b62f830fbf3bc35fdf6ce4e97e699ee60','uncommitted_new_source':True,
          'python':sys.version,'torch':torch.__version__,'formal_permission':False})
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        models={}
        for mode,raw in weights.items():
            model=StatisticalFeatureMean();state=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
            model.load_state_dict(state);assert all(torch.equal(v,state[k]) for k,v in model.state_dict().items())
            model.eval();models[mode]=model
        checkpoint();stage='prefix-preperiod-scale'
        prefix=REPO/'artifacts/representative-store-sales-shared-prefix-20261014-records'
        assert verify_record(prefix)['status']=='complete'
        prefix_summary=json.loads(item(prefix,'summary'));assert prefix_summary['validation']==stores
        snapshot=item(prefix,'selected-quantity-csv')
        assert pin(snapshot)=={'bytes':776915,'sha256':'b7805b258cb6e7a268b3b3289ac1b9688bd54cf03e1f06b01f8e74172fdeddc4'}
        raw_rows=list(csv.DictReader(io.StringIO(snapshot.decode())))
        scale_metadata=fit_scales(raw_rows,stores)
        scales={int(s):r['scale'] for s,r in scale_metadata.items()}
        assert all(scales[s] is not None and scales[s]>0 for s in active) and all(scales[s]==0 for s in zero)
        files.json('preperiod-scales-before-targets.json',{'scale_metadata':scale_metadata,'new_model_fit':False,
          'prefix_pin':pin(snapshot),'source_period':'2013-01-01 <= date < 2014-07-01','2015_quantity_interpreted':False})
        wanted={d+dt.timedelta(days=k) for d in dates for k in range(-56,14)}
        histories={s:{} for s in stores};selected=[]
        for row in raw_rows:
            s,day=int(row['store_nbr']),dt.date.fromisoformat(row['date'])
            if s not in stores or day not in wanted:continue
            assert dt.date(2014,11,18)<=day<=dt.date(2015,12,28) and day not in histories[s]
            assert row['observed'] in ('0','1') and (row['observed']=='1')==bool(row['sales'])
            value=float(row['sales']) if row['observed']=='1' else None
            assert value is None or math.isfinite(value) and value>=0
            histories[s][day]=value;selected.append(row)
        assert all(set(h)==wanted for h in histories.values())
        text=io.StringIO();writer=csv.DictWriter(text,['store_nbr','date','source_id','sales','observed']);writer.writeheader();writer.writerows(selected)
        selected_raw=text.getvalue().encode();files.write('selected-2014-context-2015.csv',selected_raw)
        files.json('input-binding.json',{'prefix_pin':pin(snapshot),'prefix_closure_pin':pin((prefix/'root-closed.json').read_bytes()),
          'selected_pin':pin(selected_raw),'calendar_rows':len(selected),'stores':stores,'2016_2017_reserved_holdout_numeric_read':False,
          'source_archive_read':False,'support_unchanged':True,'scales':scales})
        checkpoint();stage='new-series-inputs';pending=[]
        for s in stores:
            for origin in dates:
                past=AsOfHistory(histories[s],origin)
                x=build_inputs(past,origin,scales[s],'pre_post',support['enabled'])
                profile=describe_history(past,origin);encoded=encode_profile(profile,origin,scales[s])
                profiles.append({'store':s,'origin':str(origin),'profile':profile,'encoded':encoded,
                  'accessed_count':len(past.accessed),'accessed_min':min(past.accessed),'accessed_max':max(past.accessed)})
                baseline=x['baseline'] if None not in x['baseline'] else None
                rows.append({'store':s,'origin':str(origin),'scale':scales[s],'baseline':baseline,
                  'feature_off':baseline if s in zero else None,'feature_on':baseline if s in zero else None,
                  'model_available':x['available'],'input_reasons':x['reasons'],
                  'role':'positive_scale' if s in active else 'zero_scale_baseline_only'})
                if s in active and x['available']:pending.append((len(rows)-1,x,encoded))
        files.json('new-series-profiles.json',profiles)
        stage='fixed-best-inference'
        with torch.no_grad():
            for start in range(0,len(pending),8):
                batch=pending[start:start+8]
                full=model_inputs([x for i,x,e in batch],[e for i,x,e in batch]);control=without_features(full)
                for mode,data in (('feature_off',control),('feature_on',full)):
                    daily,total=models[mode](*data)
                    for j,(index,x,e) in enumerate(batch):
                        values=daily[j].tolist();assert math.isclose(math.fsum(values),total[j].item(),rel_tol=1e-6,abs_tol=1e-5)
                        rows[index][mode]=values
                checkpoint()
        files.json('predictions-before-labels.json',rows)
        stage='labels-after-predictions'
        for row in rows:
            origin=dt.date.fromisoformat(row['origin'])
            row['actual']=[histories[row['store']].get(origin+dt.timedelta(days=k)) for k in range(14)]
            row['complete_label']=all(a is not None for a in row['actual'])
            row['comparable']=all(row[m] is not None for m in ('baseline','feature_off','feature_on'))
        files.json('predictions-and-labels.json',rows)
        stage='fixed-main-and-feature-metrics';methods=('baseline','feature_off','feature_on')
        def metrics(rs,u=None):
            output={}
            for method in methods:
                de,da,te,ta=[],[],[],[]
                for row in rs:
                    if not row['comparable']:continue
                    for p,a in zip(row[method],row['actual']):
                        if a is not None:de.append(p-a);da.append(a)
                    if row['complete_label']:
                        te.append(math.fsum(row[method])-math.fsum(row['actual']));ta.append(math.fsum(row['actual']))
                output[method]={'daily':error_metrics(de,da,[u]*len(de) if u else None),
                  'total':error_metrics(te,ta,[14*u]*len(te) if u else None)}
            return output
        by_store={str(s):metrics([r for r in rows if r['store']==s],scales[s]) for s in stores}
        support_counts={str(s):{'requested':25,'model_and_baseline':sum(r['comparable'] for r in rows if r['store']==s),
          'complete_comparable_labels':sum(r['comparable'] and r['complete_label'] for r in rows if r['store']==s)} for s in active}
        ready=all(v['model_and_baseline']>=20 and v['complete_comparable_labels']>=20 for v in support_counts.values())
        store_joint={str(s):{m:.5*sum(by_store[str(s)][m][scope]['scaled_MSE'] for scope in ('daily','total'))
          if all(by_store[str(s)][m][scope]['scaled_MSE'] is not None for scope in ('daily','total')) else None for m in methods} for s in active}
        primary={m:math.fsum(store_joint[str(s)][m] for s in active)/5 if all(store_joint[str(s)][m] is not None for s in active) else None for m in methods}
        secondary={scope:{m:math.fsum(by_store[str(s)][m][scope]['scaled_MSE'] for s in active)/5
          if all(by_store[str(s)][m][scope]['scaled_MSE'] is not None for s in active) else None for m in methods} for scope in ('daily','total')}
        core_improved={m:[s for s in active if store_joint[str(s)][m] is not None and store_joint[str(s)]['baseline'] is not None and store_joint[str(s)][m]<store_joint[str(s)]['baseline']] for m in methods[1:]}
        core_pass={m:bool(ready and primary[m] is not None and primary['baseline'] is not None and primary[m]<primary['baseline'] and len(core_improved[m])>=4) for m in methods[1:]}
        feature_improved=[s for s in active if all(v is not None for v in store_joint[str(s)].values()) and all(store_joint[str(s)]['feature_on']<store_joint[str(s)][m] for m in methods[:2])]
        feature_pass=bool(ready and all(v is not None for v in primary.values()) and all(primary['feature_on']<primary[m] for m in methods[:2]) and len(feature_improved)>=4)
        def scaled_group(rs):
            values={str(s):metrics([r for r in rs if r['store']==s],scales[s]) for s in active}
            return {m:.5*math.fsum(sum(values[str(s)][m][scope]['scaled_MSE'] for scope in ('daily','total')) for s in active)/5
              if all(values[str(s)][m][scope]['scaled_MSE'] is not None for s in active for scope in ('daily','total')) else None for m in methods}
        origins={str(d):scaled_group([r for r in rows if r['origin']==str(d)]) for d in dates}
        quarters={str(q):scaled_group([r for r in rows if (dt.date.fromisoformat(r['origin']).month-1)//3+1==q]) for q in range(1,5)}
        zero_diag={str(s):{'positive_observed_targets':sum(a is not None and a>0 for r in rows if r['store']==s for a in r['actual']),
          'zero_observed_targets':sum(a==0 for r in rows if r['store']==s for a in r['actual']),
          'missing_targets':sum(a is None for r in rows if r['store']==s for a in r['actual'])} for s in zero}
        assert all((REPO/p).read_bytes()==raw for p,raw in sources.items())
        for mode,raw in weights.items():assert (prior/(mode+'-best.pt')).read_bytes()==raw
        checkpoint()
        result={'status':'complete','research_state':'PAUSED','adopted':False,'readiness_passed':ready,
          'model_transfer_progress':core_pass,'feature_input_progress':feature_pass,'primary_joint_macro_scaled_MSE':primary,
          'secondary_macro_scaled_MSE':secondary,'per_store':by_store,'store_joint_MSE':store_joint,
          'core_improved_stores':core_improved,'feature_improved_stores':feature_improved,'support_counts':support_counts,
          'origin_joint_MSE':origins,'quarter_joint_MSE':quarters,'zero_scale_diagnostics':zero_diag,
          'requested':len(rows),'model_supported':len(pending),'complete_label_windows':sum(r['complete_label'] for r in rows),
          'baseline_only_windows':sum(r['store'] in zero for r in rows),'new_profiles':len(profiles),
          'weight_pins':{m:pin(r) for m,r in weights.items()},'source_pins':{p:pin(r) for p,r in sources.items()},
          'new_training_or_checkpoint_selection':False,'evaluation_stores_in_fit_or_selection':False,
          'previously_read_public_series':True,'formal_permission':False,'2016_2017_reserved_holdout_read':False,
          'seconds':time.monotonic()-STARTED,'OS_peak_private_bytes':peak,'no_automatic_grid_or_extension':True}
        files.json('summary.json',result);status='complete'
        print(json.dumps({k:result[k] for k in ('status','research_state','readiness_passed','model_transfer_progress','feature_input_progress','primary_joint_macro_scaled_MSE','core_improved_stores','feature_improved_stores','requested','model_supported','seconds','OS_peak_private_bytes')}),flush=True)
    except BaseException as error:
        original=traceback.format_exc()
        try:
            files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':original,'research_state':'PAUSED'},True)
            if rows:files.json('failure-prediction-prefix.json',rows,True)
            if profiles:files.json('failure-profile-prefix.json',profiles,True)
        except BaseException as save_error:print('failure save error: '+repr(save_error),file=sys.stderr)
        raise
    finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True},status!='complete')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);run(parser.parse_args().output)
