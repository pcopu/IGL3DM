import unittest,json
from pathlib import Path
import numpy as np
from geometry import project,fit_point,analyze_tracks,gate
class GeometryTests(unittest.TestCase):
 def test_exact_triangulation(self):
  p=np.array([.3,-.8,.5]);obs=[(v,project(p,v*45)) for v in [0,1,2]]
  q,rank,cond=fit_point(obs)
  self.assertEqual(rank,3);np.testing.assert_allclose(q,p,atol=1e-12)
 def test_opposite_cameras_degenerate(self):
  p=np.array([.3,-.8,.5]);q,rank,cond=fit_point([(v,project(p,v*45)) for v in [0,4]])
  self.assertEqual(rank,2)
 def test_heldout_not_used_to_fit(self):
  p=np.array([.3,-.8,.5]);tracks={'p':{v:project(p,v*45) for v in [0,1,2]}}
  tracks['p'][1]=tracks['p'][1]+[80,0]
  r=analyze_tracks(tracks,heldout=(1,5))
  self.assertLess(r['training_reprojection_px']['max'],1e-10)
  self.assertAlmostEqual(r['heldout_reprojection_px']['mean'],80.)
  self.assertEqual(r['known_camera_epipolar_px']['max'],0.)
 def test_identity_failure_overrides_exact_geometry(self):
  p=np.array([.3,-.8,.5]);r=analyze_tracks({'p':{v:project(p,v*45) for v in [0,1,2]}},heldout=(1,5))
  self.assertFalse(gate(r,False,True,True)['pass'])
 def test_missing_metrics_cannot_pass(self):
  r=analyze_tracks({});self.assertFalse(gate(r,True,True,True)['pass'])
 def test_controls(self):
  r=json.loads((Path(__file__).resolve().parents[1]/'controls/summary.json').read_text())
  for name in ['exact','noise_0p4px']:self.assertTrue(r[name]['gate']['pass'])
  for name in ['swapped_heldout','warped_heldout','horizontal_swap_heldout','wrong_requested_camera','consistent_wrong_identity']:
   self.assertFalse(r[name]['gate']['pass'])
  self.assertLess(r['horizontal_swap_heldout']['known_camera_epipolar_px']['p95'],2)
  self.assertLess(r['consistent_wrong_identity']['heldout_reprojection_px']['p95'],2)
  self.assertGreater(r['consistent_wrong_identity']['ground_truth_3d_error']['p95'],.4)
if __name__=='__main__':unittest.main()
