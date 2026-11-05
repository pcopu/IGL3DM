# Dense quad-grid exploratory hull

This is an eight-view white lion with a dense connected black grid, superseding sparse numbered colored patches. Run the existing CLI with `--rows 2 --columns 4 --resolution 80 --image-size 192 --fixed-misses 1 --render`; input is `docs/experiments/15-dense-quad-grid/input.png`. Eight level cameras are assumed at45° intervals. The same silhouette segmentation, common framing and automatic extraction are used without manual model edits.

The committed `exploratory-hull.json` records the actual result. Input/output visuals live alongside the input in `docs/experiments/15-dense-quad-grid`. Drawn grid vertices are not used as true physical correspondences. Automatic junction tracking is analyzed separately; the hull was intentionally not blocked by its status.
