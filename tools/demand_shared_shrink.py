"""Fixed sharing and baseline shrinkage; 2014-only descriptive stability study."""
import datetime as dt
import math
from collections import Counter, defaultdict
from demand_persistence import FIT, quarter, measure, side_bound, attach_reliability
from demand_persistence import candidates as persistent_candidates
from demand_persistence import choose as _old_choose
ORDER=('matched_mean28','pooled_shrink','partial_pool')
EPS=1e-24


def candidates(row):
    raw,trace=persistent_candidates(row)
    return {'matched_mean28':raw['matched_mean28'], 'pooled_shrink':raw['persistent_anchor'], 'partial_pool':raw['persistent_anchor']},trace


def concentration(energy):
    values=list(energy)
    total=math.fsum(values)
    return total*total/math.fsum(v*v for v in values) if total>0 else 0.


def summarize(samples):
    a=math.fsum(r['weight']*(r['D']/(14*r['scale']))**2 for r in samples)
    c=math.fsum(-r['weight']*r['e']*r['D']/(14*r['scale'])**2 for r in samples)
    energies=[r['weight']*(r['D']/(14*r['scale']))**2 for r in samples]
    by_store=defaultdict(list);by_origin=defaultdict(list)
    for r,v in zip(samples,energies):
        by_store[str(r['store'])].append(v);by_origin[r['origin']].append(v)
    stores={k:math.fsum(v) for k,v in by_store.items()};origins={k:math.fsum(v) for k,v in by_origin.items()}
    return {'energy':a,'covariance':c,'unconstrained':c/a if a>EPS else 0.,
            'energy_kish':concentration(energies),'store_energy_kish':concentration(stores.values()),'origin_energy_kish':concentration(origins.values()),
            'store_energy':stores,'origin_energy':origins,'complete_windows':len(samples),
            'nonzero_direction_windows':sum(abs(r['D'])>1e-8 for r in samples),
            'per_store':dict(Counter(str(r['store']) for r in samples))}


def fit_journal(journal, *, excluded_store=None, excluded_origin=None):
    """Reweight complete samples; leave-outs are sensitivity only, never validation."""
    grouped={};coeff={};details={}
    for q in range(1,5):
        rr=[];seen=set()
        for original in journal[str(q)]:
            r=dict(original);key=r['store'],r['origin']
            if key in seen:raise ValueError('duplicate sample')
            seen.add(key)
            day=dt.date.fromisoformat(r['origin'])
            if r['store'] not in FIT or day.year!=2014 or day+dt.timedelta(days=13)>=dt.date(2015,1,1) or quarter(r['origin'])!=q:raise ValueError('pre-2015 FIT calibration only')
            if any(not math.isfinite(r[k]) for k in ('e','D','scale')) or r['scale']<=0:raise ValueError('finite positive scale required')
            if r['store']==excluded_store or r['origin']==excluded_origin:continue
            rr.append(r)
        counts=Counter(r['store'] for r in rr)
        for r in rr:r['weight']=1/(len(counts)*counts[r['store']])
        grouped[str(q)]=rr;v=summarize(rr)
        under=side_bound(rr,-1) if rr else 1.;over=side_bound(rr,1) if rr else 1.
        mse=max(0.,2*v['covariance']/v['energy']) if v['energy']>EPS else 1.
        v.update(under_upper=under,over_upper=over,MSE_upper=mse,upper=min(1.,under,over,mse))
        details[str(q)]=v
    global_rows=[dict(r,weight=r['weight']/4) for rr in grouped.values() for r in rr]
    global_stats=summarize(global_rows);ng=global_stats['energy_kish']
    raw_global=max(0.,min(1.,global_stats['unconstrained'])) if global_stats['energy']>EPS else 0.
    g=ng/(ng+1)*raw_global
    for q,v in details.items():
        local=max(0.,min(1.,v['unconstrained']));n=v['energy_kish'];supported=v['energy']>EPS
        proposals={'matched_mean28':0.,'pooled_shrink':g if supported else 0.,'partial_pool':(n*local+g)/(n+2) if supported else 0.}
        coeff[q]={}
        for method,proposal in proposals.items():
            alpha=max(0.,min(v['upper'],proposal))
            changes={side:math.fsum(r['weight']*(max(sg*(r['e']+alpha*r['D']),0.)-max(sg*r['e'],0.)) for r in grouped[q]) for side,sg in (('under',-1.),('over',1.))}
            changes['MSE']=v['energy']*alpha**2-2*v['covariance']*alpha
            if changes['under']>1e-8 or changes['over']>1e-8 or changes['MSE']>1e-12:raise ValueError('quarter calibration guard failed')
            coeff[q][method]={'alpha':alpha,'proposal':proposal,'calibration_changes':changes}
        v['local_clipped']=local;v['old_reference_alpha']=max(0.,min(v['upper'],v['unconstrained'])) if supported else 0.
    return {'quarter_coefficients':coeff,'quarter_statistics':details,'global_statistics':global_stats,'global_proposal':raw_global,'global_shrunk':g,
            'fixed_shrink_constant':1.,'2015_used':False,'annual_coefficient_shared':False,'independent_sample_size_claim':False,
            'excluded_store':excluded_store,'excluded_origin':excluded_origin},grouped


def calibrate(rows):
    journal={str(q):[] for q in range(1,5)};seen=set()
    for r in rows:
        key=r['store'],r['origin'];day=dt.date.fromisoformat(r['origin'])
        if key in seen or r['store'] not in FIT or day.year!=2014 or day+dt.timedelta(days=13)>=dt.date(2015,1,1):raise ValueError('unique pre-2015 FIT calibration required')
        seen.add(key)
        if None in r['actual']:continue
        if len(r['actual'])!=14 or any(not math.isfinite(y) or y<0 for y in r['actual']):raise ValueError('real complete labels required')
        b=math.fsum(r['matched_mean28']);y=math.fsum(r['actual']);p=math.fsum(candidates(r)[0]['pooled_shrink'])
        journal[str(quarter(r['origin']))].append({'store':r['store'],'origin':r['origin'],'e':b-y,'D':p-b,'scale':r['scale'],'baseline_total':b,'actual_total':y,'raw_total':p})
    if any(set(r['store'] for r in rr)!=set(FIT) for rr in journal.values()):raise ValueError('main fit needs all stores in each Q')
    return fit_journal(journal)


def choices(row,policy):
    raw,_=candidates(row);b=row['matched_mean28'];result={}
    for m in ORDER:
        a=policy['quarter_coefficients'][str(quarter(row['origin']))][m]['alpha']
        if not math.isfinite(a) or not 0<=a<=1:raise ValueError('fixed convex coefficient required')
        result[m]=[(1-a)*x+a*y if good else 0. for x,y,good in zip(b,raw[m],row['open_mask'])]
    return result


def choose(groups):
    # Reuse the existing explicit three-risk rule without changing the pinned module globals.
    selected={};eligibility={}
    for q in range(1,5):
        group=groups[f'normal_Q{q}'];eligibility[str(q)]={}
        if set(group)!={'observed','assumed_missing_zero'}:raise ValueError('both scenarios required')
        for method in ORDER:
            reasons=[]
            for mode,scores in group.items():
                b,v=scores['matched_mean28'],scores[method]
                if not all(math.isfinite(x) for x in (v['macro']['total'],v['shortfall']['macro']['under'],v['shortfall']['macro']['over'])):raise ValueError('finite risks required')
                if v['macro']['total']>b['macro']['total']+1e-12:reasons.append(mode+'/total_MSE')
                for side in ('under','over'):
                    if v['shortfall']['macro'][side]>b['shortfall']['macro'][side]+1e-8:reasons.append(mode+'/'+side)
            eligibility[str(q)][method]={'eligible':not reasons,'reasons':reasons}
        best=ORDER[0]
        for method in ORDER:
            if eligibility[str(q)][method]['eligible'] and group['observed'][method]['macro']['total']<group['observed'][best]['macro']['total']-1e-12:best=method
        selected[str(q)]=best
    return {'selected_by_quarter':selected,'eligibility':eligibility,'2015_used':False,'newyear_used':False}


def influence(journal, calibration_keys, fixed_groups):
    main,_=fit_journal(journal)
    methods=('old_reference','pooled_shrink','partial_pool')
    def alpha(p,q,m):return p['quarter_statistics'][q]['old_reference_alpha'] if m=='old_reference' else p['quarter_coefficients'][q][m]['alpha']
    result=[]
    exclusions=[('store',st) for st in FIT]+[('origin',day) for day in sorted({d for st,d in calibration_keys})]
    for kind,value in exclusions:
        fold,rows=fit_journal(journal,**{'excluded_'+kind:value})
        removed=[r for rr in journal.values() for r in rr if r['store']==value] if kind=='store' else [r for rr in journal.values() for r in rr if r['origin']==value]
        entry={'kind':kind,'value':value,'complete_removed':len(removed),'informative_removed':sum(abs(r['D'])>1e-8 for r in removed),'policy':fold,'fixed_D_changes':{}}
        for group,rr in fixed_groups.items():
            entry['fixed_D_changes'][group]={}
            for m in methods:
                delta=[(alpha(fold,str(quarter(r['origin'])),m)-alpha(main,str(quarter(r['origin'])),m))*r['D'] for r in rr]
                informative=[d for r,d in zip(rr,delta) if abs(r['D'])>1e-8]
                entry['fixed_D_changes'][group][m]={'max_abs':max(map(abs,delta),default=0.),'RMS':math.sqrt(math.fsum(d*d for d in delta)/len(delta)) if delta else 0.,'nonzero_D_windows':len(informative),'nonzero_D_RMS':math.sqrt(math.fsum(d*d for d in informative)/len(informative)) if informative else 0.}
        result.append(entry)
    return {'interpretation':'influence only; correlated removals, not validation or independent examples','folds':result,'main_policy':main}
