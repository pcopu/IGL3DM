# Video ingestion and candidate tracking harness

This is infrastructure for a future supplied clip, **not a completed real-video reconstruction**. No actual generated turntable video has been tested here. The native animation attempt in the separate experiment returned a static sheet; a static image or copied closing frame cannot establish temporal consistency.

`source/video_tracks.py` decodes a local video with timestamps, samples frames, detects grid junction candidates and propagates them using forward/backward optical flow and local image checks. A missing or ambiguous point terminates its track. The implementation does not invent hidden points or silently join reappearing candidates to an earlier identity.

Camera geometry is not guessed from elapsed time. Optional explicit projection matrices must match sampled frame coordinates and timestamps; without them, output is2D candidate observations only. Providing matrices permits conditional DLT triangulation, not proof that those cameras or correspondences are correct. Keep raw clip/arrays/point artifacts under ignored local runs.

```sh
python experiments/marker_consistency/source/video_tracks.py \
  --video path/to/authorized-clip.mp4 --output runs/video-tracks \
  --sample-fps 12 --max-frames 600 --size 512
# Add --cameras-json only with an explicitly established camera convention.
python -m unittest discover -s experiments/marker_consistency/source -p 'test_*.py' -v
```

The optional OpenCV/SciPy/Pillow/NumPy environment passes13 marker/grid/video tests. Video tests use synthetic decoded translation and complete occlusion, plus explicit projection-matrix triangulation and degenerate-camera rejection. They validate code mechanics, not detection accuracy or geometry on a real rotating character. No model weights or real user clip are included.
