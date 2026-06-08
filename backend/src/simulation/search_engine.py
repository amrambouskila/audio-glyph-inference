"""Search engine for θ* = argminθ mean d(Fθ(x), L) + λ·Complexity(Fθ)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import uuid4

import cma
import numpy as np
from scipy.special import ndtr

from src.config import BackendSettings, get_settings
from src.constants import MULTI_STROKE_LETTERS, NUM_HEBREW_LETTERS
from src.models.transform_candidate import TransformCandidate
from src.simulation.batch_features import compute_feature_matrix
from src.simulation.batch_procrustes import chamfer_distance_batch, procrustes_distance_batch
from src.simulation.batch_synthesis import synthesize_fourier_batch, synthesize_lissajous_batch
from src.simulation.contour_compare import contour_compare
from src.simulation.lookup_ratio import lookup_ratio
from src.simulation.scoring import interpretability_score, simplicity_score
from src.simulation.symbolic_search import fit_symbolic_regression
from src.simulation.transforms.fittable_family import FittableFamily
from src.simulation.transforms.parameter_spec import ParameterSpec
from src.simulation.transforms.transform_base import Theta, TransformFamily

_VALID_STRATEGIES = frozenset({"grid", "cma-es", "bayesian", "symbolic-regression"})
_VALID_METRICS = frozenset({"procrustes", "frechet", "chamfer"})


class SearchEngine:
    """Standalone transform search engine."""

    def __init__(
        self,
        family: TransformFamily,
        distance_metric: str,
        strategy: str,
        max_evaluations: int,
        regularization_weight: float,
    ) -> None:
        if strategy not in _VALID_STRATEGIES:
            raise ValueError(f"unknown search strategy {strategy!r}; expected one of {sorted(_VALID_STRATEGIES)}")
        if distance_metric not in _VALID_METRICS:
            raise ValueError(f"unknown distance metric {distance_metric!r}; expected one of {sorted(_VALID_METRICS)}")
        if max_evaluations <= 0:
            raise ValueError("max_evaluations must be positive")
        if regularization_weight < 0:
            raise ValueError("regularization_weight must be non-negative")
        if strategy == "symbolic-regression" and family.name() != "symbolic_regression":
            raise ValueError("symbolic-regression strategy requires SymbolicRegressionFamily")
        self.family = family
        self.distance_metric = distance_metric
        self.strategy = strategy
        self.max_evaluations = max_evaluations
        self.regularization_weight = regularization_weight
        self._parameter_space = family.parameter_space()
        self._parameter_keys = sorted(self._parameter_space)

    def fit(
        self,
        audio: Sequence[np.ndarray],
        targets: np.ndarray,
        letters: Sequence[str],
        accents: Sequence[str],
        *,
        shared_across_letters: bool,
        seed: int,
    ) -> list[TransformCandidate]:
        """Return candidates sorted best-first by regularized mean shape distance.

        Args:
            audio: sequence length B of ndarrays (num_frames_i, frame_length) float64.
            targets: ndarray (B, num_points, 2) float64 target contours in the unit square.
            letters: length-B letter label per example (selects the target glyph).
            accents: length-B accent label per example (drives leave-one-accent-out).
            shared_across_letters: fit one θ for all letters (True) or per-letter θ (False).
            seed: RNG seed for reproducibility; recorded on ExperimentRun.
        """
        self._validate_fit_inputs(audio, targets, letters, accents)
        settings = get_settings()
        if self.strategy == "symbolic-regression":
            return fit_symbolic_regression(
                self.family,
                audio,
                targets,
                letters,
                accents,
                distance_metric=self.distance_metric,
                max_evaluations=self.max_evaluations,
                regularization_weight=self.regularization_weight,
                shared_across_letters=shared_across_letters,
                seed=seed,
                settings=settings,
            )
        phi = compute_feature_matrix(
            audio,
            sample_rate_hz=settings.audio_sample_rate_hz,
            n_mels=settings.feature_n_mels,
            n_segments=settings.feature_n_segments,
        )
        if shared_across_letters:
            return self._fit_subset(
                audio,
                phi,
                targets,
                letters,
                shared_across_letters=True,
                seed=seed,
                settings=settings,
            )
        candidates: list[tuple[float, TransformCandidate]] = []
        for letter in sorted(set(letters)):
            indices = np.asarray([idx for idx, value in enumerate(letters) if value == letter], dtype=np.int64)
            subset = self._fit_subset(
                [audio[int(idx)] for idx in indices],
                phi[indices],
                targets[indices],
                [letters[int(idx)] for idx in indices],
                shared_across_letters=False,
                seed=seed,
                settings=settings,
            )
            candidates.extend((candidate.mean_shape_distance, candidate) for candidate in subset)
        return [candidate for _, candidate in sorted(candidates, key=lambda item: item[0])]

    def _fit_subset(
        self,
        audio: Sequence[np.ndarray],
        phi: np.ndarray,
        targets: np.ndarray,
        letters: Sequence[str],
        *,
        shared_across_letters: bool,
        seed: int,
        settings: BackendSettings,
    ) -> list[TransformCandidate]:
        if self.strategy == "cma-es":
            self._validate_cma_space()
            theta = self._run_cma(
                lambda searched: self._objective(
                    searched,
                    audio,
                    phi,
                    targets,
                    letters,
                    shared_across_letters,
                    settings,
                ),
                seed,
            )
            candidate = self._candidate_from_searched(
                theta,
                audio,
                phi,
                targets,
                letters,
                shared_across_letters,
                settings,
            )
            return [candidate]
        if self.strategy == "bayesian":
            theta = self._run_bayesian(
                lambda searched: self._objective(
                    searched,
                    audio,
                    phi,
                    targets,
                    letters,
                    shared_across_letters,
                    settings,
                ),
                seed,
                settings,
            )
            candidate = self._candidate_from_searched(
                theta,
                audio,
                phi,
                targets,
                letters,
                shared_across_letters,
                settings,
            )
            return [candidate]
        scored = [
            self._candidate_from_searched(theta, audio, phi, targets, letters, shared_across_letters, settings)
            for theta in self._grid_thetas(seed, settings)
        ]
        return sorted(
            scored,
            key=lambda candidate: self._objective_from_candidate(candidate, shared_across_letters, settings),
        )

    def _decode(self, genotype: np.ndarray) -> Theta:
        """Decode a normalized genotype vector into searched theta."""
        if genotype.shape != (len(self._parameter_keys),):
            raise ValueError(f"genotype must have shape ({len(self._parameter_keys)},)")
        clipped = np.clip(genotype.astype(np.float64), 0.0, 1.0)
        theta: Theta = {}
        settings = get_settings()
        for index, key in enumerate(self._parameter_keys):
            spec = self._parameter_space[key]
            value = float(clipped[index])
            theta[key] = self._decode_value(key, spec, value, settings)
        return theta

    def _decode_value(
        self,
        key: str,
        spec: ParameterSpec,
        genotype_value: float,
        settings: BackendSettings,
    ) -> float | int | str:
        if spec.kind == "continuous":
            if key in settings.search_log_scale_keys:
                if spec.low is None or spec.high is None or spec.low <= 0:
                    raise ValueError(f"log-scaled key {key!r} requires positive bounds")
                low_log = np.log10(spec.low)
                high_log = np.log10(spec.high)
                return float(10.0 ** (low_log + genotype_value * (high_log - low_log)))
            if spec.low is None or spec.high is None:
                raise ValueError(f"continuous key {key!r} requires bounds")
            return float(spec.low + genotype_value * (spec.high - spec.low))
        if spec.kind == "integer":
            if spec.low is None or spec.high is None:
                raise ValueError(f"integer key {key!r} requires bounds")
            count = int(spec.high - spec.low + 1)
            return int(min(int(spec.low) + int(np.floor(genotype_value * count)), int(spec.high)))
        if spec.choices is None:
            raise ValueError(f"categorical key {key!r} requires choices")
        choice_index = min(int(np.floor(genotype_value * len(spec.choices))), len(spec.choices) - 1)
        return spec.choices[choice_index]

    def _grid_thetas(self, seed: int, settings: BackendSettings) -> list[Theta]:
        axes = [
            self._grid_axis(self._parameter_space[key], settings.search_grid_resolution) for key in self._parameter_keys
        ]
        genotypes = np.array(np.meshgrid(*axes, indexing="ij"), dtype=np.float64).reshape(len(axes), -1).T
        decoded = [self._decode(row) for row in genotypes]
        if self.family.name() == "fourier_series":
            decoded = [dict(theta, fourier_k=k) for k in range(1, settings.fourier_k_max + 1) for theta in decoded]
        if len(decoded) > self.max_evaluations:
            if settings.search_grid_truncation == "error":
                raise ValueError(
                    f"grid has {len(decoded)} evaluations, exceeding max_evaluations={self.max_evaluations}"
                )
            order = np.random.default_rng(seed).permutation(len(decoded))[: self.max_evaluations]
            decoded = [decoded[int(index)] for index in order]
        return decoded

    def _grid_axis(self, spec: ParameterSpec, resolution: int) -> np.ndarray:
        if spec.kind == "continuous":
            return np.linspace(0.0, 1.0, resolution)
        if spec.kind == "integer":
            if spec.low is None or spec.high is None:
                raise ValueError("integer ParameterSpec requires bounds")
            count = int(spec.high - spec.low + 1)
            return (np.arange(count, dtype=np.float64) + 0.5) / count
        if spec.choices is None:
            raise ValueError("categorical ParameterSpec requires choices")
        return (np.arange(len(spec.choices), dtype=np.float64) + 0.5) / len(spec.choices)

    def _run_cma(self, objective: Callable[[Theta], float], seed: int) -> Theta:
        settings = get_settings()
        dim = len(self._parameter_keys)
        strategy = cma.CMAEvolutionStrategy(
            np.full(dim, 0.5, dtype=np.float64),
            settings.cma_sigma0,
            {
                "bounds": [0.0, 1.0],
                "seed": seed,
                "maxfevals": self.max_evaluations,
                "verbose": -9,
                "tolfun": settings.cma_tolfun,
            },
        )
        while not strategy.stop():
            solutions = strategy.ask()
            values = [objective(self._decode(np.asarray(solution, dtype=np.float64))) for solution in solutions]
            strategy.tell(solutions, values)
        return self._decode(np.asarray(strategy.result.xbest, dtype=np.float64))

    def _run_bayesian(self, objective: Callable[[Theta], float], seed: int, settings: BackendSettings) -> Theta:
        dim = len(self._parameter_keys)
        if dim == 0:
            return {}
        rng = np.random.default_rng(seed)
        initial_count = min(self.max_evaluations, settings.bayesian_initial_points)
        evaluated = [np.full(dim, 0.5, dtype=np.float64)]
        evaluated.extend(rng.random((max(initial_count - 1, 0), dim)))
        values = [objective(self._decode(genotype)) for genotype in evaluated]
        while len(evaluated) < self.max_evaluations:
            pool = rng.random((settings.bayesian_candidate_pool_size, dim))
            acquisition = self._expected_improvement(
                np.asarray(evaluated, dtype=np.float64),
                np.asarray(values, dtype=np.float64),
                pool,
                settings,
            )
            next_genotype = pool[int(np.argmax(acquisition))]
            evaluated.append(next_genotype)
            values.append(objective(self._decode(next_genotype)))
        return self._decode(evaluated[int(np.argmin(values))])

    def _expected_improvement(
        self,
        observed_x: np.ndarray,
        observed_y: np.ndarray,
        candidates_x: np.ndarray,
        settings: BackendSettings,
    ) -> np.ndarray:
        y_scale = float(observed_y.std())
        if y_scale == 0.0:
            y_scale = 1.0
        y = (observed_y - float(observed_y.mean())) / y_scale
        kernel = self._rbf_kernel(observed_x, observed_x, settings.bayesian_length_scale)
        kernel += np.eye(observed_x.shape[0], dtype=np.float64) * settings.bayesian_noise
        cross_kernel = self._rbf_kernel(observed_x, candidates_x, settings.bayesian_length_scale)
        cholesky = np.linalg.cholesky(kernel)
        alpha = np.linalg.solve(cholesky.T, np.linalg.solve(cholesky, y))
        mean = cross_kernel.T @ alpha
        solved = np.linalg.solve(cholesky, cross_kernel)
        variance = np.maximum(1.0 - np.sum(solved * solved, axis=0), 0.0)
        sigma = np.sqrt(variance)
        improvement = float(y.min()) - mean
        z = np.divide(improvement, sigma, out=np.zeros_like(improvement), where=sigma > 0.0)
        expected = improvement * ndtr(z) + sigma * np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi)
        return np.where(np.isfinite(expected), expected, 0.0)

    def _rbf_kernel(self, left: np.ndarray, right: np.ndarray, length_scale: float) -> np.ndarray:
        delta = left[:, None, :] - right[None, :, :]
        squared_distance = np.sum(delta * delta, axis=2)
        return np.exp(-0.5 * squared_distance / (length_scale * length_scale))

    def _validate_cma_space(self) -> None:
        non_continuous = [key for key, spec in self._parameter_space.items() if spec.kind != "continuous"]
        if non_continuous:
            raise ValueError(f"cma-es supports only continuous coordinates; got {non_continuous}")

    def _candidate_from_searched(
        self,
        searched_theta: Theta,
        audio: Sequence[np.ndarray],
        phi: np.ndarray,
        targets: np.ndarray,
        letters: Sequence[str],
        shared_across_letters: bool,
        settings: BackendSettings,
    ) -> TransformCandidate:
        theta = self._fit_theta(phi, targets, searched_theta)
        generated = self._generate(audio, phi, theta, targets.shape[1])
        distances = self._distances(generated, targets, letters, settings)
        mean_distance = float(distances.mean())
        complexity = self.family.complexity(theta)
        prior = self._family_prior(settings)
        return TransformCandidate(
            id=uuid4(),
            family=self.family.name(),
            theta=theta,
            shared_across_letters=shared_across_letters,
            interpretability_score=interpretability_score(complexity, prior, settings.simplicity_c_scale),
            simplicity_score=simplicity_score(complexity, settings.simplicity_c_scale),
            mean_shape_distance=mean_distance,
            lookup_ratio=lookup_ratio(generated, letters),
            created_at=datetime.now(tz=UTC),
        )

    def _objective(
        self,
        searched_theta: Theta,
        audio: Sequence[np.ndarray],
        phi: np.ndarray,
        targets: np.ndarray,
        letters: Sequence[str],
        shared_across_letters: bool,
        settings: BackendSettings,
    ) -> float:
        candidate = self._candidate_from_searched(
            searched_theta,
            audio,
            phi,
            targets,
            letters,
            shared_across_letters,
            settings,
        )
        return self._objective_from_candidate(candidate, shared_across_letters, settings)

    def _objective_from_candidate(
        self, candidate: TransformCandidate, shared_across_letters: bool, settings: BackendSettings
    ) -> float:
        return candidate.mean_shape_distance + (
            self.regularization_weight
            * self.family.complexity(candidate.theta)
            * self._sharing_multiplier(shared_across_letters, settings)
        )

    def _sharing_multiplier(self, shared_across_letters: bool, settings: BackendSettings) -> float:
        if shared_across_letters:
            return 1.0
        return 1.0 + settings.search_per_letter_penalty * NUM_HEBREW_LETTERS

    def _fit_theta(self, phi: np.ndarray, targets: np.ndarray, searched_theta: Theta) -> Theta:
        if isinstance(self.family, FittableFamily):
            return self.family.fit_theta(phi, targets, searched_theta, targets.shape[1])
        return dict(searched_theta)

    def _generate(self, audio: Sequence[np.ndarray], phi: np.ndarray, theta: Theta, num_points: int) -> np.ndarray:
        name = self.family.name()
        if name == "fourier_series":
            return synthesize_fourier_batch(phi, theta, num_points)
        if name == "lissajous":
            return synthesize_lissajous_batch(phi, theta, num_points)
        return np.stack([self.family.forward(frames, theta) for frames in audio]).astype(np.float64)

    def _distances(
        self,
        generated: np.ndarray,
        targets: np.ndarray,
        letters: Sequence[str],
        settings: BackendSettings,
    ) -> np.ndarray:
        if self.distance_metric == "procrustes":
            distances = procrustes_distance_batch(generated, targets)
        elif self.distance_metric == "chamfer":
            distances = chamfer_distance_batch(generated, targets)
        else:
            distances = np.asarray(
                [contour_compare(generated[index], targets[index], "frechet") for index in range(generated.shape[0])],
                dtype=np.float64,
            )
        multistroke = np.asarray([letter in MULTI_STROKE_LETTERS for letter in letters], dtype=bool)
        if multistroke.any() and self.distance_metric != "chamfer":
            if settings.search_multistroke_metric == "error":
                raise ValueError(
                    "multi-stroke targets require chamfer substitution or search_multistroke_metric='chamfer'"
                )
            chamfer = chamfer_distance_batch(generated[multistroke], targets[multistroke])
            distances = distances.copy()
            distances[multistroke] = chamfer
        return distances

    def _family_prior(self, settings: BackendSettings) -> float:
        name = self.family.name()
        if name == "fourier_series":
            return settings.interpretability_prior_fourier
        if name == "lissajous":
            return settings.interpretability_prior_lissajous
        if name == "phase_space_embedding":
            return settings.interpretability_prior_phase_space
        return 1.0

    def _validate_fit_inputs(
        self,
        audio: Sequence[np.ndarray],
        targets: np.ndarray,
        letters: Sequence[str],
        accents: Sequence[str],
    ) -> None:
        if len(audio) == 0:
            raise ValueError("audio batch must contain at least one sample")
        if targets.ndim != 3 or targets.shape[2] != 2:
            raise ValueError("targets must have shape (B, N, 2)")
        if len(audio) != targets.shape[0] or len(letters) != targets.shape[0] or len(accents) != targets.shape[0]:
            raise ValueError("audio, targets, letters, and accents must have matching length B")
