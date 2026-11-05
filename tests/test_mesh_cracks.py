"""Analytic numerical fixtures: no generated meshes or manual geometry repair."""
import unittest

import numpy as np

from igl3dm.core import (_collinear_candidates, _collinear_segment,
                        _remove_collinear_faces, extract_mesh, mesh_integrity)


class MeshCrackTests(unittest.TestCase):
    def assert_nondegenerate(self, vertices, faces):
        # Independently inspect every face so a candidate-filter regression
        # cannot silently bypass the output invariant as well.
        for face in faces:
            self.assertIsNone(_collinear_segment(vertices, face))
        self.assertTrue(np.all(faces[:,0] != faces[:,1]))
        self.assertTrue(np.all(faces[:,1] != faces[:,2]))
        self.assertTrue(np.all(faces[:,2] != faces[:,0]))

    @staticmethod
    def area_vectors(vertices, faces):
        v = vertices.astype(np.float64)
        return np.cross(v[faces[:,1]]-v[faces[:,0]], v[faces[:,2]]-v[faces[:,0]])

    def test_float32_slanted_plane_stays_closed(self):
        # A plane nearly crosses grid samples. Rounding can flatten triangles
        # to three distinct collinear vertices. Deleting them used to leave
        # 6 or 14 boundary edges, despite this being a closed convex shape.
        n = 16
        x, y, z = np.mgrid[:n,:n,:n]
        for slope, offset in ((.7,5e-8), (1.3,1e-7), (1.3,1.5e-7)):
            with self.subTest(slope=slope, offset=offset):
                field = np.minimum.reduce([
                    3*(x-3)-slope*(z-5)-offset,
                    x-1.5, n-2.5-x, y-1.5, n-2.5-y, z-1.5, n-2.5-z,
                ]).astype(np.float32)
                original = field.copy()
                vertices, faces = extract_mesh(field)
                np.testing.assert_array_equal(field, original)
                self.assertEqual(vertices.dtype, np.float32)
                self.assertEqual(len(vertices), len(np.unique(vertices, axis=0)))
                self.assert_nondegenerate(vertices, faces)
                integrity = mesh_integrity(vertices, faces)
                self.assertEqual(integrity['boundary_edges'], 0)
                self.assertEqual(integrity['nonmanifold_edges'], 0)
                self.assertEqual(integrity['euler_characteristic'], 2)
                self.assertGreater(integrity['signed_volume'], 0)
                # All the geometry is bounded by the analytic box.
                self.assertTrue(np.all(np.abs(vertices) <= .75))

    def test_subdivision_preserves_positions_area_and_winding(self):
        vertices = np.array([[0,0,0], [2,0,0], [1,0,0], [0,1,0]], np.float32)
        original = vertices.copy()
        for reverse in (False, True):
            for rotate in range(3):
                faces = np.array([[0,1,2], [1,0,3]], np.int32)
                faces = np.roll(faces, rotate, axis=1)
                if reverse:
                    faces = faces[:,::-1]
                repaired = _remove_collinear_faces(vertices, faces)
                np.testing.assert_array_equal(vertices, original)
                self.assertEqual(len(repaired), 2)
                self.assert_nondegenerate(vertices, repaired)
                old_area = self.area_vectors(vertices, faces).sum(axis=0)
                new_areas = self.area_vectors(vertices, repaired)
                np.testing.assert_array_equal(new_areas.sum(axis=0), old_area)
                self.assertTrue(np.all(new_areas @ old_area > 0))
                # The two subtriangles partition the original face, using
                # only its boundary's existing middle point.
                self.assertEqual({tuple(sorted(f)) for f in repaired},
                                 {(0,2,3), (1,2,3)})

    def test_nested_subdivision_and_all_incident_faces(self):
        vertices = np.array([[0,0,0], [4,0,0], [2,0,0], [1,0,0],
                             [0,1,0], [0,-1,0]], np.float32)
        faces = np.array([[0,1,2], [0,2,3], [1,0,4], [0,1,5]], np.int32)
        expected = {(0,3,4), (2,3,4), (1,2,4), (0,3,5), (2,3,5), (1,2,5)}
        for ordered in (faces, faces[::-1]):
            repaired = _remove_collinear_faces(vertices, ordered)
            self.assertEqual({tuple(sorted(f)) for f in repaired}, expected)
            self.assert_nondegenerate(vertices, repaired)
            np.testing.assert_array_equal(self.area_vectors(vertices, repaired).sum(axis=0),
                                          self.area_vectors(vertices, faces).sum(axis=0))
            np.testing.assert_array_equal(repaired, _remove_collinear_faces(vertices, ordered))

    def test_float64_cancellation_does_not_remove_nonzero_triangle(self):
        vertices = np.array([[1,1,0], [0,0,0], [2.0**-60,2.0**-59,0]], np.float32)
        faces = np.array([[0,1,2]], np.int32)
        self.assertTrue(np.all(self.area_vectors(vertices, faces) == 0))
        self.assertTrue(_collinear_candidates(vertices[faces].astype(np.float64))[0])
        self.assertIsNone(_collinear_segment(vertices, faces[0]))
        np.testing.assert_array_equal(_remove_collinear_faces(vertices, faces), faces)

    def test_roundoff_does_not_hide_exact_collinearity(self):
        # Exact float32 dyadics on y=3*x. Their double-precision cross product
        # is nonzero because intermediate subtraction/products round.
        vertices = np.array([
            [1.8146595337498184e-13,5.443978601249455e-13,0],
            [17.0859375,51.2578125,0],
            [3.6116689443588257e-06,1.0835006833076477e-05,0],
        ], np.float32)/64
        faces = np.array([[0,1,2]], np.int32)
        self.assertTrue(np.any(self.area_vectors(vertices, faces) != 0))
        self.assertTrue(_collinear_candidates(vertices[faces].astype(np.float64))[0])
        self.assertIsNotNone(_collinear_segment(vertices, faces[0]))
        self.assertEqual(_remove_collinear_faces(vertices, faces).shape, (0,3))

    def test_noncollinear_and_empty_inputs_are_unchanged(self):
        vertices = np.array([[0,0,0], [1,0,0], [0,1,0]], np.float32)
        for faces in (np.array([[0,1,2]], np.int32), np.empty((0,3), np.int32)):
            np.testing.assert_array_equal(_remove_collinear_faces(vertices, faces), faces)


if __name__ == '__main__':
    unittest.main()
