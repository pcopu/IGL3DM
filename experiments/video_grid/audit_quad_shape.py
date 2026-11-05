"""Report conditional quad shape statistics; never change geometry or certify squares."""
import argparse
import json
from pathlib import Path
import numpy as np


def audit(vertices, faces, conditional):
    values=[]
    for face in faces:
        q=vertices[face]
        edges=np.linalg.norm(np.roll(q,-1,axis=0)-q,axis=1)
        mean=edges.mean()
        if mean<=0 or edges.min()<=0:
            raise ValueError('Collapsed edge prevents a finite shape diagnostic')
        singular=np.linalg.svd(q-q.mean(0),compute_uv=False)
        values.append([edges.max()/edges.min(),edges.std()/mean,singular[-1]/2/mean])
    values=np.asarray(values)
    def summarize(mask):
        selected=values[mask]
        if not len(selected):return {'faces':0}
        result={'faces':len(selected)}
        for i,name in enumerate(['edge_length_ratio','edge_length_cv','best_fit_plane_rms_fraction_mean_edge']):
            result[name]={'median':float(np.median(selected[:,i])),
                          'p95':float(np.percentile(selected[:,i],95)),
                          'max':float(selected[:,i].max())}
        return result
    return {'all_faces':summarize(np.ones(len(values),bool)),
            'conditional_faces':summarize(np.asarray(conditional,bool)),
            'notes':'Diagnostic only. Drawn cells are not guaranteed equal physical squares or planar. No acceptance threshold applied; no geometry changed.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--points',type=Path,required=True,help='Private candidate_points.json')
    parser.add_argument('--faces',type=Path,required=True,help='Private candidate_faces.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Refusing to overwrite output')
    points=json.loads(args.points.read_text());faces=json.loads(args.faces.read_text())
    report=audit(np.asarray([p['xyz'] for p in points]),
                 [f['point_indices'] for f in faces],
                 [f['all_corners_conditional_pass'] for f in faces])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
