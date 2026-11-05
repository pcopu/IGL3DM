"""Apply the frozen trajectory selector, optionally evaluate a known control.

Truth is used only after selection. Raw tracks and point coordinates stay local.
"""
import argparse
import json
from pathlib import Path

from trajectory_consistency import select


def run(tracks_path, output, period, truth_path=None):
    output = Path(output)
    if period <= 0:
        raise ValueError('Period must be positive')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Refusing nonempty output')
    tracks = json.loads(Path(tracks_path).read_text())
    selected, audit = select(tracks, period, threshold=1.)
    # Selection is complete before even loading optional evaluation truth.
    report = None
    if truth_path is not None:
        from evaluate_selection import evaluate
        report = evaluate(selected, json.loads(Path(truth_path).read_text()), period)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'tracks.json').write_text(json.dumps(selected, indent=2))
    (output / 'audit.json').write_text(json.dumps(audit, indent=2))
    if report is not None:
        (output / 'validation.json').write_text(json.dumps(report, indent=2))
        summary = {k: v for k, v in report.items() if k != 'tracks'}
    else:
        summary = {'input_tracks': len(tracks), 'selected_tracks': len(selected),
                   'period_prior_frames': period, 'truth_used': False}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tracks', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--period', type=float, required=True)
    parser.add_argument('--truth', type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.tracks, args.output, args.period, args.truth), indent=2))
