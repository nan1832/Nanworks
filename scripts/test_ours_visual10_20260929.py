import math
import unittest
import numpy as np
from ours_visual10_20260929 import formula_values, rank, quantile


class TestVisual10(unittest.TestCase):
    def sample(self, a, b, dot):
        return dict(old_norm=a,new_norm=b,dot=dot,cos=dot/(a*b+1e-12))

    def test_exact_formulas(self):
        v=formula_values(self.sample(2,3,-3));c=-3/(6+1e-12)
        expected=[2,3,c,abs(c),c*2,abs(c)*2,c*3,abs(c)*3,c*3*2,abs(c)*3*2]
        self.assertEqual(list(v.values()),expected)

    def test_aggregation_order(self):
        pairs=[formula_values(self.sample(1,1,1)),formula_values(self.sample(1,1,-1))]
        mean=lambda k:sum(v[k] for v in pairs)/2
        self.assertEqual(mean('V03'),0)
        self.assertGreater(mean('V04'),.99)
        self.assertGreater(mean('V08'),.99)
        self.assertEqual(mean('V07'),0)
        self.assertNotEqual(mean('V08'),abs(mean('V03'))*mean('V02'))

    def test_quantiles(self):
        for n in [18,24,32,36]:
            a=[float(x*x-5*x) for x in range(n)]
            for q in [.25,.75]:self.assertAlmostEqual(quantile(a,q),np.quantile(a,q,method='linear'))

    def test_full_layer_filter(self):
        r=rank([0,1,2,3,100]);self.assertEqual(r['excluded'],[4]);self.assertEqual(r['top3'],[3,2,1])
        self.assertEqual(rank([-5,-3,0])['raw_top3'],[2,1,0])
        self.assertEqual(rank([0,0,0,0])['top3'],[0,1,2])
        self.assertEqual(rank([2,2])['top3'],[0,1])

    def test_nonfinite_rejected(self):
        with self.assertRaises(AssertionError):rank([math.nan,1])
        with self.assertRaises(AssertionError):formula_values(self.sample(-1,2,1))


if __name__=='__main__':unittest.main()
