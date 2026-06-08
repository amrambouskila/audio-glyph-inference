"""CLI driver for the Phase-2 feasibility probe."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from src.simulation.feasibility_probe import FeasibilityProbe


def main(argv: Sequence[str] | None = None) -> int:
    """Run the feasibility probe from an NPZ payload."""
    parser = argparse.ArgumentParser(description="Run the Phase-2 affine-Fourier feasibility probe.")
    parser.add_argument("--probe-file", type=Path, required=True)
    parser.add_argument("--held-out-accent", required=True)
    parser.add_argument("--rho-min", type=float, required=True)
    parser.add_argument("--overfit-ratio-max", type=float, required=True)
    parser.add_argument("--lookup-failure-margin", type=float, required=True)
    parser.add_argument("--no-fit-tolerance", type=float, required=True)
    parser.add_argument("--rank-r", type=int, required=True)
    parser.add_argument("--ridge-alpha", type=float, required=True)
    parser.add_argument("--fourier-k", type=int, required=True)
    args = parser.parse_args(argv)

    payload = np.load(args.probe_file, allow_pickle=False)
    probe = FeasibilityProbe(
        rho_min=args.rho_min,
        overfit_ratio_max=args.overfit_ratio_max,
        lookup_failure_margin=args.lookup_failure_margin,
        no_fit_tolerance=args.no_fit_tolerance,
    )
    result = probe.fit(
        np.asarray(payload["phi"], dtype=np.float64),
        np.asarray(payload["targets"], dtype=np.float64),
        [str(value) for value in payload["letters"].tolist()],
        [str(value) for value in payload["accents"].tolist()],
        held_out_accent=args.held_out_accent,
        rank_r=args.rank_r,
        ridge_alpha=args.ridge_alpha,
        fourier_k=args.fourier_k,
    )
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
