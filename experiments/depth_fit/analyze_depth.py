#!/usr/bin/env python3
"""Compare software-predicted relative depth to a fixed-camera mesh baseline.

This analysis does not deform geometry or claim that the baseline is ground
truth. It tests whether one positive affine depth calibration per view is a
plausible constraint under the *assumed* orthographic cameras. It requires
square same-framing images; registered DA3 RGB previews are checked explicitly.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, stats
try:
    import cv2
except ImportError:
    cv2 = None


def sample_grid(array, shape):
    yy, xx = np.indices(shape)
    coords = [(yy + .5) * array.shape[0] / shape[0] - .5,
              (xx + .5) * array.shape[1] / shape[1] - .5]
    return ndimage.map_coordinates(array, coords, order=1, mode="nearest")


def robust_affine(x, y, positive=True):
    """Huber IRLS fit with nonnegative slope and explicit zero-slope flag."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    center = float(np.median(x))
    spread = max(float(np.std(x)), 1e-10)
    xn = (x-center)/spread
    design = np.column_stack((xn, np.ones(len(x))))
    weights = np.ones(len(x))
    coeff = np.array([0., np.median(y)])
    for _ in range(30):
        lhs = design.T @ (weights[:, None] * design)
        rhs = design.T @ (weights*y)
        new = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
        if positive and new[0] < 0:
            new = np.array([0., np.average(y, weights=weights)])
        residual = y-design@new
        sigma = max(1.4826*np.median(np.abs(residual-np.median(residual))), 1e-7)
        weights = np.minimum(1., 1.345*sigma/np.maximum(np.abs(residual), 1e-12))
        converged = np.max(np.abs(new-coeff)) < 1e-9
        coeff = new
        if converged:
            break
    slope = coeff[0]/spread
    return float(slope), float(coeff[1]-slope*center)


def measure(x, y, confidence, mask, heldout):
    xv, yv = x[mask], y[mask]
    train, test = mask & ~heldout, mask & heldout
    if min(train.sum(), test.sum()) < 30:
        return {"support": int(mask.sum()), "error": "insufficient spatial holdout support"}
    a, b = robust_affine(xv, yv)
    ua, ub = robust_affine(xv, yv, positive=False)
    ta, tb = robust_affine(x[train], y[train])
    residual = a*xv+b-yv
    test_residual = ta*x[test]+tb-y[test]
    spread = float(np.quantile(yv,.95)-np.quantile(yv,.05))
    rmse = float(np.sqrt(np.mean(residual**2)))
    test_rmse = float(np.sqrt(np.mean(test_residual**2)))
    constant_mse = float(np.mean((np.median(y[train])-y[test])**2))
    return {
        "support": int(mask.sum()), "train_support": int(train.sum()), "heldout_support": int(test.sum()),
        "pearson": float(stats.pearsonr(xv,yv).statistic),
        "spearman": float(stats.spearmanr(xv,yv).statistic),
        "positive_scale": a, "offset": b, "slope_at_boundary": a < 1e-8,
        "train_positive_scale":ta, "train_offset":tb,
        "unconstrained_scale": ua, "unconstrained_offset": ub,
        "predicted_depth_p05": float(np.quantile(xv,.05)), "predicted_depth_p95": float(np.quantile(xv,.95)),
        "mesh_depth_p05": float(np.quantile(yv,.05)), "mesh_depth_p95": float(np.quantile(yv,.95)),
        "mesh_depth_span_p90": spread, "confidence_median": float(np.median(confidence[mask])),
        "fit_rmse": rmse, "fit_median_abs": float(np.median(np.abs(residual))),
        "fit_p90_abs": float(np.quantile(np.abs(residual),.9)),
        "fit_nrmse_p90": rmse/max(spread,1e-10),
        "heldout_rmse": test_rmse, "heldout_nrmse_p90": test_rmse/max(spread,1e-10),
        "heldout_skill_vs_constant": 1-test_rmse**2/max(constant_mse,1e-12),
        "confidence_absresidual_spearman": (float(stats.spearmanr(confidence[mask],np.abs(residual)).statistic)
                                             if np.ptp(confidence[mask])>0 else None),
    }


def analyze(prediction, baseline, output):
    arrays = np.load(prediction)
    metadata = json.loads(prediction.with_name("metrics.json").read_text())
    inverse_ordinal = "inverse_relative_depth" in arrays.files
    if inverse_ordinal:
        # The inverse-relative origin and scale are unknown. A reciprocal
        # would impose an unjustified zero-disparity origin. Negation only
        # preserves the documented ordering; its affine fit is approximate.
        depth = -arrays["inverse_relative_depth"]
        confidence = np.ones_like(depth)
        rgb = arrays["images"] if "images" in arrays.files else None
        input_transform = "negative inverse_relative_depth: approximate ordinal-to-camera-z surrogate, NOT metric depth"
    else:
        depth, confidence, rgb = arrays["depth"][0], arrays["depth_conf"][0], arrays["images"]
        input_transform = "unmodified DA3 relative depth, NOT metric depth"
    ids = [int(value) for value in (arrays["view_ids"] if "view_ids" in arrays.files else metadata["view_ids"])]
    if depth.shape != confidence.shape or len(depth) != len(ids):
        raise ValueError("prediction metadata shape mismatch")
    records, map_arrays = [], {k:[] for k in ("predicted", "calibrated", "aligned_depth", "confidence", "support", "high_confidence_support", "mesh_depth",
                                             "valid_mask", "confidence_weight", "fit_train_mask", "fit_heldout_mask")}
    for index, view_id in enumerate(ids):
        mesh = np.load(baseline/"renders/data"/f"view_{view_id:03d}.npz")
        target, visible = mesh["depth"], mesh["mask"]
        shape = target.shape
        source = Image.open(baseline/"views"/f"view_{view_id:02d}.png").convert("RGB")
        if source.width != source.height or depth.shape[1] != depth.shape[2]:
            raise ValueError("This experiment requires same-framing square views; supply explicit crop metadata otherwise")
        if rgb is None:
            rgb_delta = None
        elif cv2 is not None:
            rgb_resized = cv2.resize(np.asarray(source),(rgb.shape[2],rgb.shape[1]),
                                     interpolation=cv2.INTER_CUBIC if rgb.shape[2]>source.width else cv2.INTER_AREA).astype(float)
        else:
            rgb_resized = np.asarray(source.resize((rgb.shape[2],rgb.shape[1]), Image.Resampling.BICUBIC)).astype(float)
        if rgb is not None:
            rgb_delta = np.abs(rgb_resized-rgb[index].astype(float))
        x, c = sample_grid(depth[index],shape), sample_grid(confidence[index],shape)
        foreground = np.asarray(Image.open(baseline/"masks"/f"mask_{view_id:02d}.png"))>0
        if foreground.shape != shape:
            foreground = np.asarray(Image.fromarray(foreground).resize(shape[::-1],Image.Resampling.NEAREST))
        joint = foreground & visible & np.isfinite(target) & np.isfinite(x) & np.isfinite(c)
        eroded = ndimage.binary_erosion(joint,iterations=2)
        # Exclude a one-pixel neighborhood of true mesh depth discontinuities
        # in the conservative visibility stratum; do not conceal broad results.
        filled = np.where(visible,target,0.)
        local_span = ndimage.maximum_filter(filled,3)-ndimage.minimum_filter(filled,3)
        stable = eroded & (local_span<.08)
        threshold = float(np.median(c[eroded]))
        yy,xx = np.indices(shape)
        heldout = ((yy//12+xx//12)%2)==1
        strata = {"foreground_visible_eroded": eroded,
                  "high_confidence_half": eroded&(c>=threshold),
                  "stable_visible_high_confidence": stable&(c>=threshold)}
        record = {"view_id": view_id, "prediction_index": index,
                  "predicted_resolution": list(depth[index].shape), "comparison_resolution": list(shape),
                  "source_resolution": [source.height,source.width],
                  "rgb_registration_mean_abs_255": float(rgb_delta.mean()) if rgb_delta is not None else None,
                  "rgb_registration_p99_abs_255": float(np.quantile(rgb_delta,.99)) if rgb_delta is not None else None,
                  "rgb_registration_method":("source runner and image_mapping metadata verified; no RGB tensor saved" if rgb is None else
                                             "official OpenCV interpolation" if cv2 is not None else "approximate Pillow bicubic diagnostic"),
                  "source_foreground_pixels": int(foreground.sum()), "mesh_visible_pixels": int(visible.sum()),
                  "joint_pixels_before_erosion": int(joint.sum()), "confidence_median_threshold":threshold,
                  "strata":{name:measure(x,target,c,mask,heldout) for name,mask in strata.items()}}
        broad = record["strata"]["foreground_visible_eroded"]
        record["candidate_constraint_gate"] = bool(broad["pearson"]>=.7 and broad["spearman"]>=.7 and
                                                   broad["heldout_skill_vs_constant"]>=.35 and
                                                   broad["heldout_nrmse_p90"]<=.3 and not broad["slope_at_boundary"])
        # Use only the spatial training half for deliverable calibration. The
        # saved holdout half never contributes to these fit coefficients.
        a,b = broad["train_positive_scale"],broad["train_offset"]
        calibrated = a*x+b
        valid = strata["stable_visible_high_confidence"] & record["candidate_constraint_gate"]
        rank = np.zeros(shape,float)
        rank[eroded] = stats.rankdata(c[eroded])/eroded.sum()
        weight = (valid.astype(np.float32) if inverse_ordinal else
                  np.where(valid,np.clip(2*rank-1,0,1),0).astype(np.float32))
        for name,data in {"predicted":x,"calibrated":calibrated,"aligned_depth":np.where(valid,calibrated,np.nan),
                          "confidence":c,"support":eroded,"high_confidence_support":strata["stable_visible_high_confidence"],
                          "mesh_depth":target,"valid_mask":valid,"confidence_weight":weight,
                          "fit_train_mask":eroded & ~heldout,"fit_heldout_mask":eroded & heldout}.items():
            map_arrays[name].append(data)
        records.append(record)
        print(prediction.parent.name,view_id,"r",round(broad["pearson"],3),"rho",round(broad["spearman"],3),
              "scale",round(a,3),"heldout_nrmse",round(broad["heldout_nrmse_p90"],3),flush=True)
    output.mkdir(parents=True,exist_ok=True)
    broad = [r["strata"]["foreground_visible_eroded"] for r in records]
    summary = {"model":metadata["model"], "prediction":str(prediction.resolve()),"baseline":str(baseline.resolve()),
               "input_transform":input_transform,
               "views":records,"deformation_performed":False,
               "median_pearson":float(np.median([r["pearson"] for r in broad])),
               "median_spearman":float(np.median([r["spearman"] for r in broad])),
               "median_heldout_nrmse_p90":float(np.median([r["heldout_nrmse_p90"] for r in broad])),
               "median_heldout_rmse":float(np.median([r["heldout_rmse"] for r in broad])),
               "median_heldout_skill_vs_constant":float(np.median([r["heldout_skill_vs_constant"] for r in broad])),
               "negative_correlation_views":[r["view_id"] for r in records if r["strata"]["foreground_visible_eroded"]["pearson"]<0],
               "candidate_constraint_views":[r["view_id"] for r in records if r["candidate_constraint_gate"]],
               "gate_description":"Exploratory necessary, not sufficient: Pearson/Spearman >= .7, heldout skill >= .35, normalized RMSE <= .3, positive slope",
               "registration":("Same full original square crop; model output returned to the original crop dimensions with no crop/recentering, then pixel-center bilinear resample to mesh maps. " + metadata.get("image_mapping","") if inverse_ordinal else
                               "Same square reference framing. DA3 upper_bound_resize to 308 or 504 (both divisible by 14), no crop. Pixel-center bilinear resample of predictions to mesh map size."),
               "fit":"Per-view Huber IRLS positive affine mesh_depth = scale * transformed_prediction + offset; spatial 12px checkerboard half held out. Deliverable arrays use train-only coefficients; all-support coefficients are diagnostic only.",
               "confidence":("No model confidence available. Uniform weight 1 on valid gated stable-visible foreground, 0 elsewhere. Confidence-named strata retain all equally weighted foreground; they do not imply predicted confidence." if inverse_ordinal else
                             "Model confidence is not a calibrated probability. Top half within eroded common foreground is an additional stratum, not an accuracy guarantee."),
               "limitations":["Baseline is a silhouette-inferred mesh, not ground-truth geometry.","Affine alignment cannot validate hidden concavities or fix incorrect cameras/anatomy.","Agreement permits only cautious depth-prior experiments; incompatible independent per-view corrections can conflict on shared vertices.","Do not use DA3-predicted camera poses to replace the fixed assumed cameras in this comparison."]}
    (output/"analysis.json").write_text(json.dumps(summary,indent=2)+"\n")
    fields=["view_id","stratum","support","pearson","spearman","positive_scale","offset","fit_rmse","heldout_rmse","heldout_nrmse_p90","heldout_skill_vs_constant","slope_at_boundary"]
    with (output/"per_view.csv").open("w",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
        for r in records:
            for name,s in r["strata"].items():writer.writerow({k:({"view_id":r["view_id"],"stratum":name,**s}).get(k) for k in fields})
    np.savez_compressed(output/"aligned_depths.npz",view_ids=np.array(ids),
                        input_transform=np.array(input_transform),
                        fit_scale=np.array([r["train_positive_scale"] for r in broad]),
                        fit_offset=np.array([r["train_offset"] for r in broad]),
                        diagnostic_full_fit_scale=np.array([r["positive_scale"] for r in broad]),
                        diagnostic_full_fit_offset=np.array([r["offset"] for r in broad]),
                        view_gate=np.array([r["candidate_constraint_gate"] for r in records]),
                        pearson=np.array([r["pearson"] for r in broad]),
                        spearman=np.array([r["spearman"] for r in broad]),
                        heldout_nrmse=np.array([r["heldout_nrmse_p90"] for r in broad]),
                        **{k:np.array(v) for k,v in map_arrays.items()})
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--prediction",type=Path,action="append",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    results=[analyze(path,args.baseline,args.output/path.parent.name) for path in args.prediction]
    compact=[{k:v for k,v in result.items() if k!="views"} for result in results]
    (args.output/"comparison.json").write_text(json.dumps(compact,indent=2)+"\n")
    print(json.dumps(compact,indent=2))
