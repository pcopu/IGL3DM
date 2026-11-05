import unittest
import numpy as np
from audit_quad_shape import audit

class ShapeAuditTests(unittest.TestCase):
    def test_square_rectangle_and_nonplanar_diagnostic(self):
        square=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],float)
        report=audit(square,[[0,1,2,3]],[True])['all_faces']
        self.assertEqual(report['edge_length_ratio']['median'],1)
        self.assertEqual(report['best_fit_plane_rms_fraction_mean_edge']['max'],0)
        square[:,0]*=2
        self.assertEqual(audit(square,[[0,1,2,3]],[False])['all_faces']['edge_length_ratio']['median'],2)
        square[0,2]=.2
        self.assertGreater(audit(square,[[0,1,2,3]],[False])['all_faces']['best_fit_plane_rms_fraction_mean_edge']['median'],0)
    def test_no_conditional_faces_and_no_changes(self):
        vertices=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],float);before=vertices.copy()
        self.assertEqual(audit(vertices,[[0,1,2,3]],[False])['conditional_faces'],{'faces':0})
        np.testing.assert_array_equal(vertices,before)

if __name__=='__main__':unittest.main()
