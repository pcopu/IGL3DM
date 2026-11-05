"""Small independent checks of the inference, MILP and exported patch contract."""
import argparse,os,sys,unittest,itertools,json
from pathlib import Path
import numpy as np
from run_experiment import infer,sign_solve,energy

RESULTS_ROOT=None


def results_root():
 """Resolve generated records only when a result-dependent test runs."""
 value=RESULTS_ROOT or os.environ.get('SQUARE_SHAPE_OUTPUT')
 if not value:
  raise RuntimeError('Supply --output to this test script, or set SQUARE_SHAPE_OUTPUT for unittest discovery. Run run_experiment.py first.')
 return Path(value)

class SquareTest(unittest.TestCase):
 def test_square_metric(self):
  q=infer(np.array([[0,0],[6,0],[6,10],[0,10]],float))
  self.assertAlmostEqual(q['s'],10)
  self.assertTrue(np.allclose(q['A'].T@q['A']+np.outer(q['dz'],q['dz']),100*np.eye(2)))
  self.assertAlmostEqual(np.degrees(np.arccos(.6)),q['theta'])
 def test_nonparallelogram_rms(self):
  p=np.array([[0,0],[10,0],[12,10],[0,10]],float)
  q=infer(p)
  self.assertAlmostEqual(q['parallelogram_rms'],.5)
 def test_milp_matches_exhaustive_global_minimum(self):
  rng=np.random.default_rng(8)
  for trial in range(8):
   G=rng.normal(size=(6,2));N=np.c_[-G,np.ones(6)];N/=np.linalg.norm(N,axis=1)[:,None]
   m=[{'normal':n} for n in N];pairs=list(itertools.combinations(range(6),2));signs,result=sign_solve(m,pairs)
   exact=min(energy(m,pairs,[1,*s]) for s in itertools.product([-1,1],repeat=5))
   self.assertTrue(result['success']);self.assertAlmostEqual(energy(m,pairs,signs),exact,places=9)
 def test_export_mesh_reprojects_and_reflects(self):
  data=json.loads((results_root()/'selected_patch_data.json').read_text());report=json.loads((results_root()/'integration_report.json').read_text())
  p=[]
  for name in ('conditional_patch_A.ply','conditional_patch_B.ply'):
   lines=(results_root()/name).read_text().splitlines();i=lines.index('end_header')+1;n=len(data['node_ids'])
   p.append(np.array([[float(x) for x in l.split()] for l in lines[i:i+n]]))
   faces=[[int(x) for x in l.split()] for l in lines[i+n:]]
   self.assertEqual(len(faces),report['exported_triangles'])
   self.assertTrue(all(len(f)==4 and f[0]==3 and max(f[1:])<n for f in faces))
  th=np.deg2rad(data['view']*45);xy=np.array(data['xy_screen_right_up']);depth=np.array(data['depth_A_px'])
  for pp,sgn in zip(p,[1,-1]):
   screen_x=pp[:,0]*np.cos(th)+pp[:,1]*np.sin(th)
   screen_depth=-pp[:,0]*np.sin(th)+pp[:,1]*np.cos(th)
   self.assertTrue(np.allclose(screen_x,(xy[:,0]-256)/256))
   self.assertTrue(np.allclose(screen_depth,sgn*depth/256))
   self.assertTrue(np.allclose(pp[:,2],(xy[:,1]+256)/256))
 def test_negative_control_really_fails_shape(self):
  c=json.loads((results_root()/'fixture_tests.json').read_text())['faceted_cylinder_negative_control']
  self.assertLess(c['integrated_edge_rmse'],1e-8)
  self.assertGreater(c['depth_rmse_to_truth_best_global_reflection'],1)
  self.assertLess(c['optimized_normal_smoothness_energy'],c['true_normal_smoothness_energy'])

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True,help='Existing output of run_experiment.py; read-only during these tests')
 args,unittest_args=parser.parse_known_args()
 RESULTS_ROOT=args.output
 unittest.main(argv=[sys.argv[0],*unittest_args],verbosity=2)
