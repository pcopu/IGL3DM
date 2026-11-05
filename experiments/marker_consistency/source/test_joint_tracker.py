"""Structural and safe-output regressions, not physical-identity proofs."""
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from graph_tracker import detect, emit_tracks, run
from run_joint_fixed_gate import run as gate
from validate_joint_artifacts import validate


class JointTrackerTests(unittest.TestCase):
    def test_blank_has_no_nodes(self):
        graph = detect(np.full((96, 96), 255, np.uint8), cv2.SIFT_create())
        self.assertEqual(len(graph['xy']), 0)
        self.assertEqual(graph['descriptors'].shape, (0, 256))

    def test_gap_restarts_identity(self):
        graphs = [{'xy': np.array([[10., 20.]])} for _ in range(3)]
        frames = [{'timestamp_seconds': i / 24} for i in range(3)]
        tracks = emit_tracks(graphs, [{0: 0}, {}], frames, 'test')
        self.assertEqual([len(t['observations']) for t in tracks.values()], [2, 1])
        self.assertEqual(tracks['g0000000']['ended_at_sample'], 1)
        self.assertIn('no_gap_bridge', tracks['g0000000']['end_reason'])

    def test_blank_roundtrip_and_source_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'source'; source.mkdir()
            cv2.imwrite(str(source / 'blank.png'), np.full((96, 96), 255, np.uint8))
            (source / 'video_manifest.json').write_text(json.dumps({'frames': [
                {'path': 'blank.png', 'sample_index': i, 'timestamp_seconds': i / 24}
                for i in range(3)]}))
            destination = root / 'out'; destination.mkdir()
            run(source, destination)
            report = validate(destination)
            self.assertEqual(report['graph_joint']['observations'], 0)
            wrong = root / 'wrong.py'; wrong.write_text('# Not the source')
            with self.assertRaises(AssertionError):
                validate(destination, wrong)

    def test_gate_output_and_period_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); tracks = root / 'input.json'; tracks.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'positive'):
                gate(tracks, root / 'invalid', 0)
            self.assertFalse((root / 'invalid').exists())
            result = gate(tracks, root / 'output', 96)
            self.assertEqual(result['selected_tracks'], 0)
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                gate(tracks, root / 'output', 96)


if __name__ == '__main__':
    unittest.main()
