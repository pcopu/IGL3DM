import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from igl3dm.core import extract_mesh, save_json


class DepthWarpTests(unittest.TestCase):
    def test_rejects_insufficient_views_without_exporting_geometry(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/"baseline";base.mkdir()
            vertices=[[0,0,0],[1,0,0],[0,1,0]]
            save_json(base/"mesh.json",{"vertices":vertices,"faces":[[0,1,2]],"colors":[[.5,.5,.5]]*3})
            np.savez_compressed(root/"aligned.npz",view_gate=np.array([True,False,False,False]))
            script=Path(__file__).resolve().parents[1]/"experiments/depth_fit/fit_field.py"
            result=subprocess.run([sys.executable,str(script),"--baseline",str(base),"--aligned",str(root/"aligned.npz"),"--output",str(root/"fit")],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            report=json.loads((root/"fit/fit_failure.json").read_text())
            self.assertFalse(report["geometry_changed"])
            self.assertEqual(report["accepted_views"],[0])
            self.assertFalse((root/"fit/mesh.json").exists())

    def test_shared_vertex_field_has_bounded_geometry(self):
        n=16
        axis=(np.arange(n)+.5)*2/n-1
        xyz=np.stack(np.meshgrid(axis,axis,axis,indexing="ij"),axis=-1)
        vertices,faces=extract_mesh(.6-np.linalg.norm(xyz,axis=-1))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/"baseline";base.mkdir()
            save_json(base/"mesh.json",{"vertices":vertices.tolist(),"faces":faces.tolist(),"colors":np.full_like(vertices,.5).tolist()})
            size=64;y,x=np.mgrid[:size,:size];xx=(x+.5)/size*2-1;zz=1-(y+.5)/size*2
            visible=xx**2+zz**2<.58**2
            depth=4-np.sqrt(np.maximum(.6**2-xx**2-zz**2,0))
            train=((x//8+y//8)%2)==0
            np.savez_compressed(root/"aligned.npz",calibrated=np.tile(depth+.01,(16,1,1)),
                mesh_depth=np.tile(depth,(16,1,1)),valid_mask=np.tile(visible,(16,1,1)),
                fit_train_mask=np.tile(train,(16,1,1)),confidence_weight=np.ones((16,size,size)),view_gate=np.ones(16,bool))
            script=Path(__file__).resolve().parents[1]/"experiments/depth_fit/fit_field.py"
            result=subprocess.run([sys.executable,str(script),"--baseline",str(base),"--aligned",str(root/"aligned.npz"),"--output",str(root/"fit")],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            mesh=json.loads((root/"fit/mesh.json").read_text());report=json.loads((root/"fit/fit_report.json").read_text())
            np.testing.assert_array_equal(mesh["faces"],faces)
            self.assertEqual(len(mesh["vertices"]),len(vertices))
            self.assertGreater(report["displacement_max"],0)
            self.assertLessEqual(report["displacement_max"],.03)
            self.assertEqual(report["line_search"][-1]["flipped_or_collapsed_faces"],0)
            self.assertTrue(report["mesh"]["watertight_edge_incidence"])


if __name__=="__main__":unittest.main()
