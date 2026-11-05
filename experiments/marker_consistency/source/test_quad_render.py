import json
from pathlib import Path
import tempfile
import unittest
from prepare_quad_render import prepare, triangle_topology

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
            self.assertEqual(report['display_topology']['boundary_edges'],4)
            self.assertEqual(report['display_topology']['nonmanifold_edges'],0)
            with self.assertRaises(ValueError):prepare(src,root/'out')
    def test_rejects_non_quad_input(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'bad.ply';src.write_text(PLY.replace('4 0 1 2 3','3 0 1 2'))
            with self.assertRaises(ValueError):prepare(src,root/'out')
            self.assertFalse((root/'out').exists())

    def test_topology_separates_unused_points_and_components(self):
        vertices=[[0,0,0],[1,0,0],[0,1,0],[3,0,0],[4,0,0],[3,1,0],[9,9,9]]
        report=triangle_topology(vertices,[[0,1,2],[3,4,5]])
        self.assertEqual(report['unused_candidate_points'],1)
        self.assertEqual(report['component_used_vertex_counts_descending'],[3,3])
        self.assertEqual(report['boundary_edges'],6)
        self.assertFalse(report['watertight_edge_incidence'])

    def test_nonmanifold_edge_and_degenerate_triangle_are_not_repaired(self):
        vertices=[[0,0,0],[1,0,0],[0,1,0],[0,-1,0],[2,0,0]]
        faces=[[0,1,2],[1,0,3],[0,1,4]]
        report=triangle_topology(vertices,faces)
        self.assertEqual(report['nonmanifold_edges'],1)
        self.assertEqual(report['zero_area_display_triangles'],1)
        self.assertEqual(faces,[[0,1,2],[1,0,3],[0,1,4]])

if __name__=='__main__':unittest.main()
