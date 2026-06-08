"""Candidate quality scores derived from a transform's complexity.

Two closely-related free functions on the same contract (complexity -> [0, 1]
score), grouped like shape_distance.py per docs/phases/phase-2-plan.md §6.
Both are reporting-only — they never enter the search objective or the exit gate.
Pure; the calibration constants (C_scale, family priors) are passed in by the
caller from config.
"""

from __future__ import annotations


def simplicity_score(complexity: float, c_scale: float) -> float:
    """Map a complexity cost to a simplicity score.

    1/(1 + complexity/c_scale): equals 1 at complexity 0, 0.5 at complexity == c_scale,
    and decreases monotonically. For complexity >= 0 and c_scale > 0 the result is in (0, 1].
    """
    return 1.0 / (1.0 + complexity / c_scale)


def interpretability_score(complexity: float, family_prior: float, c_scale: float) -> float:
    """simplicity_score scaled by a family interpretability prior in [0, 1]."""
    return simplicity_score(complexity, c_scale) * family_prior
