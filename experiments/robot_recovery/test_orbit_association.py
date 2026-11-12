"""Independent fixtures for withheld-image isolation and competing-model ambiguity."""
import unittest,copy,tempfile,json,contextlib,io
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from associate_orbit_hypotheses import segment,choose,remove_heldout_collisions,run,support_gate

class OrbitAssociationTests(unittest.TestCase):
 def test_only_observed_samples_in_connected_support(self):
  self.assertEqual(segment([True,False,True,True,False,False,True],0,3),[0,2,3]);self.assertEqual(segment([True,False,False,True],0,3),[])
 def test_sparse_periodic_hit_paths_fail_density_gate(self):
  win=np.arange(20);yaw=win*5.;g=list(range(0,20,2));self.assertTrue(support_gate(g,win,yaw,False));self.assertFalse(support_gate(g,win,yaw,True));self.assertTrue(support_gate(list(range(19)),win,yaw,True));self.assertFalse(support_gate([],win,yaw,True))
 def test_competing_supported_models_are_not_forced(self):
  P=np.tile(np.c_[np.eye(2,3)*100,np.zeros(2)],(10,1,1));a={'xyz':[0,0,0],'calibration_nodes':[(i,0) for i in range(9)],'train_p95_px':.3};b={'xyz':[.1,0,0],'calibration_nodes':[(0,0)]+[(i,1) for i in range(1,9)],'train_p95_px':.4};ranked,selected,conflicts,veto=choose([a,b],P,True);self.assertEqual(selected,[]);self.assertEqual(len(veto),2)
  b['xyz']=[.01,0,0];ranked,selected,conflicts,veto=choose([a,b],P,True);self.assertEqual(len(selected),1);self.assertEqual(veto,{})
 def test_colliding_heldout_nodes_all_removed_without_model_change(self):
  points=[{'xyz':[1,2,3],'observations':{'0':[10,20],'4':[11,20]}},{'xyz':[4,5,6],'observations':{'1':[10,20],'4':[11,20]}}];rows=[{'predictions':[{'sample_index':4,'node_id':7,'matched':True,'nearest_distance_px':.2}]} for _ in range(2)];before=copy.deepcopy(points);self.assertEqual(remove_heldout_collisions(points,rows),2);self.assertEqual([p['xyz'] for p in points],[p['xyz'] for p in before]);self.assertNotIn('4',points[0]['observations']);self.assertTrue(all(not r['predictions'][0]['matched'] for r in rows))
 def test_heldout_pixels_cannot_change_selected_models(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);images=root/'images';images.mkdir();frames=[];views=[];nodes={};truth=np.array([[.2,.1,-.6],[-.3,.2,-.2],[.1,-.2,.2],[-.1,.3,.6]])
   for i in range(24):
    Image.new('L',(512,512),i).save(images/f'{i}.png');frames.append({'sample_index':i,'timestamp_seconds':i/24,'path':f'{i}.png'});a=np.deg2rad(i*7.5);P=np.array([[160*np.cos(a),160*np.sin(a),0,256],[0,0,-160,256]]);views.append({'sample_index':i,'yaw_deg':i*7.5,'orthographic_projection_2x4_normalized512':P.tolist()});nodes[i]=truth@P[:,:3].T+P[:,3]
   (images/'video_manifest.json').write_text(json.dumps({'frames':frames}));camera=root/'camera.json';camera.write_text(json.dumps({'views':views}));fake=lambda im:(nodes[int(im[0,0])].astype(np.float32),None,None)
   with patch('associate_orbit_hypotheses.junctions',side_effect=fake),contextlib.redirect_stdout(io.StringIO()):run(images,camera,root/'original',True,True)
   for i in range(24):
    if i%5==4:nodes[i]=nodes[i]+[80,70]
   with patch('associate_orbit_hypotheses.junctions',side_effect=fake),contextlib.redirect_stdout(io.StringIO()):run(images,camera,root/'changed_heldout',True,True)
   a=json.loads((root/'original/candidate_points.json').read_text());b=json.loads((root/'changed_heldout/candidate_points.json').read_text());self.assertGreater(len(a),0);self.assertEqual(len(a),len(b));self.assertEqual([p['calibration_node_ids'] for p in a],[p['calibration_node_ids'] for p in b]);np.testing.assert_array_equal([p['xyz'] for p in a],[p['xyz'] for p in b]);ma=json.loads((root/'original/metrics.json').read_text());mb=json.loads((root/'changed_heldout/metrics.json').read_text());self.assertGreater(mb['heldout_nearest_error_px']['p95'],ma['heldout_nearest_error_px']['p95']+50)

if __name__=='__main__':unittest.main()
