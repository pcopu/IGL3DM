"""Compare fitted mesh depths to calibrated software-depth assessment maps."""
import argparse
import json
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--fit-run",type=Path,required=True)
p.add_argument("--aligned",type=Path,required=True)
a=p.parse_args();d=np.load(a.aligned);rows=[]
for split in ["fit_train_mask","fit_heldout_mask"]:
    old=[];new=[];retained=0;eligible=0
    for i in range(len(d["calibrated"])):
        with np.load(a.fit_run/"renders/data"/f"view_{i:03d}.npz") as pred:depth=pred["depth"];mask=pred["mask"]
        valid=d["valid_mask"][i]&d[split][i];eligible+=int(valid.sum());valid &= mask;retained+=int(valid.sum())
        target=d["calibrated"][i][valid]
        old.extend((d["mesh_depth"][i][valid]-target).tolist());new.extend((depth[valid]-target).tolist())
    if not old:raise ValueError("No supported assessment pixels")
    old=np.array(old);new=np.array(new)
    rows.append({"split":split,"baseline_rmse":float(np.sqrt(np.mean(old**2))),"fitted_rmse":float(np.sqrt(np.mean(new**2))),
                 "eligible_pixels":eligible,"retained_pixels":retained})
result={"comparisons":rows,"interpretation":"Agreement with calibrated software-depth predictions, not ground-truth geometry. Assessment pixels are excluded from fitting but are used by view gates; this is not blind independent validation. Smooth deformation couples nearby vertices."}
(a.fit_run/"depth_evaluation.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2))
