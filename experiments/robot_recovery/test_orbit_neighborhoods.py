"""Independent regression tests for calibration-only endpoint support."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import trim_orbit_neighborhoods as m


class NeighborhoodTests(unittest.TestCase):
    def fixture(self,n=16):
        yaw=np.arange(n)*10.
        P=np.array([[[np.cos(np.deg2rad(a)),np.sin(np.deg2rad(a)),0,100],[0,0,1,100]] for a in yaw])
        points=[]
        for k,xyz in enumerate([[0,0,0],[20,0,30],[-20,0,-30]]):
            obs={str(i):(P[i,:,:3]@xyz+P[i,:,3]).tolist() for i in range(n)}
            points.append({'track_id':f'p{k}','xyz':[8.,9.,10.],'observations':obs,'calibration_node_ids':[[i,k] for i in range(n) if i%5!=4],'sample_span':[0,n-1],'training_reprojection_px':{'n':13,'p95':0.,'median':0.},'condition':2.,'conditional_pass':True})
        return points,P,yaw

    def edges(self,frames):
        return {i:[(0,1),(0,2),(1,2)] for i in frames}

    def test_stability_requires_three_observations_and_thirty_degrees(self):
        points,P,yaw=self.fixture()
        self.assertEqual(m.supported_intervals(points,self.edges([0,3]),yaw)[0],{})
        self.assertEqual(m.supported_intervals(points,self.edges([0,1,2]),yaw)[0],{})
        stable,_=m.supported_intervals(points,self.edges([0,1,3]),yaw)
        self.assertEqual(len(stable),3)

    def test_duplicate_or_reverse_edges_do_not_count_as_distinct_neighbors(self):
        points,P,yaw=self.fixture()
        edges={i:[(0,1),(1,0),(0,1)] for i in [0,5,10]}
        stable,decisions=m.supported_intervals(points,edges,yaw)
        self.assertEqual(stable,{(0,1):[0,5,10]})
        self.assertTrue(all(not d['retained'] for d in decisions))

    def test_neighbors_must_be_simultaneous(self):
        points,P,yaw=self.fixture()
        edges={i:[(0,1)] for i in [0,5,10]}
        edges.update({i:[(0,2)] for i in [1,6,11]})
        stable,decisions=m.supported_intervals(points,edges,yaw)
        self.assertEqual(len(stable),2)
        self.assertFalse(decisions[0]['retained'])

    def test_heldout_edges_rejected_even_when_empty(self):
        points,P,yaw=self.fixture()
        for edges in [{4:[]},{4:[(0,1)]}]:
            with self.assertRaises(ValueError):m.supported_intervals(points,edges,yaw)

    def test_reject_insufficient_span(self):
        points,P,yaw=self.fixture()
        _,decisions=m.supported_intervals(points,self.edges([0,3,8]),yaw)
        self.assertTrue(all(not d['retained'] for d in decisions))
        self.assertEqual(decisions[0]['reason'],'insufficient_remaining_support')

    def test_primary_preserves_xyz_and_only_subsets_actual_observations(self):
        points,P,yaw=self.fixture(); original=copy.deepcopy(points)
        _,decisions=m.supported_intervals(points,self.edges([0,5,10]),yaw)
        output=m.apply_intervals(points,decisions,P,yaw)
        self.assertEqual(len(output),3)
        self.assertEqual(points,original)
        for p in output:
            parent=original[p['parent_point_index']]
            self.assertEqual(p['xyz'],parent['xyz'])
            self.assertEqual(p['observations'],{i:xy for i,xy in parent['observations'].items() if int(i)<=10})
            self.assertEqual(list(map(list,p['calibration_node_ids'])),[v for v in parent['calibration_node_ids'] if v[0]<=10])
            self.assertFalse(p['geometry_refitted'])

    def test_parent_metrics_preserved_retained_metrics_recomputed_without_gate(self):
        points,P,yaw=self.fixture();original=copy.deepcopy(points)
        _,decisions=m.supported_intervals(points,self.edges([0,5,10]),yaw)
        for refit in [False,True]:
            output=m.apply_intervals(points,copy.deepcopy(decisions),P,yaw,refit)
            self.assertEqual(len(output),3)
            for p in output:
                parent=original[p['parent_point_index']]
                self.assertEqual(p['parent_fit_metrics'],{'training_reprojection_px':parent['training_reprojection_px'],'condition':parent['condition'],'calibration_node_ids':parent['calibration_node_ids']})
                obs=[(i,np.asarray(p['observations'][str(i)])) for i,j in p['calibration_node_ids']]
                errors=[np.linalg.norm(P[i,:,:3]@np.asarray(p['xyz'])+P[i,:,3]-xy) for i,xy in obs]
                self.assertEqual(p['training_reprojection_px']['n'],len(obs))
                self.assertAlmostEqual(p['training_reprojection_px']['p95'],np.percentile(errors,95))
                self.assertAlmostEqual(p['training_reprojection_px']['median'],np.median(errors))
                self.assertAlmostEqual(p['condition'],m.fit(obs,P)[2])
                if not refit:
                    self.assertGreater(p['training_reprojection_px']['p95'],1.5)
                    self.assertEqual(p['xyz'],parent['xyz'])
        self.assertEqual(points,original)

    def test_invalid_camera_order_and_calibration_rejected_before_pixels(self):
        for case in ['camera_order','heldout_source','duplicate_source','missing_coordinate','outside_frame_range']:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                points,P,yaw=self.fixture();root=Path(temp);images=root/'images';source=root/'source';images.mkdir();source.mkdir()
                views=[{'sample_index':i,'yaw_deg':float(yaw[i]),'orthographic_projection_2x4_normalized512':P[i].tolist()} for i in range(16)]
                if case=='camera_order':views[0],views[1]=views[1],views[0]
                if case=='heldout_source':points[0]['calibration_node_ids'].append([4,0])
                if case=='duplicate_source':points[0]['calibration_node_ids'].append([0,0])
                if case=='missing_coordinate':del points[0]['observations']['0']
                if case=='outside_frame_range':points[0]['calibration_node_ids'].append([16,0])
                (images/'video_manifest.json').write_text(json.dumps({'frames':[{'path':str(i)} for i in range(16)]}))
                (source/'candidate_points.json').write_text(json.dumps(points));cameras=root/'cameras.json';cameras.write_text(json.dumps({'views':views}))
                with patch.object(m.Image,'open',side_effect=AssertionError('Must reject before accessing image pixels')) as image_open:
                    with self.assertRaisesRegex(ValueError,'Camera/frame order mismatch' if case=='camera_order' else 'Invalid source calibration sample'):
                        m.run(images,cameras,source,root/'output')
                    image_open.assert_not_called()
                self.assertFalse((root/'output').exists())

    def test_missing_observation_is_not_synthesized(self):
        points,P,yaw=self.fixture()
        for p in points:
            del p['observations']['4']
        _,decisions=m.supported_intervals(points,self.edges([0,5,10]),yaw)
        output=m.apply_intervals(points,decisions,P,yaw)
        self.assertTrue(all('4' not in p['observations'] for p in output))

    def test_refit_uses_only_retained_calibration(self):
        points,P,yaw=self.fixture()
        _,decisions=m.supported_intervals(points,self.edges([0,5,10]),yaw)
        expected=m.apply_intervals(points,copy.deepcopy(decisions),P,yaw,True)
        changed=copy.deepcopy(points)
        for p in changed:
            for i in p['observations']:
                if int(i)%5==4 or int(i)>10:p['observations'][i]=[1e9,-1e9]
        actual=m.apply_intervals(changed,copy.deepcopy(decisions),P,yaw,True)
        self.assertEqual(len(actual),3)
        for a,b in zip(expected,actual):
            np.testing.assert_array_equal(a['xyz'],b['xyz'])
            self.assertEqual(a['training_reprojection_px'],b['training_reprojection_px'])
        np.testing.assert_allclose(actual[0]['xyz'],[0,0,0],atol=1e-10)

    def test_run_never_opens_heldout_images_preserves_all_prediction_rows(self):
        points,P,yaw=self.fixture()
        rejected=copy.deepcopy(points[0]);rejected['track_id']='unsupported'
        rejected['observations']={i:[xy[0]+200,xy[1]+200] for i,xy in rejected['observations'].items()}
        points.append(rejected)
        predictions=[{'track_id':p['track_id'],'predictions':[{'sample_index':i,'nearest_distance_px':float(i),'matched':False,'node_id':None,'predicted_xy':[7,8]} for i in [4,9,14]]} for p in points]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);images=root/'images';source=root/'source';images.mkdir();source.mkdir()
            frames=[{'path':f'{i}.png'} for i in range(16)]
            (images/'video_manifest.json').write_text(json.dumps({'frames':frames}))
            for i in range(16):(images/f'{i}.png').write_bytes(b'fixture source bytes')
            (source/'candidate_points.json').write_text(json.dumps(points))
            (source/'heldout_predictions.json').write_text(json.dumps(predictions))
            cameras=root/'cameras.json';cameras.write_text(json.dumps({'views':[{'sample_index':i,'yaw_deg':float(yaw[i]),'orthographic_projection_2x4_normalized512':P[i].tolist()} for i in range(16)]}))
            opened=[]
            def open_image(path):
                i=int(Path(path).stem);self.assertNotEqual(i%5,4);opened.append(i)
                return Image.new('L',(512,512),i)
            def cells(array):
                i=int(array[0,0]);return {'nodes':[{'node_id':k,'xy':p['observations'][str(i)]} for k,p in enumerate(points)],'cells':[{'node_ids':[0,1,2]}] if 2<=i<=12 else []}
            with patch.object(m.Image,'open',side_effect=open_image),patch.object(m,'detect_cells',side_effect=cells):
                m.run(images,cameras,source,root/'output')
            self.assertEqual(opened,[i for i in range(16) if i%5!=4])
            after=json.loads((root/'output/heldout_predictions.json').read_text())
            self.assertEqual(len(after),len(predictions))
            for old,new in zip(predictions,after):
                self.assertEqual(old['track_id'],new['track_id'])
                self.assertEqual(len(old['predictions']),len(new['predictions']))
                for a,b in zip(old['predictions'],new['predictions']):
                    for k,v in a.items():self.assertEqual(v,b[k])
                    self.assertEqual(b['retained_interval'],old['track_id']!='unsupported' and b['sample_index'] in [4,9])
            self.assertEqual(json.loads((source/'heldout_predictions.json').read_text()),predictions)

if __name__=='__main__':unittest.main()
