# Frozen bounded graph retracking protocol

Frozen before reading or evaluating control ground truth, 2026-11-05 UTC.

One image-only method, two variants, evaluated unchanged on known96 then known64. Optional known256 only if useful. No learned models, fitted target shape, camera data, original track identities, or truth in tracker.

- Redetect skeleton junctions in every decoded frame using existing `grid_tracks.junctions`.
- Graph = traced ink-segment edges plus edges of detected closed quad cells whose four corners uniquely map to junctions within 3.5 px with at least 0.5 px nearest-neighbor margin. Use existing detectors unchanged.
- Descriptors = normalized RootSIFT at fixed sizes 16 and 32 pixels; compare image context, not any control identity.
- Adjacent and independently computed two-step correspondences use reciprocal pyramidal LK predictions (21 px window, 3 levels), then one-to-one assignment to detected nodes. Candidate gates use 35% of local detected-node spacing, clipped to 3–7 px, and both directional predictions; forward/backward LK error <=1.5 px; displacement <=80 px; RootSIFT distance <=0.8; patch NCC >=0.55.
- Assignment cost combines both normalized prediction residuals, descriptor distance, and patch NCC. Three rounds of neighbor assignment compatibility penalize mapped source edges that disagree with target graph edges. Final accepted matches must have at least two matching graph neighbors and no more unsupported mapped neighbors than supported ones. Ambiguous alternatives with a cost gap <0.12 are rejected in either source or target direction. Missing correspondence starts a new local ID; no cross-gap reuse.
- Variant `graph_joint`: use the accepted adjacent associations.
- Variant `graph_joint_cycle_veto`: identical associations, but when an independently accepted skip-frame match disagrees with the composed adjacent matches, reject both constituent edges. Absence of skip support does not itself reject a chain. This is deliberately a veto, not proof of identity.
- Every detection, association and emitted track coordinate/ID is retained in artifacts. No original whole-track selection.
- Evaluation uses existing `evaluate_selection.evaluate` only after track artifacts exist. Report >=3 samples and >=30 degree span, correct/wrong/unresolved, unique correct physical IDs and observation coverage, heldout errors and passing wrong identities. Low reprojection and local topology are not proof of physical identity.
- No parameter changes based on truth outcomes. If implementation defects are found, document them and distinguish repair from method tuning.

Implementation repair before first run: corrected module root from parents[3] to parents[2] after import failed. No tracking or evaluation occurred before this fix.
