import unittest
import numpy as np
from score_patch_ambiguity import direction
class TestPatchAmbiguity(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(48)
        self.a=rng.integers(0,256,(160,160),dtype=np.uint8)
        self.b=rng.integers(0,256,(160,160),dtype=np.uint8)
        self.b[45:76,45:76]=self.a[45:76,45:76]
    def test_unique_patch(self):
        margin,accepted,alternative=direction(self.a,self.b,[60,60],[60,60])
        self.assertGreater(margin,.5);self.assertGreater(accepted,.99)
    def test_duplicate_alternative(self):
        self.b[45:76,77:108]=self.a[45:76,45:76]
        margin,accepted,alternative=direction(self.a,self.b,[60,60],[60,60])
        self.assertAlmostEqual(margin,0,places=5);self.assertGreater(alternative,.99)
    def test_better_alternative_than_accepted(self):
        margin,accepted,alternative=direction(self.a,self.b,[60,60],[70,60])
        self.assertLess(margin,-.5);self.assertGreater(alternative,.99)
    def test_boundary_unscorable(self):
        self.assertIsNone(direction(self.a,self.b,[5,5],[60,60]))
if __name__=='__main__':unittest.main()
