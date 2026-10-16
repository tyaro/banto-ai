"""Pre-issue level and weekly change corroborate an independently validated year anchor."""
import datetime as dt
import math
from demand_annual_reliability_v2 import FIT, measure, quarter, side_bound, attach_reliability, MD
from demand_annual_reliability_v2 import candidates as reliability_candidates
ORDER=('matched_mean28','aligned_anchor','aligned_cap')

def sign(value):return 0 if abs(value)<=1e-8 else 1 if value>0 else -1

def candidates(row):
    old,prior=reliability_candidates(row)
    o=dt.date.fromisoformat(row['origin']);values=row['past_original_quantity'];base=list(row['matched_mean28']);mask=row['open_mask']
    previous=values[-14:-7];recent=values[-7:]
    prevdates=[o-dt.timedelta(days=14-j) for j in range(7)];dates=[o-dt.timedelta(days=7-j) for j in range(7)]
    pairs=[a is not None and b is not None and str(da)[5:] not in MD and str(db)[5:] not in MD for a,b,da,db in zip(previous,recent,prevdates,dates)]
    total=math.fsum(base);t7=level=trend=None
    if all(pairs):
        t7=math.fsum(recent[j%7] for j,good in enumerate(mask) if good);level=t7-total
        trend=math.fsum(b-a for a,b in zip(previous,recent))
    year=prior['current_annual']['annual_difference'];reasons=[]
    if not prior['no_cross_gate']:reasons.append('past_no_cross_failed')
    if not all(pairs):reasons.append('latest_pair_support')
    if all(pairs):
        if 0 in (sign(year),sign(level),sign(trend)):reasons.append('zero_alignment_signal')
        if sign(year)!=sign(level):reasons.append('level_year_direction_disagreement')
        if sign(year)!=sign(trend):reasons.append('trend_year_direction_disagreement')
    aligned=not reasons
    cap=sign(year)*min(abs(year),abs(level)) if aligned else 0.
    endpoint=old['no_cross_anchor'] if aligned else list(base)
    capped=[b*((total+cap)/total) if good and total>0 else 0. for b,good in zip(base,mask)]
    trace={'prior_reliability':prior,'previous7':previous,'recent7':recent,'previous_dates':list(map(str,prevdates)),'recent_dates':list(map(str,dates)),
           'valid_pairs':pairs,'pair_count':sum(pairs),'latest14_replay':t7,'level_gap':level,'week_change':trend,'year_difference':year,
           'aligned_gate':aligned,'capped_difference':cap,'cap_reduced':aligned and abs(cap)<abs(year)-1e-8,'reasons':reasons,'gate_uses_alpha':False}
    return {'matched_mean28':base,'aligned_anchor':endpoint,'aligned_cap':capped},trace


def calibrate(rows):
    seen=set()
    for r in rows:
        if r['store'] not in FIT or not r['origin'].startswith('2014-') or dt.date.fromisoformat(r['origin'])+dt.timedelta(days=13)>=dt.date(2015,1,1):raise ValueError('observed pre-2015 FIT calibration required')
        k=r['store'],r['origin']
        if k in seen:raise ValueError('duplicate calibration')
        seen.add(k)
    coefficients={};journals={}
    for q in range(1,5):
        rr=[r for r in rows if quarter(r['origin'])==q and None not in r['actual']];counts={s:sum(r['store']==s for r in rr) for s in FIT}
        if any(n==0 for n in counts.values()):raise ValueError('all-store complete support required')
        coefficients[str(q)]={};journals[str(q)]={}
        for method in ORDER:
            samples=[]
            for r in rr:
                if len(r['actual'])!=14 or any(not math.isfinite(y) or y<0 for y in r['actual']) or not math.isfinite(r['scale']) or r['scale']<=0:raise ValueError('real labels and scale required')
                b=math.fsum(r['matched_mean28']);y=math.fsum(r['actual']);p=math.fsum(candidates(r)[0][method])
                samples.append({'store':r['store'],'origin':r['origin'],'e':b-y,'D':p-b,'weight':1/(10*counts[r['store']]),'scale':r['scale'],'baseline_total':b,'actual_total':y,'raw_total':p})
            a=math.fsum(v['weight']*(v['D']/(14*v['scale']))**2 for v in samples);c=math.fsum(-v['weight']*v['e']*v['D']/(14*v['scale'])**2 for v in samples)
            under=side_bound(samples,-1);over=side_bound(samples,1);mse_upper=max(0.,2*c/a) if a>1e-24 else 1.;upper=min(1.,under,over,mse_upper)
            alpha=max(0.,min(upper,c/a)) if a>1e-24 else 0.
            changes={side:math.fsum(v['weight']*(max(sg*(v['e']+alpha*v['D']),0.)-max(sg*v['e'],0.)) for v in samples) for side,sg in (('under',-1.),('over',1.))}
            changes['MSE']=a*alpha**2-2*c*alpha
            if changes['under']>1e-8 or changes['over']>1e-8 or changes['MSE']>1e-12:raise ValueError('calibration quarter constraint failed')
            nz=[r for r in samples if abs(r['D'])>1e-8]
            coefficients[str(q)][method]={'alpha':alpha,'energy':a,'covariance':c,'under_upper':under,'over_upper':over,'MSE_upper':mse_upper,'upper':upper,'unconstrained':c/a if a>1e-24 else 0.,'calibration_changes':changes,'complete_windows':len(samples),'per_store':{str(s):n for s,n in counts.items()},'nonzero_direction_windows':len(nz),'nonzero_direction_origins':sorted({r['origin'] for r in nz}),'nonzero_direction_stores':sorted({r['store'] for r in nz})}
            journals[str(q)][method]=samples
    return {'quarter_coefficients':coefficients,'observed_only':True,'2015_used':False,'annual_coefficient_shared':False},journals

def choices(row,policy):
    raw,_=candidates(row);b=row['matched_mean28'];result={}
    for m in ORDER:
        a=policy['quarter_coefficients'][str(quarter(row['origin']))][m]['alpha']
        if not math.isfinite(a) or not 0<=a<=1:raise ValueError('fixed convex quarter coefficient required')
        result[m]=[(1-a)*x+a*y if good else 0. for x,y,good in zip(b,raw[m],row['open_mask'])]
    return result


def choose(groups):
    selected, eligibility = {}, {}
    for q in range(1, 5):
        group = groups[f'normal_Q{q}']; eligibility[str(q)] = {}
        if set(group) != {'observed', 'assumed_missing_zero'}: raise ValueError('both label scenarios required')
        for method in ORDER:
            reasons = []
            for mode, scores in group.items():
                b, v = scores['matched_mean28'], scores[method]
                if not all(math.isfinite(x) for x in (v['macro']['total'], v['shortfall']['macro']['under'], v['shortfall']['macro']['over'])):
                    raise ValueError('finite quarter risks required')
                if v['macro']['total'] > b['macro']['total']+1e-12: reasons.append(mode+'/total_MSE')
                for side in ('under', 'over'):
                    if v['shortfall']['macro'][side] > b['shortfall']['macro'][side]+1e-8: reasons.append(mode+'/'+side)
            eligibility[str(q)][method] = {'eligible': not reasons, 'reasons': reasons}
        if not eligibility[str(q)]['matched_mean28']['eligible']: raise ValueError('baseline must be eligible')
        best = ORDER[0]
        for method in ORDER:
            if eligibility[str(q)][method]['eligible'] and group['observed'][method]['macro']['total'] < group['observed'][best]['macro']['total']-1e-12: best = method
        selected[str(q)] = best
    return {'selected_by_quarter': selected, 'eligibility': eligibility, '2015_used': False, 'newyear_used': False}
