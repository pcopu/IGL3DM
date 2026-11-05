import json
from pathlib import Path
import tempfile
import unittest
from prepare_quad_render import prepare

PLY='''ply
format ascii 1.0
element vertex 4
property float x
property float y
property float z
element face 1
property list uchar int vertex_indices
end_header
0 0 0
1 0 0
1 1 0
0 1 0
4 0 1 2 3
'''

class QuadRenderTests(unittest.TestCase):
    def test_exact_coordinates_and_only_display_diagonal(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'test.ply';src.write_text(PLY)
            report=prepare(src,root/'out');data=json.loads((root/'out/mesh.json').read_text())
            self.assertEqual(data['vertices'],[[0,0,0],[1,0,0],[1,1,0],[0,1,0]])
            self.assertEqual(data['faces'],[[0,1,2],[0,2,3]])
            self.assertEqual(report['parent_quad_for_each_triangle'],[0,0])
            self.assertFalse(report['vertex_coordinates_changed'])
            with self.assertRaises(ValueError):prepare(src,root/'out')
    def test_rejects_non_quad_input(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'bad.ply';src.write_text(PLY.replace('4 0 1 2 3','3 0 1 2'))
            with self.assertRaises(ValueError):prepare(src,root/'out')
            self.assertFalse((root/'out').exists())

if __name__=='__main__':unittest.main()
