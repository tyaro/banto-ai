"""Fixed saved-Q1 attribution, same metric weights and fixed p192 enclosures."""
from fractions import Fraction as F
from demand_bounded_metrics import FIT,METRICS,S,atoms,enclosure

def concentration(entities,a):
    positive={str(k):v['gross_positive'] for k,v in entities.items()}
    denlo=sum(int(v['lower_numerator']) for v in positive.values());denhi=sum(int(v['upper_numerator']) for v in positive.values())
    a.integer(denlo);a.integer(denhi)
    if denhi==0:return {'status':'no_positive_contribution','denominator_lower':str(denlo),'denominator_upper':str(denhi),'top1':None,'top3':None}
    if denlo<=0:return {'status':'denominator_unresolved','denominator_lower':str(denlo),'denominator_upper':str(denhi),'top1':None,'top3':None}
    ordered=sorted((k for k,v in positive.items() if int(v['upper_numerator'])>0),key=lambda k:int(positive[k]['lower_numerator']),reverse=True)
    def top(k):
        chosen=ordered[:k];rest=ordered[k:]
        if any(int(positive[x]['lower_numerator'])<=int(positive[y]['upper_numerator']) for x,y in zip(chosen,chosen[1:])) or (rest and int(positive[chosen[-1]]['lower_numerator'])<=max(int(positive[x]['upper_numerator']) for x in rest)):
            return {'status':'rank_unresolved_or_tied','entities':None,'share_lower':None,'share_upper':None}
        nlo=sum(int(positive[x]['lower_numerator']) for x in chosen);nhi=sum(int(positive[x]['upper_numerator']) for x in chosen)
        lower=a.value(F(nlo,denhi));upper=min(F(1),a.value(F(nhi,denlo)))
        return {'status':'certified','entities':chosen,'count':len(chosen),'share_lower':str(lower),'share_upper':str(upper),
            'share_display':float((lower+upper)/2)}
    return {'status':'positive_denominator_certified','basis':'positive_window_contributions','denominator_lower':str(denlo),'denominator_upper':str(denhi),'top1':top(1),'top3':top(3)}

def components(values,a):
    return {'windows':len(values),'positive_windows':sum(v>0 for v in values),'negative_windows':sum(v<0 for v in values),'zero_windows':sum(v==0 for v in values),
        'net':enclosure(values,a),'gross_positive':enclosure((max(v,F(0)) for v in values),a),'gross_negative':enclosure((max(-v,F(0)) for v in values),a)}

def within(inner,outer):
    return int(outer['lower_numerator'])<=int(inner['lower_numerator'])<=int(inner['upper_numerator'])<=int(outer['upper_numerator'])

def diagnose(forecasts,labels,group,mode,saved,a):
    if group not in ('Q1_all','Q1_normal') or mode not in ('observed','assumed_missing_zero'):raise ValueError('fixed Q1 groups/modes')
    selected=[f for f in forecasts if (int(f['origin'][5:7])-1)//3+1==1 and (group=='Q1_all' or f['origin']!='2014-01-01')]
    if len(selected)!=(70 if group=='Q1_all' else 60):raise ValueError('fixed Q1 support')
    bystore={s:[] for s in FIT};prepared=[]
    for f in selected:
        if not f['origin'].startswith('2014-'):raise ValueError('2014 only')
        actual=labels[f['key']][mode];loss=atoms(f,actual,a);prepared.append((f,actual,loss));bystore[f['store']].append(loss)
    counts={s:{m:sum(len(loss[m]) for loss in bystore[s]) for m in METRICS} for s in FIT}
    if any(v<=0 for d in counts.values() for v in d.values()):raise ValueError('all metric/store support')
    weighted={m:[] for m in METRICS};rows=[];store_values={s:{m:[] for m in METRICS} for s in FIT};origin_values={}
    for f,actual,loss in prepared:
        r={'key':f['key'],'store':f['store'],'origin':f['origin'],'feature_eligible':f['features'] is not None,'features':f['features'],'contributions':{},'canonical':None}
        origin_values.setdefault(f['origin'],{m:[] for m in METRICS})
        for m in METRICS:
            terms=[a.div(a.sub(c,b),10*counts[f['store']][m]) for b,c in loss[m]];weighted[m].extend(terms)
            delta=F(0)
            for term in terms:delta=a.add(delta,term)
            r['contributions'][m]=str(delta);store_values[f['store']][m].append(delta);origin_values[f['origin']][m].append(delta)
        if None not in actual:
            B=a.value(f['baseline_total']);C=a.value(f['candidate_total']);Y=a.canonical(actual);eb=a.sub(B,Y);change=a.sub(C,B);unit=a.mul(14,a.value(f['scale']))
            linear=a.div(a.mul(a.mul(2,eb),change),a.square(unit));quadratic=a.div(a.square(change),a.square(unit))
            raw_loss=a.sub(loss['total_MSE'][0][1],loss['total_MSE'][0][0]);assert a.add(linear,quadratic)==raw_loss
            raw_over=a.sub(loss['over'][0][1],loss['over'][0][0])
            r['canonical']={'B':str(B),'P':str(C),'Y':str(Y),'baseline_error':str(eb),'delta':str(change),
                'MSE_linear_change':str(linear),'MSE_quadratic_change':str(quadratic),'MSE_change':str(raw_loss),
                'MSE_worsening_type':('same_side_away' if a.mul(eb,change)>=0 else 'overshoot') if raw_loss>0 else 'not_worsening',
                'over_increase_type':('existing_over_extended' if eb>=0 else 'crossed_from_under') if raw_over>0 else 'not_increasing'}
        rows.append(r);a.checkpoint()
    result={'group':group,'mode':mode,'windows':len(rows),'store_support':{str(s):counts[s] for s in FIT},'metrics':{},'rows':rows}
    for m in METRICS:
        total=components([F(r['contributions'][m]) for r in rows],a)
        atomic=enclosure(weighted[m],a);assert atomic==saved['paired']['macro'][m]
        assert within(total['net'],atomic)
        stores={str(s):components(store_values[s][m],a) for s in FIT}
        for s in FIT:
            own=enclosure((a.mul(10,v) for v in store_values[s][m]),a)
            assert within(own,saved['paired']['per_store'][str(s)][m]);stores[str(s)]['store_mean_change']=own
        origins={o:components(v[m],a) for o,v in origin_values.items()}
        assert sum(int(v['net']['lower_numerator']) for v in stores.values())==int(total['net']['lower_numerator'])
        assert sum(int(v['net']['upper_numerator']) for v in origins.values())==int(total['net']['upper_numerator'])
        result['metrics'][m]={'total':total,'atomic_reconciliation':atomic,'stores':stores,'origins':origins,
            'store_concentration':concentration(stores,a),'origin_concentration':concentration(origins,a)}
    return result
