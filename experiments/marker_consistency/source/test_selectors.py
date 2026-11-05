import unittest
import numpy as np
from graph_consistency import canonical_cycle,select_segments
from trajectory_consistency import select

class SelectorTests(unittest.TestCase):
 def test_cycle_ids_preserve_connectivity_not_start_or_winding(self):
  expected=canonical_cycle(['a','b','c','d'])
  self.assertEqual(expected,canonical_cycle(['c','d','a','b']))
  self.assertEqual(expected,canonical_cycle(['d','c','b','a']))
  self.assertNotEqual(expected,canonical_cycle(['a','c','b','d']))
 def test_missing_graph_support_splits_without_rejoining(self):
  obs=[{'sample_index':i,'xy':[i,2.]} for i in range(9)]
  tracks={'t':{'observations':obs}}
  rows=[]
  for i in range(9):
   rows.append({'sample_index':i,'node_id':None if i==4 else i,'incident_detected_cells':4,'stable_full_cell_count_from_previous':0 if i in (0,4,5) else 1,'stable_neighbor_count_from_previous':0 if i in (0,4,5) else 2})
  selected,_=select_segments(tracks,{'tracks':{'t':rows}})
  self.assertEqual(len(selected),2)
  self.assertEqual([t['observations'] for t in selected.values()],[obs[:4],obs[5:]])
  self.assertTrue(all(t['source_track_id']=='t' for t in selected.values()))
 def test_exact_orbit_passes_and_end_slip_fails(self):
  def track(slip=False):
   oo=[]
   for i in range(0,33):
    angle=i*2*np.pi/96
    x=256+50*np.cos(angle)+30*np.sin(angle)+(12 if slip and i>26 else 0)
    oo.append({'sample_index':i,'xy':[x,210.]})
   return {'observations':oo}
  original=track();selected,audit=select({'exact':original,'slip':track(True)},96)
  self.assertEqual(set(selected),{'exact'})
  self.assertIs(selected['exact'],original)
  self.assertLess(audit[0]['endpoint_prediction_p95_px'],1e-8)
 def test_short_baseline_is_not_promoted(self):
  t={'observations':[{'sample_index':i,'xy':[260.,210.]} for i in range(8)]}
  selected,audit=select({'short':t},96)
  self.assertEqual(selected,{})

class OrbitFitTests(unittest.TestCase):
 def test_shared_orbit_recovers_synthetic_camera_without_shape_input(self):
  from fit_shared_orbit import design,fit
  rng=np.random.default_rng(71);truth=np.array([np.log(120.),np.deg2rad(8),np.deg2rad(2),250.]);tracks={}
  for j in range(35):
   time=np.arange(j%60,j%60+32,dtype=float);xyz=rng.uniform(-.6,.6,3);A,b=design(time,truth);xy=np.einsum('nij,j->ni',A,xyz)+b
   tracks[f'synthetic_{j}']={'observations':[{'sample_index':int(t),'xy':p.tolist()} for t,p in zip(time,xy)]}
  result=fit(tracks,initial_period=96,minimum_samples=16)
  self.assertTrue(result['optimizer_success'])
  np.testing.assert_allclose(result['parameter_vector'],truth,atol=1e-4)
  self.assertLess(result['validation_after']['endpoint_observation_errors_px']['p95'],1e-5)

class ValidationTests(unittest.TestCase):
 def test_invalid_period_and_dimensions_are_rejected(self):
  for value in [0,-1,float('nan'),float('inf')]:
   with self.assertRaisesRegex(ValueError,'period'):select({},value)
  with self.assertRaisesRegex(ValueError,'dimensions'):select({},96,(1024,512))
class PreviewTests(unittest.TestCase):
 def test_empty_selection_emits_negative_result_without_filling(self):
  import json,tempfile
  from pathlib import Path
  from build_variable_preview import build
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)
   fixtures={'tracks':{},'manifest':{'working_size':[512,512],'frames':[]},'graph':{'tracks':{}},'cameras':{'views':[],'status':'experimental','coordinates':'relative test gauge'},'selection':{'real':{'variable':{'selected_candidate_track_ids':[]}}}}
   for name,value in fixtures.items():(p/(name+'.json')).write_text(json.dumps(value))
   result=build(*(p/(name+'.json') for name in ['tracks','manifest','graph','cameras','selection']),p/'out')
   self.assertEqual(result['points'],0);self.assertEqual(result['observed_quad_faces_seen_at_least_three_frames'],0)
   self.assertTrue((p/'out'/'experimental_geometry_preview.png').exists())
   with self.assertRaisesRegex(ValueError,'nonempty'):build(*(p/(name+'.json') for name in ['tracks','manifest','graph','cameras','selection']),p/'out')
if __name__=='__main__':unittest.main()
