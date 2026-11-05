import unittest,tempfile,json
from pathlib import Path
import numpy as np
import cv2
from video_tracks import dlt,ingest
class VideoTests(unittest.TestCase):
 def test_projection_triangulation(self):
  P0=np.array([[200,0,0,160],[0,200,0,160],[0,0,0,1.]])
  P1=np.array([[0,0,200,160],[0,200,0,160],[0,0,0,1.]])
  X=np.array([.2,-.3,.7]);p0=P0@np.r_[X,1];p1=P1@np.r_[X,1]
  result=dlt([(0,p0[:2]),(1,p1[:2])],{0:P0,1:P1})
  np.testing.assert_allclose(result,X,atol=1e-10)
 def test_degenerate_camera_rejected(self):
  P=np.array([[200,0,0,160],[0,200,0,160],[0,0,0,1.]])
  self.assertIsNone(dlt([(0,[200,100]),(1,[200,100])],{0:P,1:P}))
 def test_decode_track_and_stop_at_occlusion(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);video=td/'fixture.avi';writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),12.,(256,256))
   self.assertTrue(writer.isOpened())
   base=np.full((256,256,3),255,np.uint8)
   for x in range(35,225,20):cv2.line(base,(x,25),(x+6,225),(0,0,0),2)
   for y in range(35,225,20):cv2.line(base,(25,y),(225,y+4),(0,0,0),2)
   for i in range(32):
    if i==16:frame=np.full_like(base,255)
    else:frame=cv2.warpAffine(base,np.float32([[1,0,i*.5],[0,1,i*.25]]),(256,256),borderValue=(255,255,255))
    writer.write(frame)
   writer.release();r=ingest(video,td/'out',12,100,256)
   self.assertEqual(r['sample_count'],32);self.assertFalse(r['truncated']);self.assertGreater(r['track_count_at_least_3_samples'],10)
   self.assertEqual(r['geometry']['status'],'not_attempted')
   tracks=json.loads((td/'out/tracks.json').read_text())
   initial=[t for t in tracks.values() if t['observations'][0]['sample_index']==0]
   self.assertGreater(len(initial),10)
   self.assertTrue(all(max(o['sample_index'] for o in t['observations'])<16 for t in initial))
   # No old ID is reattached after total disappearance.
   self.assertTrue(all(not(any(o['sample_index']<16 for o in t['observations']) and any(o['sample_index']>16 for o in t['observations'])) for t in tracks.values()))
if __name__=='__main__':unittest.main()
