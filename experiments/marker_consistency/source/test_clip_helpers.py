import importlib.util,tempfile,unittest,json,contextlib,io
import numpy as np
from PIL import Image
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class HelperTests(unittest.TestCase):
 def test_imports_are_safe(self):
  self.assertTrue(callable(load('prepare_measurements').prepare));self.assertTrue(callable(load('reconstruct_video').reconstruct))
 def test_prepare_refuses_nonempty_output(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'keep.txt').write_text('preserve')
   with self.assertRaisesRegex(ValueError,'nonempty'):load('prepare_measurements').prepare(p/'missing',p)
   self.assertEqual((p/'keep.txt').read_text(),'preserve')
 def test_reconstruct_refuses_nonempty_output(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'keep.txt').write_text('preserve')
   with self.assertRaisesRegex(ValueError,'nonempty'):load('reconstruct_video').reconstruct(p/'missing',p/'missing',p)
   self.assertEqual((p/'keep.txt').read_text(),'preserve')
 def test_invalid_parameters_do_not_create_outputs(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);prep=load('prepare_measurements');recon=load('reconstruct_video')
   for value in [0,-1,1.5]:
    with self.assertRaisesRegex(ValueError,'period_frames'):prep.prepare(p/'missing',p/'prep',period_frames=value)
    with self.assertRaisesRegex(ValueError,'period_frames'):recon.reconstruct(p/'missing',p/'missing',p/'recon',period_frames=value)
   for value in [0,-24,float('nan'),float('inf')]:
    with self.assertRaisesRegex(ValueError,'source_fps'):prep.prepare(p/'missing',p/'prep',source_fps=value)
   with self.assertRaisesRegex(ValueError,'holdout_radius'):recon.reconstruct(p/'missing',p/'missing',p/'recon',holdout_radius=-1)
   self.assertFalse((p/'prep').exists());self.assertFalse((p/'recon').exists())
 def test_97_sample_fixture_keeps_period_and_offset_explicit(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);inputs=root/'tracking';inputs.mkdir()
   # White frames are deliberate: this tests provenance/triangulation, not cell detection.
   Image.new('RGB',(512,512),'white').save(inputs/'white.png')
   manifest={'sample_count':97,'working_size':[512,512],'frames':[{'path':'white.png','timestamp_seconds':i/24} for i in range(97)]}
   (inputs/'video_manifest.json').write_text(json.dumps(manifest))
   recon=load('reconstruct_video');xyz=np.array([.25,.15,.35]);observations=[]
   for i in range(97):
    camera=np.array([2*np.pi*i/96,0,0,np.log(256),256,256]);A,b=recon.matrix(camera)
    xy=(A@xyz+b).tolist() if i<96 else [10000,10000]
    observations.append({'sample_index':i,'timestamp_seconds':i/24,'xy':xy})
   (inputs/'tracks.json').write_text(json.dumps({'test_vertex':{'observations':observations}}))
   measurements=root/'measurements';output=root/'geometry'
   with contextlib.redirect_stdout(io.StringIO()):
    load('prepare_measurements').prepare(inputs,measurements,96,14,24)
    recon.reconstruct(inputs,measurements,output,96,(12,36,60,84),2,14)
   meta=json.loads((measurements/'measurement_manifest.json').read_text())
   self.assertEqual(meta['measured_sample_count'],97)
   self.assertEqual(meta['selected_sample_indices'],list(range(0,96,12)))
   self.assertEqual(meta['selected_original_indices'],list(range(14,110,12)))
   points=json.loads((output/'candidate_points.json').read_text())
   self.assertEqual(len(points),1)
   self.assertEqual(points[0]['sample_span'],[0,95])
   self.assertNotIn('96',points[0]['observations'])
   self.assertTrue(points[0]['conditional_pass'])
   np.testing.assert_allclose(points[0]['xyz'],xyz,atol=1e-10)
   # An empty candidate set is a valid negative outcome, not a rendering crash.
   (inputs/'tracks.json').write_text('{}')
   with contextlib.redirect_stdout(io.StringIO()):
    recon.reconstruct(inputs,measurements,root/'empty_geometry',96,(12,36,60,84),2,14)
   self.assertEqual(json.loads((root/'empty_geometry'/'candidate_points.json').read_text()),[])
   self.assertTrue((root/'empty_geometry'/'candidate_grid_mesh_preview.png').exists())
if __name__=='__main__':unittest.main()
