import unittest
from dimple_control import generate,validate,radial

class DimpleControlTests(unittest.TestCase):
 def test_shared_all_quad_topology(self):
  r=validate(24)
  self.assertEqual((r['vertices'],r['quads'],r['euler']),(3458,3456,2))
  for key in ['boundary_edges','nonmanifold_edges','inconsistent_edge_winding']:self.assertEqual(r[key],0)
 def test_recess_and_matched_topology(self):
  self.assertGreater(validate(24)['center_recession_below_chord'],.03)
  self.assertLess(validate(24,False)['center_recession_below_chord'],0)
  self.assertAlmostEqual(radial([1,0,0],False)-radial([1,0,0]),.19)
  v,f,u=generate(24);v2,f2,u2=generate(24,False)
  self.assertEqual(f,f2);self.assertEqual(u,u2);self.assertNotEqual(v,v2)
 def test_invalid_resolution(self):
  for n in [0,3,5]:
   with self.assertRaises(ValueError):generate(n)

if __name__=='__main__':unittest.main()
