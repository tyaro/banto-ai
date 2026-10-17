"""Focused synthetic checks for the new real alarm/scorer path, no model run."""
from pathlib import Path
import sys,math,json,traceback
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files
from care_alarm import *
from care_learning import pinball_origin
from care_score import event_result,macro,freeze_units
from macos_demand_runtime import MacCheckpoint


def row(i,score,flags=15,time=None):
    return (0,i,i,i*600,(i+1)*600 if time is None else time,flags,0.,0.,0.,0.,0.,0.,float(score),float(score),*([0.]*9))


def main(output):
    out=Files(output);status='failed';check=MacCheckpoint(seconds=870);tests={}
    try:
        out.sources([Path(__file__),ROOT/'models/mini-transformer/care_alarm.py',ROOT/'models/mini-transformer/care_learning.py',ROOT/'models/mini-transformer/care_score.py',ROOT/'models/mini-transformer/care_learning_slot.py'])
        rs=[row(i,s) for i,s in enumerate([2,2,2,0,0,0])];ep=episodes(rs,'neural-common',1.)
        assert ep==[{'open':1800,'open_ordinal':2,'open_source_id':2,'close':3600,'reason':'three-nonexceedances'}]
        assert active_seconds(rs,'neural-common',ep)==1800 and eligible_seconds(rs,'neural-common')==3600
        tests['open_and_clear_at_third_availability_not_retroactive']=True
        assert not episodes([row(i,1.) for i in range(8)],'neural-common',1.)
        tests['threshold_is_strictly_greater']=True
        rs=[row(i,2.,0 if i==3 else 15) for i in range(7)];ep=episodes(rs,'neural-common',1.)
        assert [(e['open'],e['close']) for e in ep]==[(1800,2400),(4200,4800)]
        tests['missing_closes_at_last_eligible_plus600_resets_confirmation']=True
        rs=[row(i,2.,time=(i+1)*600+(3600 if i>=3 else 0)) for i in range(6)];ep=episodes(rs,'neural-common',1.)
        assert [(e['open'],e['close']) for e in ep]==[(1800,2400),(7200,7800)]
        tests['gap_is_not_alarm_exposure_and_requires_reconfirmation']=True
        assert not episodes([row(i,2.) for i in range(2)],'neural-common',1.)
        assert episodes([row(i,2.) for i in range(3)],'neural-common',1.)[0]['close']==2400
        tests['file_end_closes_and_next_file_starts_fresh']=True
        rs=[row(i,2.,13 if i<2 else 15) for i in range(5)]
        assert episodes(rs,'baseline-native',1.)[0]['open']==1800 and episodes(rs,'baseline-common',1.)[0]['open']==3000
        tests['native_and_common_have_independent_states_and_support']=True
        t=calibration_threshold([float(i) for i in range(1000)]);assert t['order_index']==994 and t['threshold']==994
        for scores in ([0.]*511,[0.]*511+[math.nan]):
            try:calibration_threshold(scores)
            except ValueError:pass
            else:raise AssertionError('invalid calibration accepted')
        tests['calibration_inverse_empirical_index_and_support']=True
        ep=[{'open':600,'close':3000}];r=event_result(ep,1200,3600);assert not r['hit'] and r['earliness']==0 and len(r['already_active_before_start'])==1
        r=event_result([{'open':3600,'close':4200}],1200,3600);assert r['hit'] and r['earliness']==0 and r['lead_proxy_seconds']==0
        tests['prior_active_not_primary_hit_miss_zero_end_boundary_inclusive']=True
        stats={'A':{'recall':1.,'false_episodes_per_1000_record_hours':None,'normal_alarm_fraction':None,'earliness':.5},'B':{'recall':0.,'false_episodes_per_1000_record_hours':2.,'normal_alarm_fraction':.1,'earliness':0.}}
        z=macro(stats);assert z['recall']==.5 and z['earliness']==.25 and z['false_episodes_per_1000_record_hours']==2
        tests['macro_uses_all_assets_with_relevant_class']=True
        p=[[[0.]*3 for h in range(32)] for v in range(3)];y=[[1.]*32 for v in range(3)]
        assert pinball_origin(p,y,[1.]*3)==.5
        tests['fixed_scale_pinball_target_lead_quantile_equal']=True
        assert PREDICTION.size==144 and VALIDATION.size==1544 and PREDICTION.unpack(PREDICTION.pack(*row(0,2.)))==row(0,2.)
        tests['portable_output_layout_roundtrip']=True
        for declaration in ({'unit_roots':[]},{'unit_roots':['/no-such-care-fold']*5}):
            try:freeze_units(declaration)
            except ValueError:pass
            else:raise AssertionError('incomplete/duplicate fold freeze accepted')
        tests['scoring_requires_five_distinct_complete_folds']=True
        out.json('checks.json',tests);out.json('summary.json',{'status':'complete','checks':len(tests),'real_training':False,'model_forward':False,'real_event_truth':False,'resources':check.check()});status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc(),'checks_completed':tests},True);raise
    finally:out.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
