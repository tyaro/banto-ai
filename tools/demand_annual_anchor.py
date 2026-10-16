"""Past-only 52-week seasonal anchor and direction/cap confirmation."""
import datetime as dt
import math
from decimal import Decimal, localcontext
from demand_autonomous_mean import FIT
from demand_adaptive_consensus import candidates as old_candidates
from demand_shortfall_quantity import measure
from demand_seasonal_quantity import quarter
ORDER=('matched_mean28','annual_anchor','anchor_cap')
MD={'01-01','12-25'}

def sign(v):return 0 if abs(v)<=1e-8 else 1 if v>0 else -1

def attach_annual(row,history):
    s=row['store'];o=dt.date.fromisoformat(row['origin'])
    if s not in FIT or not '2014-01-01'<=row['origin']<'2016-01-01':raise ValueError('fixed store and development metadata required')
    a=o-dt.timedelta(days=364)
    dates=[a+dt.timedelta(days=j) for j in range(-28,14)]
    if any(day>=o for day in dates):raise ValueError('annual feature reaches current issue')
    values=[history[s].get(day) if dt.date(2013,1,1)<=day<dt.date(2015,1,1) else None for day in dates]
    return dict(row,annual_input={'first':str(dates[0]),'annual_issue':str(a),'end_exclusive':str(a+dt.timedelta(days=14)),
                                 'values':values,'observed':[v is not None for v in values]})

def candidates(row):
    b=list(row['matched_mean28']);mask=row['open_mask'];o=dt.date.fromisoformat(row['origin']);a=o-dt.timedelta(days=364);data=row['annual_input'];v=data['values']
    if row['store'] not in FIT or len(b)!=14 or len(mask)!=14 or len(v)!=42:raise ValueError('fixed store and horizon required')
    if data['first']!=str(a-dt.timedelta(days=28)) or data['annual_issue']!=str(a) or data['end_exclusive']!=str(a+dt.timedelta(days=14)) or a+dt.timedelta(days=14)>o:raise ValueError('annual feature dates changed')
    if data['observed']!=[x is not None for x in v] or any(x is not None and (not math.isfinite(x) or x<0) for x in v):raise ValueError('real annual observation mask required')
    if any(not math.isfinite(x) or x<0 or (not good and x!=0.) for x,good in zip(b,mask)):raise ValueError('matched nonnegative baseline required')
    weekday=[[] for _ in range(7)]
    for j,x in enumerate(v[:28]):
        day=a-dt.timedelta(days=28-j)
        if x is not None and str(day)[5:] not in MD:weekday[day.weekday()].append(x)
    counts=[len(xs) for xs in weekday];reasons=[]
    if min(counts)<3:reasons.append('annual_weekday_support')
    indices=[j for j,good in enumerate(mask) if good]
    if any(v[28+j] is None for j in indices):reasons.append('annual_target_missing')
    if any(str(a+dt.timedelta(days=j))[5:] in MD for j in indices):reasons.append('annual_target_closure_mismatch')
    total=math.fsum(b);den=num=None;ratio=1.
    if not indices or total<=0:reasons.append('zero_current_total')
    if not reasons:
        den=math.fsum(math.fsum(weekday[(a+dt.timedelta(days=j)).weekday()])/counts[(a+dt.timedelta(days=j)).weekday()] for j in indices)
        num=math.fsum(v[28+j] for j in indices)
        if den<=0:reasons.append('zero_annual_reference')
        else:
            ratio=num/den
            if not math.isfinite(ratio) or not math.isfinite(total*ratio):reasons.append('nonfinite_annual_ratio')
    if reasons:ratio=1.
    anchor=[x*ratio if good else 0. for x,good in zip(b,mask)]
    old,old_trace=old_candidates(row);old_diff=math.fsum(old['consensus_raw'])-total;anchor_diff=math.fsum(anchor)-total
    agree=not reasons and sign(old_diff)!=0 and sign(old_diff)==sign(anchor_diff)
    cap_diff=sign(anchor_diff)*min(abs(old_diff),abs(anchor_diff)) if agree else 0.
    capped=[x*((total+cap_diff)/total) if good and total>0 else 0. for x,good in zip(b,mask)]
    trace={'annual_input':data,'weekday_counts':counts,'paired_target_positions':indices,'numerator':num,'denominator':den,'ratio':ratio,'reasons':reasons,
           'supported':not reasons,'annual_difference':anchor_diff,'old_raw_difference':old_diff,'cap_difference':cap_diff,'direction_agrees':agree,'old_consensus':old_trace}
    return {'matched_mean28':b,'annual_anchor':anchor,'anchor_cap':capped},trace

def side_bound(samples,sg):
    with localcontext() as ctx:
        ctx.prec=80
        data=[(Decimal(str(r['weight'])),Decimal(str(r['e'])),Decimal(str(r['D']))) for r in samples]
        points=sorted({Decimal(0),Decimal(1),*(-e/d for w,e,d in data if d and 0<-e/d<1)})
        excess=lambda alpha:sum((w*(max(sg*(e+alpha*d),0)-max(sg*e,0)) for w,e,d in data),Decimal(0))
        before=Decimal(0);previous=Decimal(0);upper=Decimal(1)
        for point in points[1:]:
            after=excess(point)
            if after>0:
                upper=previous+(point-previous)*(-before)/(after-before);break
            previous,before=point,after
        result=float(upper)
        if result>0:result=math.nextafter(result,0.)
        return result

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
