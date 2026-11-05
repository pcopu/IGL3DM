"""CPU-only adapter using scikit-image from PyPI, not third-party torchmcubes code.

TripoSR's helper expects native torchmcubes vertices in reversed (z,y,x)
order and reverses them before export. Preserve that interface explicitly.
"""
import numpy as np
import torch
from skimage.measure import marching_cubes as _marching_cubes


def marching_cubes(level, threshold):
    vertices, faces, _, _ = _marching_cubes(
        level.detach().cpu().numpy(), level=threshold, gradient_direction="descent"
    )
    return (torch.from_numpy(np.ascontiguousarray(vertices[:, [2, 1, 0]])),
            torch.from_numpy(np.ascontiguousarray(faces.astype(np.int64))))
