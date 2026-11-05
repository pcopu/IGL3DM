"""Optional numerical controls independent of any generated animal."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from PIL import Image

AVAILABLE=all(importlib.util.find_spec(name) is not None for name in ('torch','skimage','trimesh'))

@unittest.skipUnless(AVAILABLE,'Optional volume dependencies are not installed')
class VolumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/'experiments/volume/fit_volume.py'
        spec=importlib.util.spec_from_file_location('volume_experiment',path)
        cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)

    def test_analytic_sphere_render_and_gradient(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.module.primitive_test(Path(tmp))
            r=json.loads((Path(tmp)/'primitive_validation.json').read_text())
            self.assertGreater(r['silhouette_iou'],.9)
            self.assertLess(r['interior_depth_mae'],.05)
            self.assertTrue(r['radius_gradient_positive'])

    def test_radius_optimization_converges(self):
        torch=self.module.torch
        n=40;axis=(torch.arange(n)+.5)*2/n-1
        xyz=torch.meshgrid(axis,axis,axis,indexing='ij')
        distance=torch.sqrt(sum(x*x for x in xyz))
        grid,t=self.module.rays(40,112,[0,45,180])
        radius=torch.nn.Parameter(torch.tensor(.43));opt=torch.optim.Adam([radius],lr=.012)
        with torch.no_grad():target,_=self.module.render((.55-distance)[None,None],grid,t)
        losses=[]
        for _ in range(40):
            opt.zero_grad();pred,_=self.module.render((radius-distance)[None,None],grid,t)
            loss=((pred-target)**2).mean();loss.backward();opt.step();losses.append(float(loss.detach()))
        self.assertLess(abs(float(radius.detach())-.55),.015)
        self.assertLess(losses[-1],losses[0]*.05)

    def test_negative_isovalue_expands_a_known_sphere(self):
        n=24;axis=(np.arange(n)+.5)*2/n-1
        xyz=np.meshgrid(axis,axis,axis,indexing='ij')
        sdf=.55-np.sqrt(sum(x*x for x in xyz))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            zero=self.module.export(sdf,root/'zero')
            expanded=self.module.export(sdf+.04,root/'expanded')
            self.assertTrue(zero['watertight'])
            self.assertTrue(expanded['watertight'])
            self.assertGreater(expanded['volume'],zero['volume'])

    def test_input_guards_reject_unsupported_depth_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'base';base.mkdir();(base/'masks').mkdir()
            (base/'report.json').write_text(json.dumps({'camera_convention':{'yaw_degrees':list(np.arange(16)*22.5),'elevation_degrees':0,'orthographic_scale':2,'yaw0_location':[0,-4,0]}}))
            np.savez_compressed(base/'field.npz',occupied=np.ones((8,8,8),bool))
            y,x=np.mgrid[:8,:8];train=(x+y)%2==0;shape=(16,8,8)
            gate=np.zeros(16,bool);gate[:2]=True
            np.savez_compressed(root/'depth.npz',calibrated=np.ones(shape)*4,valid_mask=np.ones(shape,bool),confidence_weight=np.ones(shape),fit_train_mask=np.tile(train,(16,1,1)),fit_heldout_mask=np.tile(~train,(16,1,1)),view_gate=gate)
            for i in range(16):Image.new('L',(8,8),255).save(base/f'masks/mask_{i:02}.png')
            args=SimpleNamespace(initial_sigma=0.,iterations=1,size=8,grid=8,control=4,depth_weight=4,name='run',depth_prior=root/'depth.npz')
            with self.assertRaisesRegex(ValueError,'fewer than four'):self.module.validate_inputs(args,base,root/'run')
            args.depth_weight=0;self.module.validate_inputs(args,base,root/'run')
            (root/'run').mkdir();(root/'run'/'preserve.txt').write_text('preserve')
            with self.assertRaises(FileExistsError):self.module.validate_inputs(args,base,root/'run')
            self.assertEqual((root/'run'/'preserve.txt').read_text(),'preserve')

if __name__=='__main__':unittest.main()
