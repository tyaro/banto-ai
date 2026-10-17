"""Fixed dyadic enclosures of unchanged exact loss terms; no optimizer import."""
import math
from fractions import Fraction as F

BITS=8192
P=192
S=1<<P
MAX_TERMS=8192
FIT=(6,7,10,13,15,17,19,23,26,27)
METRICS=('total_MSE','under','over','daily_MSE','quantity_MSE')
PASS=('equal','decreased','nonincreased')

class BoundFailure(RuntimeError):pass

class Arithmetic:
    def __init__(self,checkpoint=lambda:None):self.max_bits=0;self.checkpoint=checkpoint
    def integer(self,x):
        if type(x) is not int:raise ValueError('integer required')
        b=abs(x).bit_length();self.max_bits=max(self.max_bits,b)
        if b>BITS:raise BoundFailure('integer_bit_limit')
        return x
    def value(self,x):
        if isinstance(x,F):self.integer(x.numerator);self.integer(x.denominator);return x
        if type(x) is str:
            parts=x.split('/')
            if len(parts) not in (1,2) or any(len(a)>2468 or not a.lstrip('-').isdigit() for a in parts):raise ValueError('bounded rational text required')
            n=self.integer(int(parts[0]));d=self.integer(int(parts[1])) if len(parts)==2 else 1
            if d<=0:raise ValueError('positive denominator required')
            return F(n,d)
        if type(x) not in (int,float) or (type(x) is float and not math.isfinite(x)):raise ValueError('finite numeric required')
        if type(x) is int:self.integer(x)
        return self.value(F(x))
    def imul(self,a,b):
        self.integer(a);self.integer(b)
        # Reject before allocating an oversized product; exact borderline checked after.
        if a and b and abs(a).bit_length()+abs(b).bit_length()-1>BITS:raise BoundFailure('integer_product_bit_limit')
        return self.integer(a*b)
    def iadd(self,a,b):self.integer(a);self.integer(b);return self.integer(a+b)
    def add(self,a,b):
        a=self.value(a);b=self.value(b);g=math.gcd(a.denominator,b.denominator)
        left=self.imul(a.numerator,b.denominator//g);right=self.imul(b.numerator,a.denominator//g)
        return self.value(F(self.iadd(left,right),self.imul(a.denominator//g,b.denominator)))
    def sub(self,a,b):return self.add(a,-self.value(b))
    def mul(self,a,b):
        a=self.value(a);b=self.value(b);g=math.gcd(a.numerator,b.denominator);h=math.gcd(b.numerator,a.denominator)
        return self.value(F(self.imul(a.numerator//g,b.numerator//h),self.imul(a.denominator//h,b.denominator//g)))
    def div(self,a,b):
        b=self.value(b)
        if not b:raise ValueError('zero denominator')
        return self.mul(a,self.value(F(b.denominator,b.numerator)))
    def square(self,a):return self.mul(a,a)
    def canonical(self,values):
        if len(values)!=14 or any(self.value(v)<0 for v in values):raise ValueError('14 nonnegative actual values required')
        return self.value(math.fsum(values))


def decision(interval):
    lo=int(interval['lower_numerator']);hi=int(interval['upper_numerator'])
    if interval['nonzero_terms']==0 or lo==hi==0:return 'equal'
    if hi<0:return 'decreased'
    if hi==0:return 'nonincreased'
    if lo>0:return 'increased'
    return 'unresolved'


def enclosure(terms,arithmetic):
    """terms are already correctly weighted exact rationals."""
    lo=hi=n=nz=0
    for term in terms:
        n+=1
        if n>MAX_TERMS:raise BoundFailure('term_count_limit')
        t=arithmetic.value(term);nz+=t!=0
        scaled=arithmetic.imul(t.numerator,S)
        l=scaled//t.denominator;h=-((-scaled)//t.denominator)
        lo=arithmetic.iadd(lo,l);hi=arithmetic.iadd(hi,h)
    if n==0:raise ValueError('empty support')
    width=arithmetic.integer(hi-lo)
    assert 0<=width<=n
    middle=arithmetic.value(F(arithmetic.iadd(lo,hi),2*S))
    result={'precision_bits':P,'denominator':str(S),'lower_numerator':str(lo),'upper_numerator':str(hi),
        'terms':n,'nonzero_terms':nz,'width_units':width,'display_midpoint':float(middle)}
    result['decision']=decision(result)
    return result


def atoms(f,actual,a):
    if len(actual)!=14 or len(f['assumed_open_mask'])!=14:raise ValueError('14 days required')
    u=a.value(f['scale'])
    if u<=0:raise ValueError('positive scale')
    baseline=list(map(a.value,f['baseline']));candidate=list(map(a.value,f['candidate_daily_exact']))
    if len(baseline)!=14 or len(candidate)!=14:raise ValueError('14 predictions required')
    result={m:[] for m in METRICS}
    for b,c,y,opened in zip(baseline,candidate,actual,f['assumed_open_mask']):
        if b<0 or c<0 or (not opened and (b!=0 or c!=0)):raise ValueError('nonnegative masked prediction')
        if y is None:continue
        y=a.value(y)
        if y<0:raise ValueError('nonnegative actual')
        pair=(a.square(a.div(a.sub(b,y),u)),a.square(a.div(a.sub(c,y),u)))
        result['daily_MSE'].append(pair)
        if opened:result['quantity_MSE'].append(pair)
    if None not in actual:
        Y=a.canonical(actual);unit=a.mul(14,u);B=a.value(f['baseline_total']);C=a.value(f['candidate_total'])
        eb=a.sub(B,Y);ec=a.sub(C,Y)
        result['total_MSE']=[(a.square(a.div(eb,unit)),a.square(a.div(ec,unit)))]
        result['under']=[(max(-eb,F(0)),max(-ec,F(0)))]
        result['over']=[(max(eb,F(0)),max(ec,F(0)))]
    return result


def score_group(rows,mode,a):
    per={s:{m:[] for m in METRICS} for s in FIT}
    for r in rows:
        f=r['forecast']
        if f['store'] not in FIT:raise ValueError('FIT store required')
        values=atoms(f,r[mode],a)
        for m in METRICS:per[f['store']][m].extend(values[m])
        a.checkpoint()
    supports={str(s):{m:len(per[s][m]) for m in METRICS} for s in FIT}
    if any(not n for counts in supports.values() for n in counts.values()):raise ValueError('all ten stores require metric support')
    result={name:{'per_store':{},'macro':{}} for name in ('matched_mean28','candidate','paired')}
    for s in FIT:
        for name in result:result[name]['per_store'][str(s)]={}
        for m in METRICS:
            pairs=per[s][m];n=len(pairs)
            for name in result:
                terms=[b if name=='matched_mean28' else c if name=='candidate' else a.sub(c,b) for b,c in pairs]
                result[name]['per_store'][str(s)][m]=enclosure((a.div(t,n) for t in terms),a)
    for name in result:
        for m in METRICS:
            def weighted():
                for s in FIT:
                    pairs=per[s][m]
                    for b,c in pairs:
                        t=b if name=='matched_mean28' else c if name=='candidate' else a.sub(c,b)
                        yield a.div(t,10*len(pairs))
            result[name]['macro'][m]=enclosure(weighted(),a)
        result[name]['store_support']=supports
    decisions={m:result['paired']['macro'][m]['decision'] for m in ('total_MSE','under','over')}
    result['decisions']=decisions;result['violations']=[m for m,d in decisions.items() if d=='increased']
    result['unresolved']=[m for m,d in decisions.items() if d=='unresolved']
    result['eligible']=False if result['violations'] else None if result['unresolved'] else True
    result['windows']=len(rows)
    return result


def groups(rows):
    origin=lambda r:r['forecast']['origin'];q=lambda r:(int(origin(r)[5:7])-1)//3+1
    result={'all260':rows,'normal250':[r for r in rows if origin(r)!='2014-01-01'],
        'newyear10':[r for r in rows if origin(r)=='2014-01-01'],'yearend':[r for r in rows if origin(r).startswith('2014-12-')]}
    for season in range(1,5):
        result[f'Q{season}_all']=[r for r in rows if q(r)==season]
        result[f'Q{season}_normal']=[r for r in rows if q(r)==season and origin(r)!='2014-01-01']
    return result


def summarize(evaluation):
    mandatory=[f'Q{q}_{k}' for q in range(1,5) for k in ('all','normal')]+['newyear10']
    cells=[{'group':g,'mode':mode,'metric':m,'decision':evaluation[g][mode]['decisions'][m]}
        for g in mandatory for mode in ('observed','assumed_missing_zero') for m in ('total_MSE','under','over')]
    bad=[c for c in cells if c['decision']=='increased'];unknown=[c for c in cells if c['decision']=='unresolved']
    passed=False if bad else None if unknown else True
    annual={mode:evaluation['all260'][mode]['paired']['macro']['total_MSE']['decision'] for mode in ('observed','assumed_missing_zero')}
    return {'mandatory_pass':passed,'confirmed_violations':bad,'unresolved_conditions':unknown,
        'annual_MSE_decisions':annual,'strict_total_improvement':passed is True and all(d=='decreased' for d in annual.values()),
        'all_metric_signs_resolved':all(evaluation[g][mode]['paired']['macro'][m]['decision']!='unresolved' for g in evaluation for mode in evaluation[g] for m in METRICS)}
