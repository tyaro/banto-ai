"""Additional predeclared degeneracy cases; no real data or solver changes."""
import sys,unittest
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_constrained_qp as m

class ExactActiveSetEdges(unittest.TestCase):
    def test_negative_multiplier_removes_previously_blocking_normal(self):
        G=[[F(i==j) for j in range(3)] for i in range(3)]
        constraints=[{'a':list(map(F,[1,0,0])),'b':F(1,2)},
                     {'a':list(map(F,[2,1,0])),'b':F(3)}]
        trace=[];original=m.cycle_key
        def observe(beta,W,seen):trace.append(tuple(W));return original(beta,W,seen)
        with patch.object(m,'cycle_key',side_effect=observe):
            beta,dual,_=m.linear_qp(G,list(map(F,[1,3,0])),constraints,m.Budget())
        self.assertEqual(beta,[F(1,5),F(13,5),F(0)])
        self.assertIn((0,1),trace);self.assertIn((1,),trace)
        self.assertEqual(dual,[(1,F(2,5))])

    def test_zero_normal_and_simultaneous_blockers(self):
        G=[[F(i==j) for j in range(3)] for i in range(3)]
        constraints=[{'a':list(map(F,a)),'b':F(b)} for a,b in
                     (([0,0,0],0),([1,0,0],0),([0,1,0],0),([0,0,1],0))]
        beta,dual,_=m.linear_qp(G,[F(1)]*3,constraints,m.Budget())
        self.assertEqual(beta,[0,0,0]);self.assertEqual(len(dual),3)

if __name__=='__main__':unittest.main()
