import copy
import itertools
import json
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_constrained_qp as m
from demand_constrained_qp_verify import verify
from tests.test_demand_common_residual import full_batch
from tests.test_demand_prefix_adapter import sample_batch
from demand_prefix_adapter import fixed_features


def problem(specs):
    # Specs are (B,Y,x,quarter,unit), with exact equal per-Q risk weights.
    counts={q:sum(s[3]==q for s in specs) for q in {s[3] for s in specs}}
    return {'rows':[{'key':str(i),'quarter':q,'B':str(B),'Y':str(Y),'unit':str(u),
                    'x':list(map(str,x)) if x is not None else None,
                    'fit_weight':str(F(1,len(specs))) if x is not None and B>0 else '0',
                    'risk_weight':str(F(1,counts[q]))} for i,(B,Y,x,q,u) in enumerate(specs)]}


def examples():
    return {
      'intercept':problem([(10,12,[1,0,0],1,1)]),
      'changes_aggregate_total':problem([(10,14,[1,-1,0],1,1),(10,8,[1,1,0],1,1)]),
      'quarter_conflict':problem([(10,12,[1,0,0],1,1),(10,9,[1,0,0],2,1)]),
      'zero_optimum_nonzero_feasible':problem([(10,12,[0,1,0],1,1),(10,11,[0,-2,0],1,1)]),
      'exact_hinge':problem([(10,10,[1,0,0],1,1),(10,12,[1,0,0],1,1)]),
      'two_cuts':problem([(10,30,[1,0,0],1,1),(10,11,[1,0,0],2,1),(10,12,[1,0,0],3,1)]),
      'three_dimensional':problem([(10,13,[1,1,0],1,1),(10,8,[1,-1,0],1,1),(10,12,[1,0,1],2,1),(10,9,[1,0,-1],2,1)])}


def exhaustive(problem_):
    """Tiny-fixture independent all-facet/all-active-subset enumeration.

    It does not call solver helpers or its Gaussian eliminator.
    """
    rr=problem_['rows'];dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    G=[[F(i==j) for j in range(3)] for i in range(3)];c=[F(0)]*3;constraints=[]
    for r in rr:
        if r['x'] is None:continue
        B,Y,u,w=map(F,(r['B'],r['Y'],r['unit'],r['fit_weight']));x=list(map(F,r['x']))
        h=[u*v for v in x];constraints.append((tuple(-v for v in h),B))
        for i in range(3):
            c[i]+=w*x[i]*(Y-B)/u
            for j in range(3):G[i][j]+=w*x[i]*x[j]
    for q in sorted({r['quarter'] for r in rr}):
        rows=[r for r in rr if r['quarter']==q]
        for s in (-1,1):
            bound=sum(F(r['risk_weight'])*max(s*(F(r['B'])-F(r['Y'])),0) for r in rows)
            for mask in itertools.product((False,True),repeat=len(rows)):
                chosen=[r for r,keep in zip(rows,mask) if keep]
                a=tuple(sum(F(r['risk_weight'])*s*F(r['unit'])*F(r['x'][j]) for r in chosen if r['x'] is not None and F(r['B'])>0) for j in range(3))
                b=bound-sum(F(r['risk_weight'])*s*(F(r['B'])-F(r['Y'])) for r in chosen)
                if any(a):constraints.append((a,b))
    constraints=sorted(set(constraints));best=None
    def inverse_solve(A,b):
        # Fraction-free recursive determinant / Cramer's rule, unlike production.
        def det(M):
            if not M:return F(1)
            return sum((-1)**j*M[0][j]*det([row[:j]+row[j+1:] for row in M[1:]]) for j in range(len(M)))
        den=det(A)
        if not den:return None
        return [det([row[:j]+[b[i]]+row[j+1:] for i,row in enumerate(A)])/den for j in range(len(A))]
    for n in range(4):
        for active in itertools.combinations(constraints,n):
            normals=[list(a) for a,b in active]
            K=[G[i]+[a[i] for a in normals] for i in range(3)]+[a+[F(0)]*n for a in normals]
            sol=inverse_solve(K,c+[b for a,b in active])
            if sol is None or any(v<0 for v in sol[3:]):continue
            beta=sol[:3]
            if any(dot(a,beta)>b for a,b in constraints):continue
            value=dot(beta,[dot(row,beta) for row in G])/2-dot(c,beta)
            if best is None or value<best[0]:best=(value,beta)
    if best is None:raise AssertionError('enumeration found no KKT point')
    return best[1]


class ConstrainedQPTests(unittest.TestCase):
    def test_known_nonzero_ridge_intercept_penalty(self):
        p=examples()['intercept'];cert=m.solve(p)
        self.assertEqual(cert['beta'],['1','0','0']);self.assertEqual(verify(p,cert)['gap'],'0')

    def test_total_is_not_fixed(self):
        p=examples()['changes_aggregate_total'];cert=m.solve(p);verify(p,cert)
        self.assertEqual(cert['beta'],['1/2','-3/2','0'])
        self.assertEqual(sum(F(r['B'])+F(r['unit'])*sum(F(x)*F(b) for x,b in zip(r['x'],cert['beta'])) for r in p['rows']),21)

    def test_quarter_conflict_zero_has_certificate(self):
        p=examples()['quarter_conflict'];cert=m.solve(p);checked=verify(p,cert)
        self.assertTrue(checked['zero_beta']);self.assertTrue(cert['active']);self.assertGreater(len(cert['rounds']),1)

    def test_zero_optimal_does_not_mean_nonzero_infeasible(self):
        p=examples()['zero_optimum_nonzero_feasible'];cert=m.solve(p);self.assertTrue(verify(p,cert)['zero_beta'])
        # beta=(0,-1/4,0) is feasible but has strictly larger ridge objective.
        values=[F(r['B'])+F(r['unit'])*F(r['x'][1])*F(-1,4) for r in p['rows']]
        self.assertEqual(values,[F(39,4),F(21,2)])
        self.assertLess(sum(max(F(r['Y'])-v,0) for r,v in zip(p['rows'],values)),3)

    def test_hinge_zero_and_multiple_cut_rounds(self):
        for name in ('exact_hinge','two_cuts','three_dimensional'):
            with self.subTest(name=name):
                p=examples()[name];cert=m.solve(p);self.assertEqual(verify(p,cert)['gap'],'0')
        cert=m.solve(examples()['two_cuts']);self.assertEqual(cert['beta'],['1','0','0']);self.assertGreaterEqual(len(cert['cuts']),2)

    def test_independent_all_facet_active_subset_enumeration(self):
        for name in ('intercept','changes_aggregate_total','quarter_conflict','exact_hinge','two_cuts'):
            with self.subTest(name=name):
                p=examples()[name];self.assertEqual(list(map(F,m.solve(p)['beta'])),exhaustive(p))

    def test_duplicate_dependent_and_opposite_normals(self):
        B=m.Budget();G=[[F(i==j) for j in range(3)] for i in range(3)]
        cs=[{'a':list(map(F,a)),'b':F(b)} for a,b in (([1,0,0],0),([2,0,0],0),([-1,0,0],0),([0,1,0],0))]
        beta,dual,_=m.linear_qp(G,list(map(F,[1,1,0])),cs,B)
        self.assertEqual(beta,[0,0,0]);self.assertTrue(dual)

    def test_nonnegative_training_boundary(self):
        # One row with large positive feature is given zero fit weight. It still
        # constrains nonnegativity and enters risk. No fabricated missing target.
        p=problem([(10,8,[1,0,0],1,1),(1,0,[100,0,0],1,1)])
        p['rows'][0]['fit_weight']='1';p['rows'][1]['fit_weight']='0'
        checked=verify(p,m.solve(p));self.assertEqual(checked['beta'],['-1/100','0','0'])

    def test_prefix_exact_weights_and_fallback_denominators(self):
        batch=full_batch();extra=sample_batch('2013-03-12',6)['rows'][0]
        extra['past14_values'][0]=None
        extra['features'],extra['reasons']=fixed_features(extra['past14_values'],extra['past14_dates'],extra['baseline'],extra['assumed_open_mask'],extra['scale'])
        batch['rows'].append(extra);before=copy.deepcopy(batch)
        with patch.object(Path,'open',side_effect=AssertionError('no files')):built=m.from_prefix(batch)
        self.assertEqual(batch,before);self.assertTrue(built['supported'])
        rows=built['problem']['rows'];self.assertEqual(sum(F(r['fit_weight']) for r in rows),1)
        fallback=next(r for r in rows if r['key']==extra['key']);self.assertIsNone(fallback['x']);self.assertEqual(fallback['fit_weight'],'0');self.assertEqual(fallback['risk_weight'],'1/20')
        verify(built['problem'],m.solve(built['problem']))

    def test_unsupported_prefix_and_future_or_partial_rejected(self):
        batch=full_batch();batch['rows'].pop();self.assertFalse(m.from_prefix(batch)['supported'])
        for field,value in (('label_available_at','2014-01-02'),('raw_actual',[None]*14),('features',[1.,999.,0.])):
            bad=full_batch();bad['rows'][0][field]=value
            with self.assertRaises(ValueError):m.from_prefix(bad)

    def test_unknown_floor_unsupported_and_B_zero(self):
        self.assertEqual(m.predict_total([10]*14,140,[1,0,0],[-2,0,0]),0)
        self.assertEqual(m.predict_total([10]*14,140,None,[-2,0,0]),140)
        self.assertEqual(m.predict_total([0]*14,140,[1,0,0],[2,0,0]),0)

    def test_binary64_exact_and_invalid_numeric_inputs(self):
        self.assertEqual(m.number(.1),F.from_float(.1));self.assertNotEqual(m.number(.1),F(1,10))
        for value in (True,float('nan'),float('inf'),'1e9999999','1/0'):
            with self.assertRaises(ValueError):m.number(value)
        for change in ({'fit_weight':'-1'},{'risk_weight':'0'},{'x':[1,2]},{'Y':None}):
            p=examples()['intercept'];p['rows'][0].update(change)
            with self.assertRaises(ValueError):m.solve(p)

    def test_tampered_certificates_and_original_problem_rejected(self):
        p=examples()['two_cuts'];cert=m.solve(p)
        variants=[]
        z=copy.deepcopy(cert);z['beta'][0]='2';variants.append(z)
        z=copy.deepcopy(cert);z['active'][0]['dual']='-1';variants.append(z)
        z=copy.deepcopy(cert);z['active'][0]['selected']=['not-a-row'];variants.append(z)
        z=copy.deepcopy(cert);z['objective_J']='0';variants.append(z)
        z=copy.deepcopy(cert);z['cuts'][0]['side']=0;variants.append(z)
        for z in variants:
            with self.assertRaises(ValueError):verify(p,z)
        altered=copy.deepcopy(p);altered['rows'][0]['Y']='100'
        with self.assertRaises(ValueError):verify(altered,cert)

    def test_limits_cycles_and_certificate_size_are_failure(self):
        p=examples()['quarter_conflict']
        for limits in ({'rounds':1},{'pivots':1},{'total_pivots':1},{'bits':1},{'certificate_bytes':1},{'cuts':1},{'rows':1}):
            with self.subTest(limits=limits):
                with self.assertRaises(m.NumericFailure):m.solve(examples()['two_cuts'] if 'cuts' in limits else p,limits=limits)
        seen=set();m.cycle_key([F(0)]*3,[],seen)
        with self.assertRaisesRegex(m.NumericFailure,'cycle'):m.cycle_key([F(0)]*3,[],seen)
        with self.assertRaises(m.NumericFailure):m.linear_solve([[F(0)]],[F(1)],m.Budget())
        with self.assertRaises(ValueError):m.solve(p,limits={'rounds':65})


if __name__=='__main__':unittest.main()
