"""Bounded exact single-season QP. Authorized invocation: synthetic problems only.

Concrete rows use x=features_exact=z, already multiplied by reliability r.
No consumer, dataset, file IO, encoder, or legacy optimizer dependency.
"""
import hashlib
import json
import re
from fractions import Fraction as F
from demand_bounded_metrics import Arithmetic

VERSION='weighted-single-season-active-set-v1'
LIMITS={'rows':512,'rounds':64,'cuts':512,'pivots':4096,'total_pivots':65536,'bits':8192,'certificate_bytes':512*1024}
FIELDS={'key','quarter','B','Y','unit','x','fit_weight','risk_weight'}
class SolverFailure(RuntimeError):pass

def pin(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

class Budget(Arithmetic):
    def __init__(self,limits=None,checkpoint=lambda:None,event=lambda x:None):
        super().__init__(checkpoint);self.limits=dict(LIMITS);self.pivots=0;self.operations=0;self.event=event
        for k,v in (limits or {}).items():
            if k not in LIMITS or type(v) is not int or not 0<v<=LIMITS[k]:raise ValueError('limits may only tighten')
            self.limits[k]=v
    def integer(self,value):
        if type(value) is not int:raise ValueError('integer required')
        bits=abs(value).bit_length();self.max_bits=max(self.max_bits,bits);self.operations+=1
        if bits>self.limits['bits']:raise SolverFailure('integer_bit_limit')
        if self.operations%128==0:self.checkpoint()
        return value
    def imul(self,a,b):
        self.integer(a);self.integer(b)
        if a and b and abs(a).bit_length()+abs(b).bit_length()-1>self.limits['bits']:raise SolverFailure('integer_product_bit_limit')
        return self.integer(a*b)
    def read(self,value):
        if type(value) is not str or len(value)>4937 or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?',value):raise ValueError('canonical rational string required')
        if any(len(s.lstrip('-'))>2467 for s in value.split('/')):raise ValueError('rational token limit')
        v=self.value(value)
        if str(v)!=value:raise ValueError('noncanonical rational')
        return v
    def cmp(self,a,b):
        a=self.value(a);b=self.value(b);x=self.imul(a.numerator,b.denominator);y=self.imul(b.numerator,a.denominator)
        return (x>y)-(x<y)
    def sum(self,values):
        out=F()
        for v in values:out=self.add(out,v)
        return out
    def dot(self,left,right):
        if len(left)!=len(right):raise ValueError('dot dimensions')
        return self.sum(self.mul(x,y) for x,y in zip(left,right))
    def positive(self,x):return self.value(x) if self.cmp(x,0)>0 else F()

def parse(problem,a):
    if type(problem) is not dict or set(problem)!={'rows'} or type(problem['rows']) is not list:raise ValueError('concrete rows only')
    if not 0<len(problem['rows'])<=a.limits['rows']:raise SolverFailure('row_limit')
    out=[];keys=set();quarters=set()
    for row in problem['rows']:
        a.checkpoint()
        if type(row) is not dict or set(row)!=FIELDS:raise ValueError('row schema')
        key,q=row['key'],row['quarter']
        if type(key) is not str or not 0<len(key)<=128 or key in keys or type(q) is not int or q not in (1,2,3,4):raise ValueError('row identity')
        keys.add(key);quarters.add(q);vals={k:a.read(row[k]) for k in ('B','Y','unit','fit_weight','risk_weight')}
        if any(a.cmp(vals[k],0)<0 for k in ('B','Y','fit_weight')) or any(a.cmp(vals[k],0)<=0 for k in ('unit','risk_weight')):raise ValueError('row signs')
        x=row['x']
        if x is not None and (type(x) is not list or len(x)!=3):raise ValueError('three features or None')
        x=None if x is None else [a.read(v) for v in x]
        if x is None or vals['B']==0:
            if vals['fit_weight']!=0:raise ValueError('fallback fit weight')
            x=None
        elif a.cmp(vals['fit_weight'],0)<=0:raise ValueError('old E requires positive fit weight including r0')
        h=[F()]*3 if x is None else [a.mul(vals['unit'],v) for v in x]
        out.append({'key':key,'quarter':q,**vals,'x':x,'h':h,'e':a.sub(vals['B'],vals['Y'])})
    if len(quarters)!=1:raise ValueError('single own quarter required')
    if a.sum(r['fit_weight'] for r in out)!=1 or a.sum(r['risk_weight'] for r in out)!=1:raise ValueError('original weights sum one')
    return out

def objective(rows,a):
    G=[[F(i==j) for j in range(3)] for i in range(3)];rhs=[F()]*3;C=F()
    for row in rows:
        if row['x'] is None:continue
        t=a.div(-row['e'],row['unit']);w=row['fit_weight'];x=row['x'];C=a.add(C,a.mul(w,a.square(t)))
        for j in range(3):
            rhs[j]=a.add(rhs[j],a.mul(w,a.mul(x[j],t)))
            for k in range(3):G[j][k]=a.add(G[j][k],a.mul(w,a.mul(x[j],x[k])))
    return G,rhs,C

def eliminate(A,b,a):
    n=len(b)
    if not 1<=n<=6 or len(A)!=n or any(len(row)!=n for row in A):raise ValueError('KKT dimensions')
    M=[list(row)+[v] for row,v in zip(A,b)]
    for k in range(n):
        a.checkpoint();pivot=next((i for i in range(k,n) if M[i][k]),None)
        if pivot is None:raise SolverFailure('singular_KKT')
        M[k],M[pivot]=M[pivot],M[k];v=M[k][k];M[k]=[a.div(x,v) for x in M[k]]
        for i in range(n):
            if i==k:continue
            v=M[i][k];M[i]=[a.sub(x,a.mul(v,y)) for x,y in zip(M[i],M[k])]
    return [row[-1] for row in M]

def rank(normals,a):
    M=[list(row) for row in normals];p=0
    for k in range(3):
        pivot=next((i for i in range(p,len(M)) if M[i][k]),None)
        if pivot is None:continue
        M[p],M[pivot]=M[pivot],M[p];v=M[p][k];M[p]=[a.div(x,v) for x in M[p]]
        for i in range(p+1,len(M)):
            v=M[i][k];M[i]=[a.sub(x,a.mul(v,y)) for x,y in zip(M[i],M[p])]
        p+=1
    return p

def cycle(beta,working,seen):
    state=(tuple(beta),tuple(working))
    if state in seen:raise SolverFailure('active_set_cycle_undetermined')
    seen.add(state)

def linear_qp(G,rhs,constraints,a,round_number):
    beta=[F()]*3;working=[];seen=set()
    if any(a.cmp(c['b'],0)<0 for c in constraints):raise SolverFailure('zero_not_feasible')
    for pivot in range(a.limits['pivots']):
        a.checkpoint();a.pivots+=1
        if a.pivots>a.limits['total_pivots']:raise SolverFailure('total_pivot_limit')
        cycle(beta,working,seen);grad=[a.sub(a.dot(row,beta),v) for row,v in zip(G,rhs)];normals=[constraints[i]['a'] for i in working]
        if any(a.dot(constraints[i]['a'],beta)!=constraints[i]['b'] for i in working):raise SolverFailure('working_not_active')
        if rank(normals,a)!=len(working):raise SolverFailure('dependent_working_set')
        K=[G[j]+[n[j] for n in normals] for j in range(3)]+[n+[F()]*len(working) for n in normals]
        sol=eliminate(K,[-x for x in grad]+[F()]*len(working),a);p,dual=sol[:3],sol[3:]
        if any(a.dot(n,p) for n in normals):raise SolverFailure('non_tangent_direction')
        state={'event':'pivot','round':round_number,'pivot':pivot+1,'total_pivots':a.pivots,'beta':list(map(str,beta)),'working':list(working),'gradient':list(map(str,grad)),'direction':list(map(str,p)),'dual':list(map(str,dual))}
        if not any(p):
            bad=[i for i,v in zip(working,dual) if a.cmp(v,0)<0]
            state['action']='remove' if bad else 'linear_optimum';state['remove']=min(bad) if bad else None;a.event(state)
            if not bad:return beta,[(i,v) for i,v in zip(working,dual) if v],pivot+1
            working.remove(min(bad));continue
        step=F(1);block=None
        for i,c in enumerate(constraints):
            ap=a.dot(c['a'],p)
            if a.cmp(ap,0)<=0:continue
            t=a.div(a.sub(c['b'],a.dot(c['a'],beta)),ap)
            if a.cmp(t,0)<0:raise SolverFailure('lost_primal_feasibility')
            comparison=a.cmp(t,step)
            if a.cmp(t,1)<0 and (comparison<0 or comparison==0 and (block is None or i<block)):step,block=t,i
        next_beta=[a.add(b,a.mul(step,d)) for b,d in zip(beta,p)]
        state.update({'action':'step','step':str(step),'block':block,'next_beta':list(map(str,next_beta))});a.event(state);beta=next_beta
        if block is not None:
            if block in working or len(working)>=3 or rank(normals+[constraints[block]['a']],a)!=len(working)+1:raise SolverFailure('dependent_blocker_undetermined')
            working.append(block);working.sort()
        if any(a.cmp(a.dot(c['a'],beta),c['b'])>0 for c in constraints):raise SolverFailure('lost_primal_feasibility')
    raise SolverFailure('pivot_limit_undetermined')

def facet(rows,side,selected,a):
    if type(side) is not int or side not in (-1,1) or type(selected) is not list or len(set(selected))!=len(selected) or not set(selected)<={r['key'] for r in rows}:raise ValueError('facet subset')
    chosen=set(selected);normal=[a.sum(a.mul(r['risk_weight'],a.mul(side,r['h'][j])) for r in rows if r['key'] in chosen) for j in range(3)]
    base=a.sum(a.mul(r['risk_weight'],a.positive(a.mul(side,r['e']))) for r in rows)
    offset=a.sum(a.mul(r['risk_weight'],a.mul(side,r['e'])) for r in rows if r['key'] in chosen);bound=a.sub(base,offset)
    if a.cmp(bound,0)<0:raise SolverFailure('facet_zero_infeasible')
    return {'a':normal,'b':bound,'kind':'hinge','quarter':rows[0]['quarter'],'side':side,'selected':sorted(chosen)}

def descriptor(c):return {k:v for k,v in c.items() if k not in ('a','b')}

def solve_artificial_problem(problem,*,limits=None,checkpoint=lambda:None,event=lambda x:None):
    a=Budget(limits,checkpoint,event);a.event({'event':'start','problem_pin':pin(problem),'limits':a.limits});rows=parse(problem,a);G,rhs,C=objective(rows,a)
    constraints=[{'a':[-v for v in r['h']],'b':r['B'],'kind':'nonnegative','key':r['key']} for r in rows] # Include fallback/zero normals in full feasibility.
    a.event({'event':'objective','G':[[str(x) for x in row] for row in G],'rhs':list(map(str,rhs)),'C':str(C)})
    cuts=0;signatures=set();journal=[]
    for round_index in range(a.limits['rounds']):
        beta,dual,pivots=linear_qp(G,rhs,constraints,a,round_index+1);additions=[];changes={}
        for side in (-1,1):
            delta=a.sum(a.mul(r['risk_weight'],a.sub(a.positive(a.mul(side,a.add(r['e'],a.dot(r['h'],beta)))),a.positive(a.mul(side,r['e'])))) for r in rows);changes[str(side)]=str(delta)
            if a.cmp(delta,0)>0:
                selected=[r['key'] for r in rows if a.cmp(a.mul(side,a.add(r['e'],a.dot(r['h'],beta))),0)>0];cut=facet(rows,side,selected,a);signature=(side,tuple(cut['selected']))
                if signature in signatures or not any(cut['a']):raise SolverFailure('repeated_or_zero_violated_cut_undetermined')
                signatures.add(signature);additions.append(cut)
        journal.append({'round':round_index+1,'pivots':pivots,'new_cuts':len(additions)});a.event({'event':'round','round':round_index+1,'beta':list(map(str,beta)),'changes':changes,'additions':[{**descriptor(c),'normal':list(map(str,c['a'])),'bound':str(c['b'])} for c in additions]})
        if not additions:
            J=a.sub(a.add(C,a.dot(beta,[a.dot(row,beta) for row in G])),a.mul(2,a.dot(rhs,beta)))
            cert={'schema':VERSION,'problem_pin':pin(problem),'beta':list(map(str,beta)),'dual_convention':'J:2Gbeta-2rhs+ATdual=0','active':[{**descriptor(constraints[i]),'dual':str(a.mul(2,v))} for i,v in dual],
                  'cuts':[descriptor(c) for c in constraints if c['kind']=='hinge'],'rounds':journal,'total_pivots':a.pivots,'objective_J':str(J),'max_bits':a.max_bits,'limits':dict(a.limits)}
            if pin(cert)['bytes']>a.limits['certificate_bytes']:raise SolverFailure('certificate_size_limit')
            a.event({'event':'candidate_certificate','certificate':cert});return cert
        cuts+=len(additions)
        if cuts>a.limits['cuts']:raise SolverFailure('cut_limit_undetermined')
        constraints.extend(additions)
    raise SolverFailure('round_limit_undetermined')
