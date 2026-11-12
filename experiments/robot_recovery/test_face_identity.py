"""Truth-scoring and conservative fragment-join fixtures, independent of target data."""
from pathlib import Path
import sys,unittest,copy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from score_physical_faces import score,cyclic
from audit_cell_conflicts import audit
from join_cell_fragments import propose,refit

class FaceIdentityTests(unittest.TestCase):
 def fixture(self):
  xyz=[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[2,0,0]];xy=[[10,10],[30,10],[30,30],[10,30],[60,10]];truth={'vertices':xyz,'faces':[[0,1,2,3]],'views':[{'view':i,'yaw_deg':i*8,'observations':[{'vertex_id':j,'xy':p,'visible':True} for j,p in enumerate(xy)]} for i in range(3)]};points=[{'track_id':str(j),'xyz':x,'observations':{str(i):xy[j] for i in range(3)}} for j,x in enumerate(xyz[:4])];faces=[{'point_indices':[0,1,2,3],'source_cells':[{'sample_index':i} for i in range(3)]}];return points,faces,truth
 def test_full_track_identity_not_just_local_face(self):
  p,f,t=self.fixture();r=score(p,f,t);self.assertEqual(r['face_identity_counts'],{'correct':1});self.assertEqual(r['unique_correct_physical_faces'],1)
  p[0]['observations']['2']=[60,10];f[0]['source_cells']=[{'sample_index':0},{'sample_index':1}];r=score(p,f,t);self.assertEqual(r['face_identity_counts'],{'wrong_track_identity':1});self.assertEqual(r['source_cell_identity_counts'],{'correct_same_cell':1})
 def test_unresolved_denominator_and_ambiguity(self):
  p,f,t=self.fixture();p[0]['observations']['0']=[200,200];r=score(p,f,t);self.assertEqual(r['faces'],1);self.assertEqual(r['strict_correct_face_fraction_all'],0);self.assertEqual(r['face_identity_counts'],{'unresolved':1})
  p,f,t=self.fixture();t['vertices'].append([3,0,0]);t['views'][0]['observations'].append({'vertex_id':5,'xy':[10.5,10],'visible':True});self.assertEqual(score(p,f,t)['face_identity_counts'],{'unresolved':1})
 def test_physical_duplicate_vertices_and_cyclic_order(self):
  p,f,t=self.fixture();t['vertices'].append([0,0,0]);t['faces'].append([5,1,2,3]);self.assertEqual(score(p,f,t)['available_non_degenerate_truth_faces'],1);f[0]['point_indices']=[0,2,1,3];self.assertEqual(score(p,f,t)['face_identity_counts'],{'wrong_topology':1});self.assertEqual(cyclic([0,1,2,3]),cyclic([2,1,0,3]))
 def test_quarantine_all_conflicts_no_winner(self):
  p=[{'xyz':[i,0,0],'track_id':str(i)} for i in range(10)];fs=[{'point_indices':v,'source_cells':[{'sample_index':i}]} for i,v in enumerate([[0,1,2,3],[0,1,4,5],[0,1,6,7],[2,3,8,9]])];before=copy.deepcopy(fs);r,keep=audit(p,fs);self.assertEqual(r['removed_face_indices'],[0,1,2]);self.assertEqual(keep,[fs[3]]);self.assertEqual(fs,before);self.assertEqual(r['after_quarantine']['nonmanifold_edges'],0)
 def test_unique_fragment_join_and_many_to_one_rejection(self):
  p=[{'xyz':[0,0,0],'observations':{str(i):[0,0] for i in range(a,b)}} for a,b in [(0,11),(0,31),(0,31),(0,31),(12,21),(22,31)]];P=np.tile(np.c_[np.eye(2,3),np.zeros(2)],(31,1,1));faces=[{'point_indices':v} for v in [[0,1,2,3],[4,1,2,3]]];r,pairs=propose(p,faces,P);self.assertEqual(pairs,[(0,4)]);faces.append({'point_indices':[5,1,2,3]});r,pairs=propose(p,faces,P);self.assertEqual(pairs,[]);self.assertEqual(sum(x['reason']=='ambiguous_candidate_component' for x in r),2)
  p[4]['observations']['10']=[0,0];r,pairs=propose(p,faces[:2],P);self.assertEqual(pairs,[]);self.assertEqual(r[0]['reason'],'overlapping_observations')
 def test_fragment_refit_uses_only_actual_observations(self):
  yaw=np.arange(40)*4.;P=np.array([[[100*np.cos(np.deg2rad(a)),100*np.sin(np.deg2rad(a)),0,256],[0,0,-100,256]] for a in yaw]);xyz=np.array([.2,-.1,.3]);mk=lambda name,frames:{'track_id':name,'xyz':xyz.tolist(),'observations':{str(i):(P[i,:,:3]@xyz+P[i,:,3]).tolist() for i in frames}};a=mk('a',range(0,11));b=mk('b',range(15,31));r=refit(a,b,P,{5,20},yaw);self.assertIsNotNone(r);np.testing.assert_allclose(r['xyz'],xyz,atol=1e-12);self.assertEqual(set(r['observations']),set(a['observations'])|set(b['observations']));self.assertNotIn('12',r['observations']);self.assertEqual(r['source_track_ids'],['a','b'])

if __name__=='__main__':unittest.main()
