import unittest
import numpy as np
from complete import directions,fit,mesh,topology

class CompletionTests(unittest.TestCase):
 def test_constant_radius_and_translation(self):
  u=directions(200);center=np.array([2.,-3.,4.]);m=fit(2*u+center,center)
  self.assertLess(np.max(abs(m(directions(351))-2)),1e-8)
 def test_closed_oriented_connected(self):
  u=directions(500);v,f=mesh(u,np.exp(.3*u[:,2]),np.zeros(3));t=topology(v,f)
  for key in ['boundary_edges','nonmanifold_edges','degenerate_triangles','inconsistent_edge_winding']:self.assertEqual(t[key],0)
  self.assertEqual(t['connected_components'],1);self.assertEqual(t['euler'],2);self.assertGreater(t['signed_volume'],0)
 def test_invalid_data(self):
  for pts in [np.zeros((5,3)),np.ones((3,3)),np.full((10,3),np.nan)]:
   with self.assertRaises(ValueError):fit(pts,np.zeros(3))
 def test_missing_cap_not_ground_truth(self):
  u=directions(600);keep=u[:,0]<.8;m=fit(u[keep],np.zeros(3));q=np.array([[1.,0.,0.]])
  # Both an unseen dent and an unseen smooth patch fit the same observations.
  self.assertAlmostEqual(float(m(q)[0]),1,places=8)
  self.assertGreater(abs(float(m(q)[0])-.8),.19)

if __name__=='__main__': unittest.main()
