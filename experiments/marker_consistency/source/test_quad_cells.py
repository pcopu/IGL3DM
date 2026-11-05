import unittest
import cv2,numpy as np
from quad_cells import detect_cells
class QuadCellTests(unittest.TestCase):
 def test_closed_grid_cells_found(self):
  a=np.full((100,100),255,np.uint8)
  for x in [20,40,60]:cv2.line(a,(x,20),(x,60),0,1)
  for y in [20,40,60]:cv2.line(a,(20,y),(60,y),0,1)
  g=detect_cells(a);self.assertEqual(len(g['cells']),4)
  self.assertTrue(all(len(set(c['node_ids']))==4 for c in g['cells']))
 def test_cell_corners_cannot_weld_to_themselves(self):
  a=np.full((100,100),255,np.uint8)
  for x in [20,25,30,35]:cv2.line(a,(x,20),(x,35),0,1)
  for y in [20,25,30,35]:cv2.line(a,(20,y),(35,y),0,1)
  g=detect_cells(a);self.assertTrue(all(len(set(c['node_ids']))==4 for c in g['cells']))
 def test_no_ink_has_no_cells(self):
  self.assertEqual(detect_cells(np.full((100,100),255,np.uint8))['cells'],[])
if __name__=='__main__':unittest.main()
