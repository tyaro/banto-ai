"""Two completed hindcasts gate an uncalibrated annual anchor, before alpha fit."""
import datetime as dt
import math
from demand_autonomous_mean import FIT
from demand_shortfall_quantity import measure
from demand_seasonal_quantity import quarter
from demand_annual_anchor import side_bound
ORDER=('matched_mean28','validated_anchor','no_cross_anchor')
MD={'01-01','12-25'}

def annual_context(store,issue,history):
    if store not in FIT:raise ValueError('fixed store required before annual values')
    a=issue-dt.timedelta(days=364);dates=[a+dt.timedelta(days=j) for j in range(-28,14)]
    if any(day>=issue for day in dates):raise ValueError('annual feature reaches issue')
    values=[history[store].get(day) if dt.date(2013,1,1)<=day<dt.date(2015,1,1) else None for day in dates]
    return {'first':str(dates[0]),'annual_issue':str(a),'end_exclusive':str(a+dt.timedelta(days=14)),'values':values,'observed':[x is not None for x in values]}

def attach_reliability(row,history):
    store=row['store'];o=dt.date.fromisoformat(row['origin'])
    if store not in FIT or not dt.date(2014,1,1)<=o<dt.date(2016,1,1):raise ValueError('fixed store/development metadata required')
    current=annual_context(store,o,history)
    if 'annual_input' in row and row['annual_input']!=current:raise ValueError('saved current annual input changed')
    return dict(row,annual_input=current,reliability_input={str(lag):annual_context(store,o-dt.timedelta(days=lag),history) for lag in (14,28)})

def annual_anchor(base,mask,issue,data):
    a=issue-dt.timedelta(days=364)
    if data['first']!=str(a-dt.timedelta(days=28)) or data['annual_issue']!=str(a) or data['end_exclusive']!=str(a+dt.timedelta(days=14)) or a+dt.timedelta(days=14)>=issue:raise ValueError('annual dates changed')
    v=data['values']
    if len(base)!=14 or len(mask)!=14 or len(v)!=42 or data['observed']!=[x is not None for x in v]:raise ValueError('fixed calendar/mask required')
    for j,x in enumerate(v):
        day=a+dt.timedelta(days=j-28)
        if x is not None and not dt.date(2013,1,1)<=day<dt.date(2015,1,1):raise ValueError('annual observation outside allowed years')
        if x is not None and (not math.isfinite(x) or x<0):raise ValueError('nonnegative annual quantity required')
    if any(not math.isfinite(x) or x<0 or (not good and x!=0.) for x,good in zip(base,mask)):raise ValueError('matched baseline required')
    weekday=[[] for _ in range(7)]
    for j,x in enumerate(v[:28]):
        day=a+dt.timedelta(days=j-28)
        if x is not None and str(day)[5:] not in MD:weekday[day.weekday()].append(x)
    counts=[len(xs) for xs in weekday];positions=[j for j,good in enumerate(mask) if good];reasons=[]
    if min(counts)<3:reasons.append('annual_weekday_support')
    if any(v[28+j] is None for j in positions):reasons.append('annual_target_missing')
    if any(str(a+dt.timedelta(days=j))[5:] in MD for j in positions):reasons.append('annual_target_closure_mismatch')
    total=math.fsum(base);num=den=None;ratio=1.
    if not positions or total<=0:reasons.append('zero_current_total')
    if not reasons:
        num=math.fsum(v[28+j] for j in positions)
        den=math.fsum(math.fsum(weekday[(a+dt.timedelta(days=j)).weekday()])/counts[(a+dt.timedelta(days=j)).weekday()] for j in positions)
        if den<=0:reasons.append('zero_annual_reference')
        else:
            ratio=num/den
            if not math.isfinite(ratio) or not math.isfinite(total*ratio):reasons.append('nonfinite_annual_ratio')
    if reasons:ratio=1.
    forecast=[x*ratio if good else 0. for x,good in zip(base,mask)]
    return forecast,{'annual_input':data,'weekday_counts':counts,'paired_target_positions':positions,'numerator':num,'denominator':den,'ratio':ratio,'reasons':reasons,'supported':not reasons,'annual_difference':math.fsum(forecast)-total}

def candidates(row):
    s=row['store'];o=dt.date.fromisoformat(row['origin'])
    if s not in FIT or not dt.date(2014,1,1)<=o<dt.date(2016,1,1):raise ValueError('fixed store/development metadata required')
    values=row['past_original_quantity'];scale=row['scale']
    if len(values)!=56 or any(v is not None and (not math.isfinite(v) or v<0) for v in values) or not math.isfinite(scale) or scale<=0:raise ValueError('real past56 and positive model scale required')
    if row['past_original_observed']!=[v is not None for v in values]:raise ValueError('raw past observation mask changed')
    base=list(row['matched_mean28']);anchor,current=annual_anchor(base,row['open_mask'],o,row['annual_input']);blocks={}
    for lag in (14,28):
        issue=o-dt.timedelta(days=lag);ref=issue-dt.timedelta(days=28);start=28-lag;actual=values[56-lag:70-lag]
        weekday=[[] for _ in range(7)]
        for j,v in enumerate(values[start:start+28]):
            if v is not None:weekday[(ref+dt.timedelta(days=j)).weekday()].append(v)
        counts=[len(xs) for xs in weekday];mask=[str(issue+dt.timedelta(days=j))[5:] not in MD for j in range(14)];reasons=[]
        if min(counts)<3:reasons.append('retrospective_weekday_support')
        if None in actual:reasons.append('missing_actual')
        b=p=None;annual=None;errors=None;strict=no_cross=False
        if min(counts)>=3:
            b=[math.fsum(weekday[(issue+dt.timedelta(days=j)).weekday()])/counts[(issue+dt.timedelta(days=j)).weekday()] if good else 0. for j,good in enumerate(mask)]
            p,annual=annual_anchor(b,mask,issue,row['reliability_input'][str(lag)])
            if not annual['supported']:reasons.extend('hindcast_'+reason for reason in annual['reasons'])
            if None not in actual:
                y=math.fsum(actual);e=math.fsum(b)-y;z=math.fsum(p)-y
                errors={'baseline_error':e,'anchor_error':z,'baseline_MSE':(e/(14*scale))**2,'anchor_MSE':(z/(14*scale))**2,
                        'baseline_under':max(-e,0.),'anchor_under':max(-z,0.),'baseline_over':max(e,0.),'anchor_over':max(z,0.)}
                strict=not reasons and errors['anchor_MSE']<errors['baseline_MSE']-1e-12
                no_cross=strict and errors['anchor_under']<=errors['baseline_under']+1e-8 and errors['anchor_over']<=errors['baseline_over']+1e-8
        if not strict:reasons.append('no_strict_MSE_improvement')
        blocks[str(lag)]={'issue':str(issue),'reference_first':str(ref),'actual_end_exclusive':str(issue+dt.timedelta(days=14)),
                         'weekday_counts':counts,'actual':actual,'baseline':b,'anchor':p,'open_mask':mask,'annual':annual,'errors':errors,
                         'supported':all(reason not in reasons for reason in ('retrospective_weekday_support','missing_actual')) and annual is not None and annual['supported'],
                         'strict_improvement':strict,'no_cross':no_cross,'reasons':reasons}
    validated=current['supported'] and all(v['strict_improvement'] for v in blocks.values())
    conservative=validated and all(v['no_cross'] for v in blocks.values())
    trace={'current_annual':current,'blocks':blocks,'model_scale':scale,'first_input_day':str(o-dt.timedelta(days=56)),'last_input_exclusive':str(o),
           'validated_gate':validated,'no_cross_gate':conservative,'gate_uses_alpha':False}
    return {'matched_mean28':base,'validated_anchor':anchor if validated else list(base),'no_cross_anchor':anchor if conservative else list(base)},trace


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
