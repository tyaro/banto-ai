"""One fixed common signed residual ridge; training consumes only permitted batches."""
import math
from collections import Counter
from demand_prefix_adapter import validate_batch,input_features
from demand_input_boundary_v2 import FIT,CUTS,day
from demand_annual_reliability_v2 import side_bound
LAMBDA=1.


def solve_spd(gram,rhs):
    lower=[[0.]*3 for _ in range(3)]
    for i in range(3):
        for j in range(i+1):
            v=gram[i][j]-math.fsum(lower[i][k]*lower[j][k] for k in range(j))
            if i==j:
                if not math.isfinite(v) or v<=0:raise ValueError('nonpositive regression system')
                lower[i][j]=math.sqrt(v)
            else:lower[i][j]=v/lower[j][j]
    z=[]
    for i in range(3):z.append((rhs[i]-math.fsum(lower[i][k]*z[k] for k in range(i)))/lower[i][i])
    beta=[0.]*3
    for i in range(2,-1,-1):beta[i]=(z[i]-math.fsum(lower[k][i]*beta[k] for k in range(i+1,3)))/lower[i][i]
    if not all(math.isfinite(v) for v in beta):raise ValueError('nonfinite regression solution')
    return beta


def endpoint(baseline,scale,x,beta):
    B=math.fsum(baseline)
    if x is None or B<=0:return B
    raw=B+14*scale*math.fsum(a*b for a,b in zip(x,beta))
    if not math.isfinite(raw):raise ValueError('nonfinite endpoint')
    return max(raw,0.)


def quarter(origin):return str((day(origin).month-1)//3+1)


def train(batch):
    validate_batch(batch);rows=batch['rows'];eligible=[r for r in rows if r['features'] is not None]
    counts=Counter((quarter(r['origin']),r['store']) for r in eligible)
    supported=all(counts[q,s]>0 for q in ('1','2','3','4') for s in FIT)
    weighted=[]
    if supported:
        for r in eligible:
            w=1/(4*10*counts[quarter(r['origin']),r['store']]);y=(math.fsum(r['raw_actual'])-math.fsum(r['baseline']))/(14*r['scale'])
            weighted.append({'key':r['key'],'weight':w,'x':r['features'],'residual_target':y})
    gram=[[math.fsum(r['weight']*r['x'][i]*r['x'][j] for r in weighted)+(LAMBDA if i==j else 0.) for j in range(3)] for i in range(3)]
    rhs=[math.fsum(r['weight']*r['x'][j]*r['residual_target'] for r in weighted) for j in range(3)]
    beta=solve_spd(gram,rhs) if supported else [0.,0.,0.]
    if weighted and abs(math.fsum(r['weight'] for r in weighted)-1)>1e-12:raise ValueError('sum-one regression weights required')
    cal={};journals={}
    for q in ('1','2','3','4'):
        rr=[r for r in rows if quarter(r['origin'])==q];n=Counter(r['store'] for r in rr);samples=[]
        if not all(n[s]>0 for s in FIT):
            cal[q]={'alpha':0.,'reason':'missing_complete_store_support','complete_windows':len(rr)};journals[q]=[];continue
        for r in rr:
            B=math.fsum(r['baseline']);Y=math.fsum(r['raw_actual']);R=endpoint(r['baseline'],r['scale'],r['features'],beta)
            samples.append({'key':r['key'],'store':r['store'],'origin':r['origin'],'e':B-Y,'D':R-B,'scale':r['scale'],'weight':1/(10*n[r['store']]),'feature_eligible':r['features'] is not None})
        A=math.fsum(r['weight']*(r['D']/(14*r['scale']))**2 for r in samples);C=math.fsum(-r['weight']*r['e']*r['D']/(14*r['scale'])**2 for r in samples)
        under=side_bound(samples,-1);over=side_bound(samples,1);mse=max(0.,2*C/A) if A>1e-24 else 1.;U=min(1.,under,over,mse)
        alpha=max(0.,min(U,C/A)) if A>1e-24 else 0.
        changes={name:math.fsum(r['weight']*(max(sg*(r['e']+alpha*r['D']),0.)-max(sg*r['e'],0.)) for r in samples) for name,sg in (('under',-1),('over',1))};changes['MSE']=A*alpha**2-2*C*alpha
        if changes['under']>1e-8 or changes['over']>1e-8 or changes['MSE']>1e-12:raise ValueError('past internal risk constraint failed')
        cal[q]={'alpha':alpha,'energy':A,'covariance':C,'under_upper':under,'over_upper':over,'MSE_upper':mse,'upper':U,'changes':changes,'complete_windows':len(rr),'nonzero_D':sum(abs(r['D'])>1e-8 for r in samples)};journals[q]=samples
    return {'cutoff':batch['cutoff'],'beta':beta,'lambda':LAMBDA,'gram':gram,'rhs':rhs,'weighted_rows':weighted,'supported':supported,
        'unsupported_reason':None if supported else 'missing_feature_store_quarter_cell','calibration':cal,'calibration_journal':journals,
        'same_fit_labels_internal_optimization':True,'new_2015_fit':False}


def forecast(row,transforms,state):
    q=quarter(row['origin'])
    if state['cutoff']!=CUTS[int(q)-1] or day(row['origin'])<day(state['cutoff']) or not row['origin'].startswith('2014-'):raise ValueError('matching 2014 quarter-frozen model required')
    x,reasons=input_features(row,transforms);b=list(row['matched_mean28']);B=math.fsum(b);u=transforms['scales'][str(row['store'])]
    R=endpoint(b,u,x,state['beta']);alpha=state['calibration'][q]['alpha'];P=B+alpha*(R-B)
    pred=[v*(P/B) for v in b] if B>0 and x is not None else list(b)
    if any(not math.isfinite(p) or p<0 or (not good and p!=0.) for p,good in zip(pred,row['assumed_open_mask'])):raise ValueError('nonnegative masked prediction required')
    return {'key':row['key'],'store':row['store'],'origin':row['origin'],'scale':u,'baseline_proxy':b,'candidate':pred,'baseline':b,'prior':b,
        'assumed_closure':[not v for v in row['assumed_open_mask']],'operating_status':['unknown']*14,'features':x,'feature_reasons':reasons,
        'raw_endpoint_total':R,'alpha':alpha,'correction_total':P-B,'cutoff':state['cutoff']}
