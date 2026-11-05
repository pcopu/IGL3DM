import unittest
import numpy as np
from estimate_cameras import matrix,predict,triangulate,fit
class CameraTests(unittest.TestCase):
 def test_projection_and_triangulation(self):
  cams=np.array([[0,0,0,np.log(256),256,256],[np.pi/3,.1,.02,np.log(260),255,257],[np.pi/2,0,0,np.log(256),256,256]])
  point=np.array([.2,.3,-.4]);obs=[(v,predict(point,c)) for v,c in enumerate(cams)]
  q,condition=triangulate(obs,cams);np.testing.assert_allclose(q,point,atol=1e-10)
 def test_too_few_multiview_tracks_reported(self):
  r,cams=fit({'x':{0:[256,256],1:[260,260]}});self.assertEqual(r['status'],'insufficient_tracks')
if __name__=='__main__':unittest.main()
