import unittest,tempfile,json
from pathlib import Path
import numpy as np
from prepare_graph_input import prepare
from build_graph_geometry import build
class CombinedTests(unittest.TestCase):
 def test_one_uniform_affine_is_recorded(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'src';src.mkdir();(src/'video_manifest.json').write_text(json.dumps({'working_size':[575,768],'frames':[]}));r=prepare(src,root/'out');np.testing.assert_allclose(r['uniform_affine'],[[2/3,0,64+1/3],[0,2/3,0]])
 def test_nonempty_destination_preserved(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'keep').write_text('keep')
   with self.assertRaisesRegex(ValueError,'nonempty'):prepare(root/'missing',root)
   self.assertEqual((root/'keep').read_text(),'keep')
 def test_empty_geometry_is_valid_negative_output(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for name,data in [('tracks',{}),('graphs',[]),('cameras',{'views':[],'coordinates':'relative test'})]:(root/(name+'.json')).write_text(json.dumps(data))
   r=build(root/'tracks.json',root/'graphs.json',root/'cameras.json',root/'out');self.assertEqual(r['candidate_points'],0);self.assertEqual(r['observed_quad_faces_at_least_three_frames'],0);self.assertTrue((root/'out/conditional_graph_geometry_preview.png').exists())
if __name__=='__main__':unittest.main()
