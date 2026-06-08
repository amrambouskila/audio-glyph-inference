"""Pure Phase-2 feasibility probe for the affine-Fourier route."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from src.models.feasibility_probe_result import FeasibilityProbeResult, FeasibilityVerdict
from src.simulation.affine_fit import fit_fourier_theta
from src.simulation.batch_procrustes import procrustes_distance_batch
from src.simulation.batch_synthesis import synthesize_fourier_batch
from src.simulation.lookup_ratio import lookup_ratio
from src.simulation.transforms.transform_base import Theta

_DISTANCE_EPS = 1e-12


class FeasibilityProbe:
    """Closed-form affine-Fourier entry gate before full search compute."""

    def __init__(
        self,
        *,
        rho_min: float,
        overfit_ratio_max: float,
        lookup_failure_margin: float,
        no_fit_tolerance: float,
    ) -> None:
        if rho_min < 0.0:
            raise ValueError("rho_min must be non-negative")
        if overfit_ratio_max <= 0.0:
            raise ValueError("overfit_ratio_max must be positive")
        if lookup_failure_margin < 0.0:
            raise ValueError("lookup_failure_margin must be non-negative")
        if no_fit_tolerance < 0.0:
            raise ValueError("no_fit_tolerance must be non-negative")
        self.rho_min = rho_min
        self.overfit_ratio_max = overfit_ratio_max
        self.lookup_failure_margin = lookup_failure_margin
        self.no_fit_tolerance = no_fit_tolerance

    def fit(
        self,
        phi: np.ndarray,
        targets: np.ndarray,
        letters: Sequence[str],
        accents: Sequence[str],
        *,
        held_out_accent: str,
        rank_r: int,
        ridge_alpha: float,
        fourier_k: int,
    ) -> FeasibilityProbeResult:
        """Fit the probe on non-held-out accents and score the held-out accent.

        Args:
            phi: ndarray (B, D) dtype=float64, precomputed audio feature vectors.
            targets: ndarray (B, N, 2) dtype=float64, unit-square target contours.
            letters: length-B Hebrew-letter labels.
            accents: length-B accent labels.
            held_out_accent: accent label excluded from the closed-form fit.
            rank_r: low-rank affine cap r.
            ridge_alpha: non-negative ridge regularization weight.
            fourier_k: Fourier order K.

        Returns:
            FeasibilityProbeResult with distances, diagnostics, and verdict.
        """
        self._validate_inputs(phi, targets, letters, accents, rank_r, ridge_alpha, fourier_k)
        out_mask = np.asarray([accent == held_out_accent for accent in accents], dtype=bool)
        train_mask = ~out_mask
        if not out_mask.any():
            raise ValueError("held_out_accent must appear in accents")
        if not train_mask.any():
            raise ValueError("at least one fitted accent is required")

        searched_theta: Theta = {"rank_r": rank_r, "ridge_alpha": ridge_alpha, "fourier_k": fourier_k}
        theta = fit_fourier_theta(phi[train_mask], targets[train_mask], searched_theta, targets.shape[1])
        generated = synthesize_fourier_batch(phi, theta, targets.shape[1])
        probe_distances = procrustes_distance_batch(generated, targets)
        constants = self._constant_contours(targets, letters, train_mask)
        const_distances = procrustes_distance_batch(constants, targets)
        global_constants = np.repeat(self._global_mean(targets[train_mask])[None, :, :], targets.shape[0], axis=0)
        global_distances = procrustes_distance_batch(global_constants, targets)

        d_probe_in = float(probe_distances[train_mask].mean())
        d_probe_out = float(probe_distances[out_mask].mean())
        d_const_in = float(const_distances[train_mask].mean())
        d_const_out = float(const_distances[out_mask].mean())
        d_global_in = float(global_distances[train_mask].mean())
        r_track = lookup_ratio(generated[out_mask], [letters[index] for index in np.flatnonzero(out_mask)])
        overfit_ratio = float(d_probe_out / max(d_probe_in, _DISTANCE_EPS))
        delta_lookup = float(d_const_out - d_probe_out)
        return FeasibilityProbeResult(
            verdict=self.classify(
                d_probe_in=d_probe_in,
                d_probe_out=d_probe_out,
                d_const_out=d_const_out,
                d_global_in=d_global_in,
                r_track=r_track,
                overfit_ratio=overfit_ratio,
            ),
            d_probe_in=d_probe_in,
            d_probe_out=d_probe_out,
            d_const_in=d_const_in,
            d_const_out=d_const_out,
            d_global_in=d_global_in,
            delta_lookup=delta_lookup,
            overfit_ratio=overfit_ratio,
            r_track=r_track,
        )

    def classify(
        self,
        *,
        d_probe_in: float,
        d_probe_out: float,
        d_const_out: float,
        d_global_in: float,
        r_track: float,
        overfit_ratio: float,
    ) -> FeasibilityVerdict:
        """Classify already-computed probe metrics."""
        if d_probe_in >= d_global_in - self.no_fit_tolerance:
            return "NO_FIT"
        if r_track < self.rho_min:
            return "TRIVIAL_LOOKUP"
        if d_probe_out > d_const_out + self.lookup_failure_margin:
            return "TRIVIAL_LOOKUP"
        if d_probe_out < d_const_out and overfit_ratio < self.overfit_ratio_max:
            return "FEASIBLE"
        return "TRIVIAL_LOOKUP"

    def _constant_contours(self, targets: np.ndarray, letters: Sequence[str], train_mask: np.ndarray) -> np.ndarray:
        prototypes = {
            letter: self._global_mean(
                targets[[index for index, value in enumerate(letters) if value == letter and train_mask[index]]]
            )
            for letter in sorted(set(letters))
            if any(value == letter and train_mask[index] for index, value in enumerate(letters))
        }
        missing = sorted({letter for letter in letters if letter not in prototypes})
        if missing:
            raise ValueError(f"held-out letters lack fitted-accent prototypes: {missing}")
        return np.stack([prototypes[letter] for letter in letters]).astype(np.float64)

    def _global_mean(self, contours: np.ndarray) -> np.ndarray:
        """Return the row-wise contour mean.

        Args:
            contours: ndarray (B, N, 2) dtype=float64, unit-square target contours.

        Returns:
            ndarray (N, 2) dtype=float64, arithmetic mean contour.
        """
        return contours.mean(axis=0).astype(np.float64)

    def _validate_inputs(
        self,
        phi: np.ndarray,
        targets: np.ndarray,
        letters: Sequence[str],
        accents: Sequence[str],
        rank_r: int,
        ridge_alpha: float,
        fourier_k: int,
    ) -> None:
        if phi.ndim != 2:
            raise ValueError("phi must have shape (B, D)")
        if targets.ndim != 3 or targets.shape[2] != 2:
            raise ValueError("targets must have shape (B, N, 2)")
        if phi.shape[0] != targets.shape[0] or len(letters) != targets.shape[0] or len(accents) != targets.shape[0]:
            raise ValueError("phi, targets, letters, and accents must have matching length B")
        if targets.shape[0] == 0:
            raise ValueError("probe batch must contain at least one sample")
        if rank_r <= 0:
            raise ValueError("rank_r must be positive")
        if ridge_alpha < 0.0:
            raise ValueError("ridge_alpha must be non-negative")
        if fourier_k <= 0:
            raise ValueError("fourier_k must be positive")
