import unittest
import numpy as np
from PIL import Image, ImageDraw
from igl3dm.core import (Camera, orbit_cameras, split_atlas, segment, grid_points, silhouette_fields,
                        carve, extract_mesh, mesh_integrity, mask_metrics, project_occupancy)


class GeometryTests(unittest.TestCase):
    def test_camera_basis_and_projection(self):
        for yaw in [0,22.5,90,180,270]:
            c=Camera(yaw,12)
            basis=np.array(c.basis())
            np.testing.assert_allclose(basis@basis.T,np.eye(3),atol=1e-6)
            np.testing.assert_allclose(c.project(np.array([[0,0,0]]),100),[[49.5,49.5]])
        np.testing.assert_allclose(Camera(0).project(np.array([[1,0,1]]),100),[[99.5,-0.5]])

    def test_irregular_grid_does_not_recenter_animals(self):
        tiles=split_atlas(Image.new("RGB",(1261,1247),"white"))
        self.assertEqual(len(tiles),16)
        self.assertEqual(len(set(t.size for t in tiles)),1)
        with self.assertRaises(ValueError):split_atlas(Image.new("RGB",(20,20)))

    def test_segment_fills_white_enclosed_regions(self):
        im=Image.new("RGB",(64,64),"white")
        ImageDraw.Draw(im).ellipse((16,10,48,55),outline="black",width=2)
        mask,info=segment(im)
        self.assertTrue(mask[32,32]);self.assertFalse(mask[0,0])
        self.assertFalse(info["touches_frame"])

    def test_uniform_gutter_removes_thick_atlas_frames(self):
        atlas=Image.new("RGB",(256,128),"white")
        draw=ImageDraw.Draw(atlas)
        for row in range(2):
            for col in range(4):
                x,y=col*64,row*64
                draw.rectangle((x,y,x+63,y+63),outline="black",width=4)
                draw.ellipse((x+18,y+12,x+46,y+52),outline="black",width=2)
        with self.assertRaises(ValueError):segment(split_atlas(atlas,2,4,gutter=2)[0])
        tiles=split_atlas(atlas,2,4,gutter=6)
        results=[segment(tile) for tile in tiles]
        self.assertEqual(len({tuple(info["bbox_xyxy"]) for _,info in results}),1)
        for mask,info in results:
            self.assertTrue(mask[26,26])
            self.assertFalse(info["touches_frame"])
            self.assertLess(info["foreground_fraction"],.5)

    def test_empty_segmentation_fails(self):
        with self.assertRaises(ValueError):segment(Image.new("RGB",(64,64),"white"))

    def test_alpha_segmentation(self):
        im=Image.new("RGBA",(64,64),(0,0,0,0))
        ImageDraw.Draw(im).rectangle((20,10,40,50),fill=(255,255,255,255))
        mask,info=segment(im)
        self.assertEqual(info["mode"],"alpha");self.assertTrue(mask[20,30])

    def test_known_sphere_carves_and_mesh_is_closed(self):
        size=64;n=24
        y,x=np.mgrid[:size,:size]
        mask=((x+0.5-size/2)**2+(y+0.5-size/2)**2)<=(size*.32)**2
        cameras=[Camera(i*22.5) for i in range(16)]
        points=grid_points(n)
        fields=silhouette_fields([mask]*16,cameras,points)
        field,occupied,info=carve(fields,n,0,0.6)
        self.assertGreater(info["voxel_count"],100)
        vertices,faces=extract_mesh(field)
        integrity=mesh_integrity(vertices,faces)
        self.assertTrue(integrity["watertight_edge_incidence"])
        self.assertEqual(integrity["nonmanifold_edges"],0)
        self.assertGreater(integrity["signed_volume"],0)
        self.assertTrue(np.all(np.abs(vertices)<.8))
        metrics=mask_metrics(project_occupancy(occupied,points,cameras,size),[mask]*16)
        self.assertGreater(metrics["mean_iou"],.85)

    def test_small_nonzero_triangles_are_not_dropped(self):
        # Near-iso-level intersections create tiny valid triangles. Removing
        # them by an arbitrary area threshold opened four edges in lion-001.
        field=-np.ones((12,12,12),dtype=np.float32)
        field[3:9,3:9,3:9]=1
        field[2,4,4]=1e-5
        vertices,faces=extract_mesh(field)
        integrity=mesh_integrity(vertices,faces)
        self.assertEqual(integrity["boundary_edges"],0)
        self.assertTrue(integrity["watertight_edge_incidence"])

    def test_exact_zero_level_samples_share_vertices(self):
        x,y,z=np.mgrid[:16,:16,:16]
        field=9-((x-8)**2+(y-8)**2+(z-8)**2)
        vertices,faces=extract_mesh(field)
        integrity=mesh_integrity(vertices,faces)
        self.assertEqual(integrity["boundary_edges"],0)
        self.assertTrue(integrity["watertight_edge_incidence"])
        self.assertEqual(len(vertices),len(np.unique(vertices,axis=0)))

    def test_float32_coincident_intersections_are_welded(self):
        field=-np.ones((12,12,12),dtype=np.float32)
        field[3:9,3:9,3:9]=1
        field[2,4,4]=1e-10
        vertices,faces=extract_mesh(field)
        self.assertEqual(len(vertices),len(np.unique(vertices,axis=0)))
        self.assertTrue(mesh_integrity(vertices,faces)["watertight_edge_incidence"])

    def test_dual_elevation_camera_bands(self):
        cameras=orbit_cameras(32,[15,-15])
        self.assertEqual(cameras[15].yaw_degrees,337.5)
        self.assertEqual(cameras[16].yaw_degrees,0)
        self.assertEqual(cameras[16].elevation_degrees,-15)
        self.assertEqual(cameras[31].yaw_degrees,337.5)
        with self.assertRaises(ValueError):orbit_cameras(31,[15,-15])
        with self.assertRaises(ValueError):orbit_cameras(16,[float("nan")])

    def test_yaw_rotation_convention(self):
        # Animal front is -Y. It appears on the left at yaw +90.
        p=Camera(90).project(np.array([[0,-.5,0]]),100)
        np.testing.assert_allclose(p,[[24.5,49.5]],atol=1e-6)

    def test_empty_hull_fails(self):
        with self.assertRaises(ValueError):carve(-np.ones((16,12**3)),12)

    def test_relaxed_hull_reports_tolerance(self):
        n=12;fields=np.ones((16,n**3));fields[0]=-1
        with self.assertRaises(ValueError):carve(fields,n,0,0)
        _,occupied,info=carve(fields,n,1,0)
        self.assertEqual(info["minimum_supporting_views"],15)
        self.assertEqual(int(occupied.sum()),n**3)


if __name__=="__main__":unittest.main()
