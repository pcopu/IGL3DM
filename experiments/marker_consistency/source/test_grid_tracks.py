import unittest
import numpy as np
import cv2
from grid_tracks import thin,junctions,neighborhood_support
class GridTrackTests(unittest.TestCase):
 def test_crossing_detected(self):
  image=np.full((100,100),255,np.uint8)
  cv2.line(image,(20,50),(80,50),0,3);cv2.line(image,(50,20),(50,80),0,3)
  pts,skel,branches=junctions(image)
  self.assertTrue(any(np.linalg.norm(p-[50,50])<4 for p in pts))
 def test_thinning_preserves_intersection(self):
  a=np.zeros((30,30),np.uint8);a[12:17,3:27]=1;a[3:27,12:17]=1
  out=thin(a);self.assertLess(out.sum(),a.sum());self.assertEqual(out[14,14],1)
 def test_translated_neighborhood_kept(self):
  p=np.array([[0,0],[10,0],[0,10],[10,10]],float);q=p+[3,2]
  m=[(i,i,0) for i in range(4)]
  self.assertEqual(len(neighborhood_support(m,p,q)),4)
 def test_isolated_match_not_propagated(self):
  p=np.array([[0,0],[100,100]],float);q=p+[3,2]
  self.assertEqual(neighborhood_support([(0,0,0),(1,1,0)],p,q),[])
if __name__=='__main__':unittest.main()
