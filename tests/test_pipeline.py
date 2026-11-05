"""Reproducible analytic fixture, not a manually modeled animal."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw


@unittest.skipUnless(shutil.which("blender"),"Blender is required for the full export/render smoke test")
class PipelineTests(unittest.TestCase):
    def test_one_command_produces_verified_mesh_and_turntable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            atlas=Image.new("RGB",(256,256),"white")
            draw=ImageDraw.Draw(atlas)
            for row in range(4):
                for col in range(4):
                    x,y=col*64,row*64
                    draw.ellipse((x+12,y+12,x+51,y+51),fill=(65,170,100))
            atlas.save(root/"atlas.png")
            command=[sys.executable,"-m","igl3dm.cli",str(root/"atlas.png"),
                     "--output",str(root/"output"),"--resolution","24","--image-size","64",
                     "--render-size","64","--max-misses","0","--gutter","0","--render"]
            result=subprocess.run(command,text=True,capture_output=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            out=root/"output"
            report=json.loads((out/"report.json").read_text())
            self.assertIsNone(report["input"]["imagegen_calls_for_this_input"])
            self.assertFalse(report["manual_modeling"])
            self.assertTrue(report["mesh"]["watertight_edge_incidence"])
            self.assertEqual(report["render_status"],"completed")
            self.assertGreater(report["actual_mesh_reprojection"]["mean_iou"],.85)
            self.assertEqual(report["render_validation"]["unseen_yaw_frames"],16)
            self.assertFalse(report["render_validation"]["geometry_changed_by_renderer"])
            self.assertEqual((out/"renders"/"model.glb").read_bytes()[:4],b"glTF")
            with Image.open(out/"turntable.gif") as gif:self.assertGreaterEqual(gif.n_frames,1)
            with np.load(out/"renders"/"data"/"view_000.npz") as data:
                self.assertTrue(np.isfinite(data["depth"][data["mask"]]).all())
                self.assertTrue(np.isfinite(data["position"][data["mask"]]).all())
                self.assertTrue(np.isnan(data["depth"][~data["mask"]]).all())
            # A repeated command must not overwrite the completed evidence.
            repeat=subprocess.run(command,text=True,capture_output=True,timeout=10)
            self.assertNotEqual(repeat.returncode,0)
            self.assertIn("not empty",repeat.stderr)


if __name__=="__main__":unittest.main()
