"""Independent exact certificate checks. Never import or call the solver."""
import json
import math
import re
from fractions import Fraction


def rational(value):
    if type(value) is bool or type(value) not in (int,float,str,Fraction):raise ValueError('numeric type')
    if type(value) is float and not math.isfinite(value):raise ValueError('finite value')
    if type(value) is str and (len(value)>5000 or not re.fullmatch(r'-?[0-9]+(?:/[1-9][0-9]*)?',value)):
        raise ValueError('bounded rational encoding')
    result=Fraction(value)
    if max(result.numerator.bit_length(),result.denominator.bit_length())>8192:raise ValueError('bit limit')
    return result


def verify(problem,certificate):
    if len(json.dumps(certificate,sort_keys=True).encode())>512*1024:raise ValueError('certificate size')
    expected={'schema','beta','active','cuts','rounds','total_pivots','objective_J'}
    if type(certificate) is not dict or set(certificate)!=expected or certificate['schema']!='fraction-active-set-cuts-v1':
        raise ValueError('certificate schema')
    if type(certificate['beta']) is not list or len(certificate['beta'])!=3 or type(certificate['active']) is not list or len(certificate['active'])>3:
        raise ValueError('certificate dimensions')
    if type(certificate['cuts']) is not list or len(certificate['cuts'])>512:
        raise ValueError('cut limit')
    if type(certificate['rounds']) is not list or not 0<len(certificate['rounds'])<=64 or type(certificate['total_pivots']) is not int or not 0<certificate['total_pivots']<=65536:
        raise ValueError('iteration metadata')
    beta=list(map(rational,certificate['beta']))
    if type(problem) is not dict or set(problem)!={'rows'} or type(problem['rows']) is not list or not 0<len(problem['rows'])<=512:
        raise ValueError('problem schema')
    parsed={};Q={};fit_sum=Fraction(0);G=[[Fraction(i==j) for j in range(3)] for i in range(3)];c=[Fraction(0)]*3
    J=sum(v*v for v in beta);quarter_checks={}
    for r in problem['rows']:
        if type(r) is not dict or set(r)!={'key','quarter','B','Y','unit','x','fit_weight','risk_weight'}:
            raise ValueError('row schema')
        key=r['key'];q=r['quarter']
        if type(key) is not str or not key or key in parsed or type(q) is not int or q not in (1,2,3,4):raise ValueError('row identity')
        B,Y,u,w,v=map(rational,(r['B'],r['Y'],r['unit'],r['fit_weight'],r['risk_weight']))
        if min(B,Y,w)<0 or min(u,v)<=0:raise ValueError('row signs')
        x=r['x']
        if x is not None:
            if type(x) is not list or len(x)!=3:raise ValueError('feature dimensions')
            x=list(map(rational,x))
        if x is None or B==0:
            if w!=0:raise ValueError('fallback fit weight')
            x=None
        h=[u*t for t in x] if x is not None else [Fraction(0)]*3
        e=B-Y;p=B+sum(h[j]*beta[j] for j in range(3))
        if p<0:raise ValueError('negative training total')
        parsed[key]={'q':q,'B':B,'Y':Y,'h':h,'e':e,'v':v,'P':p}
        Q.setdefault(q,[]).append(key);fit_sum+=w
        if x is not None:
            target=(Y-B)/u;residual=target-sum(x[j]*beta[j] for j in range(3))
            J+=w*residual**2
            for j in range(3):
                c[j]+=w*x[j]*target
                for k in range(3):G[j][k]+=w*x[j]*x[k]
    if fit_sum!=1:raise ValueError('objective weights')
    for q,keys in Q.items():
        if sum(parsed[k]['v'] for k in keys)!=1:raise ValueError('risk weights')
        changes={}
        for name,s in (('under',-1),('over',1)):
            delta=sum(parsed[k]['v']*(max(s*(parsed[k]['P']-parsed[k]['Y']),0)-max(s*parsed[k]['e'],0)) for k in keys)
            if delta>0:raise ValueError('original hinge violation')
            changes[name]=str(delta)
        quarter_checks[str(q)]=changes
    if rational(certificate['objective_J'])!=J:raise ValueError('objective value')
    # G=I+positive semidefinite sum. Exact stationarity and nonnegative
    # multipliers on valid original-constraint lower bounds prove optimality.
    gradient=[sum(G[j][k]*beta[k] for k in range(3))-c[j] for j in range(3)]
    correction=[Fraction(0)]*3;dual_b=Fraction(0);facets=[]
    all_entries=[dict(c,dual='0') for c in certificate['cuts']]+certificate['active']
    registered={json.dumps(c,sort_keys=True) for c in certificate['cuts']}
    for index,entry in enumerate(all_entries):
        kind=entry.get('kind');dual=rational(entry.get('dual'))
        if dual<0:raise ValueError('negative dual')
        if kind=='nonnegative':
            if set(entry)!={'kind','key','dual'} or entry['key'] not in parsed:raise ValueError('nonnegative certificate')
            r=parsed[entry['key']];a=[-v for v in r['h']];b=r['B']
        elif kind=='hinge':
            if set(entry)!={'kind','quarter','side','selected','dual'}:raise ValueError('facet schema')
            q,s,selected=entry['quarter'],entry['side'],entry['selected']
            if type(q) is not int or q not in Q or type(s) is not int or s not in (-1,1) or type(selected) is not list:
                raise ValueError('facet identity')
            if any(type(k) is not str for k in selected) or len(set(selected))!=len(selected) or not set(selected)<=set(Q[q]):
                raise ValueError('invalid facet subset')
            if index>=len(certificate['cuts']) and json.dumps({k:v for k,v in entry.items() if k!='dual'},sort_keys=True) not in registered:
                raise ValueError('active facet not registered')
            # Any subset yields a valid affine lower bound, including ties.
            a=[sum(parsed[k]['v']*s*parsed[k]['h'][j] for k in selected) for j in range(3)]
            b=sum(parsed[k]['v']*max(s*parsed[k]['e'],0) for k in Q[q])-sum(parsed[k]['v']*s*parsed[k]['e'] for k in selected)
        else:raise ValueError('unknown facet kind')
        slack=b-sum(a[j]*beta[j] for j in range(3))
        if slack<0 or dual*slack!=0:raise ValueError('primal or complementarity')
        for j in range(3):correction[j]+=dual*a[j]
        dual_b+=dual*b
        if index>=len(certificate['cuts']):facets.append({'slack':str(slack),'dual':str(dual)})
    if any(gradient[j]+correction[j]!=0 for j in range(3)):raise ValueError('stationarity')
    # For q=c-A^Tλ, stationarity gives q=Gβ; evaluate the dual bound for J.
    constant=sum(rational(r['fit_weight'])*((rational(r['Y'])-rational(r['B']))/rational(r['unit']))**2 for r in problem['rows'] if r['x'] is not None and rational(r['B'])>0)
    dual_bound=constant-sum((c[j]-correction[j])*beta[j] for j in range(3))-2*dual_b
    if J!=dual_bound:raise ValueError('nonzero duality gap')
    return {'status':'exact_optimality_verified','beta':list(map(str,beta)),'objective_J':str(J),
            'dual_bound_J':str(dual_bound),'gap':'0','quarter_changes':quarter_checks,
            'active_facets':facets,'original_hinges_and_nonnegative_verified':True,
            'zero_beta':not any(beta),'nonzero_feasibility_not_decided_by_zero_result':True}
