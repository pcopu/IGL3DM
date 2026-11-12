"""Independent numerical fixtures. Never use the target generator or target shape."""
import unittest,importlib.util,json,tempfile
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bspline_camera',HERE/'fit_bspline_orbit.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
class RecoveryTests(unittest.TestCase):
 def test_basis_nonnegative_partition(self):
  x=np.linspace(0,1,1001);b=BSpline.design_matrix(x,[0,0,0,0,.5,1,1,1,1],3).toarray();self.assertTrue((b>=0).all());np.testing.assert_allclose(b.sum(1),1,atol=1e-14)
 def test_nested_constant_agrees(self):
  p=np.array([np.log(192),.03,-.02,253]);q=np.r_[np.full(5,np.log(2*np.pi)-p[0]),p[1:]];a,b=model.design(np.arange(193),q,(0,192));aa,bb=model.constant.design(np.arange(193),p);np.testing.assert_allclose(a,aa,atol=1e-9);np.testing.assert_allclose(b,bb,atol=1e-9)
 def test_speed_bounds_monotone(self):
  q=np.r_[np.log(np.deg2rad([.01,5.625,.3,5.625,.01])),0,0,256];t=np.linspace(0,192,20001);angle=model.yaw(t,q,(0,192));self.assertTrue((np.diff(angle)>0).all());speed=np.diff(angle)/np.diff(t);self.assertGreaterEqual(speed.min(),np.deg2rad(.01)-1e-10);self.assertLessEqual(speed.max(),np.deg2rad(5.625)+1e-10)
 def test_integration_precision(self):
  q=np.r_[np.log(np.deg2rad([.4,3,3,3,.1])),.02,.01,256];t=np.arange(193);base=model.yaw(t,q,(0,192));old=model.INTEGRATION_STEPS_PER_FRAME
  try:model.INTEGRATION_STEPS_PER_FRAME=512;fine=model.yaw(t,q,(0,192))
  finally:model.INTEGRATION_STEPS_PER_FRAME=old
  self.assertLess(np.abs(base-fine).max(),1e-6)
 def test_refine_keeps_ids_edges_and_shift_bound(self):
  spec=importlib.util.spec_from_file_location('refiner',HERE/'refine_junctions.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  import cv2
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'root';imgs=Path(tmp)/'images';out=Path(tmp)/'out';root.mkdir();imgs.mkdir()
   image=np.full((48,48),255,np.uint8);cv2.line(image,(8,24),(40,24),0,2);cv2.line(image,(24,8),(24,40),0,2);cv2.imwrite(str(imgs/'frame.png'),image)
   graph=[{'sample_index':0,'nodes':[{'node_id':0,'xy':[24.4,23.7],'neighbor_ids':[]}],'closed_cells':[]}];(root/'frame_graphs.json').write_text(json.dumps(graph));(root/'manifest.json').write_text(json.dumps({'source_sha256':'fixture'}));(imgs/'video_manifest.json').write_text(json.dumps({'frames':[{'sample_index':0,'path':'frame.png'}]}))
   for v in ['graph_joint','graph_joint_cycle_veto']:
    d=root/v;d.mkdir();(d/'associations.json').write_text('[]');(d/'tracks.json').write_text(json.dumps({'x':{'observations':[{'sample_index':0,'node_id':0,'xy':[24.4,23.7]}]}}))
   m.refine(root,imgs,out);g=json.loads((out/'frame_graphs.json').read_text());self.assertLessEqual(np.linalg.norm(np.array(g[0]['nodes'][0]['xy'])-[24.4,23.7]),1.50001);self.assertEqual(g[0]['closed_cells'],[]);self.assertEqual(g[0]['nodes'][0]['neighbor_ids'],[])
   t=json.loads((out/'graph_joint/tracks.json').read_text());self.assertEqual(list(t),['x']);self.assertEqual(t['x']['observations'][0]['xy'],g[0]['nodes'][0]['xy'])
   with self.assertRaises(ValueError):m.refine(root,imgs,out)

 def test_explicit_camera_triangulation_and_endpoint_exclusion(self):
  from PIL import Image
  import contextlib,io
  spec=importlib.util.spec_from_file_location('explicit_reconstruction',HERE/'reconstruct_explicit_camera.py');recon=importlib.util.module_from_spec(spec);spec.loader.exec_module(recon)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);inputs=root/'tracking';inputs.mkdir();measurement=root/'measurements';measurement.mkdir();Image.new('RGB',(512,512),'white').save(inputs/'white.png');frames=[{'path':'white.png','sample_index':i,'timestamp_seconds':i/24} for i in range(97)];(inputs/'video_manifest.json').write_text(json.dumps({'sample_count':97,'working_size':[512,512],'frames':frames}));(measurement/'measurement_manifest.json').write_text(json.dumps({'normalization':{'common_scale':1,'common_x_padding':0},'selected_sample_indices':list(range(0,96,12))}));xyz=np.array([.25,.15,.35]);observations=[];views=[]
   for i in range(97):
    a,b=recon.matrix([2*np.pi*i/96,.03,.01,np.log(256),253,256]);xy=(a@xyz+b).tolist() if i<96 else [10000,10000];observations.append({'sample_index':i,'xy':xy});views.append({'sample_index':i,'yaw_deg':i*360/96,'orthographic_projection_2x4_normalized512':np.c_[a,b].tolist()})
   (inputs/'tracks.json').write_text(json.dumps({'fixture':{'observations':observations}}));camera=root/'cameras.json';camera.write_text(json.dumps({'views':views}))
   with contextlib.redirect_stdout(io.StringIO()):recon.reconstruct(inputs,measurement,root/'out',96,(12,36,60,84),2,0,camera)
   points=json.loads((root/'out/candidate_points.json').read_text());self.assertEqual(len(points),1);np.testing.assert_allclose(points[0]['xyz'],xyz,atol=1e-10);self.assertNotIn('96',points[0]['observations']);self.assertTrue(points[0]['conditional_pass'])
   views[0]['sample_index']=2;camera.write_text(json.dumps({'views':views}))
   with self.assertRaisesRegex(ValueError,'sample order'):recon.reconstruct(inputs,measurement,root/'bad',96,(12,36,60,84),2,0,camera)


 def test_observed_cells_preserve_points_require_span_and_reject_collisions(self):
  from PIL import Image
  from unittest.mock import patch
  import contextlib,io
  spec=importlib.util.spec_from_file_location('cell_assembly',HERE/'assemble_observed_cells.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);tracking=root/'tracking';tracking.mkdir();Image.new('RGB',(64,64),'white').save(tracking/'white.png');(tracking/'video_manifest.json').write_text(json.dumps({'frames':[{'path':'white.png'}]*3}));measurement=root/'measurement.json';measurement.write_text(json.dumps({'normalization':{'common_scale':8,'common_x_padding':0}}));xy=[[100,100],[140,100],[140,140],[100,140]];points=[{'conditional_pass':True,'xyz':[i,0,0],'observations':{str(k):p for k in range(3)}} for i,p in enumerate(xy)];pointfile=root/'points.json';pointfile.write_text(json.dumps(points));camera=root/'camera.json';views=[{'sample_index':i,'yaw_deg':i*8} for i in range(3)];camera.write_text(json.dumps({'views':views}));graph={'nodes':[{'node_id':i,'xy':p} for i,p in enumerate(xy)],'cells':[{'node_ids':[0,1,2,3],'cell_id':0}]}
   with patch.object(a,'detect_cells',return_value=graph),contextlib.redirect_stdout(io.StringIO()):r=a.assemble(tracking,pointfile,measurement,camera,root/'out')
   self.assertEqual(r['observed_quads'],1);self.assertEqual(json.loads((root/'out/candidate_points.json').read_text()),points)
   views[-1]['yaw_deg']=14;camera.write_text(json.dumps({'views':views}))
   with patch.object(a,'detect_cells',return_value=graph),contextlib.redirect_stdout(io.StringIO()):r=a.assemble(tracking,pointfile,measurement,camera,root/'small_span')
   self.assertEqual(r['observed_quads'],0)
   views[-1]['yaw_deg']=16;camera.write_text(json.dumps({'views':views}));graph['nodes'].append({'node_id':4,'xy':[100.1,100.1]})
   with patch.object(a,'detect_cells',return_value=graph),contextlib.redirect_stdout(io.StringIO()):r=a.assemble(tracking,pointfile,measurement,camera,root/'collision')
   self.assertEqual(r['observed_quads'],0)
   with self.assertRaises(ValueError):a.assemble(tracking,pointfile,measurement,camera,root/'out')

if __name__=='__main__':unittest.main()
