"""Bounded exact 3D ridge QP; consumes concrete rows, never paths or readers.

Only synthetic fixtures are authorized by the accompanying numerical contract.
"""
import json
import math
import re
from collections import Counter
from fractions import Fraction as F

VERSION = 'fraction-active-set-cuts-v1'
LIMITS = {'rows':512, 'rounds':64, 'cuts':512, 'pivots':4096,
          'total_pivots':65536, 'bits':8192, 'certificate_bytes':512*1024}


class NumericFailure(RuntimeError):
    pass


def number(v):
    if type(v) is bool or type(v) not in (int,float,str,F):
        raise ValueError('finite rational number required')
    if type(v) is float and not math.isfinite(v):
        raise ValueError('finite number required')
    if type(v) is str and (len(v)>5000 or re.fullmatch(r'-?[0-9]+(?:/[1-9][0-9]*)?',v) is None):
        raise ValueError('bounded integer or rational string required')
    return F(v)


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)),F(0))


class Budget:
    def __init__(self, limits=None, checkpoint=None):
        self.limits=dict(LIMITS)
        for k,v in (limits or {}).items():
            if k not in self.limits or type(v) is not int or not 0<v<=self.limits[k]:
                raise ValueError('limits may only be tightened')
            self.limits[k]=v
        self.checkpoint=checkpoint or (lambda:None)
        self.pivots=0

    def check(self,*values):
        self.checkpoint()
        def walk(x):
            if isinstance(x,(list,tuple)):
                for v in x:walk(v)
            elif isinstance(x,F) and max(x.numerator.bit_length(),x.denominator.bit_length())>self.limits['bits']:
                raise NumericFailure('bit_length_limit')
        for v in values:walk(v)


def parse_rows(problem,budget):
    if type(problem) is not dict or set(problem)!={'rows'} or type(problem['rows']) is not list:
        raise ValueError('only concrete rows are accepted')
    if not 0<len(problem['rows'])<=budget.limits['rows']:
        raise NumericFailure('row_limit')
    rows=[];keys=set()
    for row in problem['rows']:
        if type(row) is not dict or set(row)!={'key','quarter','B','Y','unit','x','fit_weight','risk_weight'}:
            raise ValueError('exact numeric row schema required')
        if type(row['key']) is not str or not row['key'] or row['key'] in keys or type(row['quarter']) is not int or row['quarter'] not in (1,2,3,4):
            raise ValueError('unique key and quarter required')
        keys.add(row['key'])
        vals={k:number(row[k]) for k in ('B','Y','unit','fit_weight','risk_weight')}
        if min(vals['B'],vals['Y'],vals['fit_weight'])<0 or vals['unit']<=0 or vals['risk_weight']<=0:
            raise ValueError('nonnegative quantity and positive scale/risk weight required')
        x=row['x']
        if x is not None and (type(x) is not list or len(x)!=3):
            raise ValueError('three features or None required')
        x=None if x is None else list(map(number,x))
        if x is None or vals['B']==0:
            if vals['fit_weight']!=0:raise ValueError('fallback cannot enter fit objective')
            x=None
        h=[v*vals['unit'] for v in x] if x is not None else [F(0)]*3
        rows.append({**row,**vals,'x':x,'h':h,'e':vals['B']-vals['Y']})
        budget.check(list(vals.values()),x,h)
    if sum(r['fit_weight'] for r in rows)!=1:
        raise ValueError('fit weights must sum exactly to one')
    for q in {r['quarter'] for r in rows}:
        if sum(r['risk_weight'] for r in rows if r['quarter']==q)!=1:
            raise ValueError('each quarter risk weights must sum exactly to one')
    return rows


def objective(rows,budget):
    G=[[F(i==j) for j in range(3)] for i in range(3)]
    rhs=[F(0)]*3;constant=F(0)
    for r in rows:
        if r['x'] is None:continue
        x=r['x'];w=r['fit_weight'];target=-r['e']/r['unit']
        constant+=w*target*target
        for i in range(3):
            rhs[i]+=w*x[i]*target
            for j in range(3):G[i][j]+=w*x[i]*x[j]
    budget.check(G,rhs,constant)
    return G,rhs,constant


def linear_solve(A,b,budget):
    n=len(b);a=[list(row)+[v] for row,v in zip(A,b)]
    for k in range(n):
        pivot=next((i for i in range(k,n) if a[i][k]),None)
        if pivot is None:raise NumericFailure('singular_KKT')
        a[k],a[pivot]=a[pivot],a[k]
        v=a[k][k];a[k]=[z/v for z in a[k]]
        for i in range(n):
            if i!=k:
                v=a[i][k];a[i]=[z-v*t for z,t in zip(a[i],a[k])]
        budget.check(a)
    return [row[-1] for row in a]


def cycle_key(beta,working,seen):
    key=(tuple(beta),tuple(working))
    if key in seen:raise NumericFailure('active_set_cycle')
    seen.add(key)


def linear_qp(G,rhs,constraints,budget):
    beta=[F(0)]*3;working=[];seen=set()
    if any(c['b']<0 for c in constraints):raise NumericFailure('known_zero_not_feasible')
    for pivot in range(budget.limits['pivots']):
        budget.pivots+=1
        if budget.pivots>budget.limits['total_pivots']:raise NumericFailure('total_pivot_limit')
        cycle_key(beta,working,seen);budget.check(beta)
        grad=[dot(row,beta)-v for row,v in zip(G,rhs)]
        normals=[constraints[i]['a'] for i in working]
        if any(dot(constraints[i]['a'],beta)!=constraints[i]['b'] for i in working):
            raise NumericFailure('inactive_working_constraint')
        K=[G[i]+[a[i] for a in normals] for i in range(3)]
        K += [a+[F(0)]*len(working) for a in normals]
        sol=linear_solve(K,[-v for v in grad]+[F(0)]*len(working),budget)
        p=sol[:3];dual=sol[3:]
        if any(dot(a,p) for a in normals):raise NumericFailure('non_tangent_direction')
        if not any(p):
            bad=[working[j] for j,v in enumerate(dual) if v<0]
            if not bad:
                return beta,[(i,v) for i,v in zip(working,dual) if v],pivot+1
            working.remove(min(bad));continue
        candidates=[]
        for i,c in enumerate(constraints):
            ap=dot(c['a'],p)
            if ap>0:
                t=(c['b']-dot(c['a'],beta))/ap
                if t<0:raise NumericFailure('lost_primal_feasibility')
                if t<1:candidates.append((t,i))
        step,block=min(candidates) if candidates else (F(1),None)
        beta=[b+step*v for b,v in zip(beta,p)]
        if block is not None:
            if block in working or len(working)>=3:raise NumericFailure('dependent_working_set')
            working.append(block);working.sort()
        if any(dot(c['a'],beta)>c['b'] for c in constraints):raise NumericFailure('lost_primal_feasibility')
    raise NumericFailure('pivot_limit')


def facet(rows,q,side,selected):
    chosen=set(selected);rr=[r for r in rows if r['quarter']==q]
    if not chosen<=set(r['key'] for r in rr):raise ValueError('cut outside quarter')
    baseline=sum(r['risk_weight']*max(side*r['e'],0) for r in rr)
    a=[sum(r['risk_weight']*side*r['h'][j] for r in rr if r['key'] in chosen) for j in range(3)]
    b=baseline-sum(r['risk_weight']*side*r['e'] for r in rr if r['key'] in chosen)
    return {'a':a,'b':b,'kind':'hinge','quarter':q,'side':side,'selected':sorted(chosen)}


def solve(problem,*,limits=None,checkpoint=None):
    budget=Budget(limits,checkpoint);rows=parse_rows(problem,budget)
    G,rhs,constant=objective(rows,budget)
    constraints=[{'a':[-v for v in r['h']],'b':r['B'],'kind':'nonnegative','key':r['key']} for r in rows if any(r['h'])]
    # Equal normals/bounds are harmless; the solver handles deterministic ties.
    cut_signatures=set();journal=[];cuts=0
    for round_index in range(budget.limits['rounds']):
        budget.check()
        beta,dual,pivots=linear_qp(G,rhs,constraints,budget)
        additions=[]
        for q in sorted({r['quarter'] for r in rows}):
            rr=[r for r in rows if r['quarter']==q]
            for side in (-1,1):
                changed=sum(r['risk_weight']*(max(side*(r['e']+dot(r['h'],beta)),0)-max(side*r['e'],0)) for r in rr)
                if changed>0:
                    chosen=[r['key'] for r in rr if side*(r['e']+dot(r['h'],beta))>0]
                    cut=facet(rows,q,side,chosen)
                    if not any(cut['a']):raise NumericFailure('zero_normal_violated_cut')
                    signature=(q,side,tuple(cut['selected']))
                    if signature in cut_signatures:raise NumericFailure('repeated_violated_cut')
                    cut_signatures.add(signature);additions.append(cut)
        journal.append({'round':round_index+1,'pivots':pivots,'new_cuts':len(additions)})
        if not additions:
            cert={'schema':VERSION,'beta':list(map(str,beta)),
                  'active':[{**{k:v for k,v in constraints[i].items() if k not in ('a','b')},'dual':str(v)} for i,v in dual],
                  'cuts':[{k:v for k,v in c.items() if k not in ('a','b')} for c in constraints if c['kind']=='hinge'],
                  'rounds':journal,'total_pivots':budget.pivots,
                  'objective_J':str(constant+dot(beta,[dot(r,beta) for r in G])-2*dot(rhs,beta))}
            if len(json.dumps(cert,sort_keys=True).encode())>budget.limits['certificate_bytes']:
                raise NumericFailure('certificate_size_limit')
            return cert
        cuts+=len(additions)
        if cuts>budget.limits['cuts']:raise NumericFailure('cut_limit')
        constraints.extend(additions)
        budget.check([c['a']+[c['b']] for c in additions])
    raise NumericFailure('round_limit')


def from_prefix(batch):
    # No file access. The existing adapter rejects future, partial, or forged rows.
    from demand_prefix_adapter import validate_batch
    from demand_input_boundary_v2 import FIT
    validate_batch(batch)
    eligible=[r for r in batch['rows'] if r['features'] is not None and math.fsum(r['baseline'])>0]
    quarter=lambda r:(int(r['origin'][5:7])-1)//3+1
    counts=Counter((quarter(r),r['store']) for r in eligible)
    complete=Counter((quarter(r),r['store']) for r in batch['rows'])
    if not all(counts[q,s]>0 for q in (1,2,3,4) for s in FIT):
        return {'supported':False,'reason':'missing_feature_store_quarter_cell','problem':None}
    rows=[]
    for r in batch['rows']:
        q=quarter(r);B=math.fsum(r['baseline']);x=r['features'] if B>0 else None
        rows.append({'key':r['key'],'quarter':q,'B':str(number(B)),'Y':str(number(math.fsum(r['raw_actual']))),
                     'unit':str(14*number(r['scale'])),'x':None if x is None else list(map(lambda x:str(number(x)),x)),
                     'fit_weight':str(F(1,40*counts[q,r['store']])) if x is not None else '0',
                     'risk_weight':str(F(1,10*complete[q,r['store']]))})
    return {'supported':True,'reason':None,'problem':{'rows':rows}}


def predict_total(baseline,unit,x,beta):
    B=sum(map(number,baseline),F(0))
    if B<0:raise ValueError('nonnegative baseline required')
    if B==0 or x is None:return B
    if len(x)!=3 or len(beta)!=3:raise ValueError('three features and coefficients required')
    return max(B+number(unit)*dot(list(map(number,x)),list(map(number,beta))),F(0))
