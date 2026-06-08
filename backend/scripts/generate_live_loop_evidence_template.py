"""Generate a complete all-glyph-form browser live-loop evidence template."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from uuid import UUID

from src.constants import GLYPH_FORMS


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not isfinite(parsed) or parsed <= 0.0:
        raise argparse.ArgumentTypeError("must be finite and greater than 0")
    return parsed


def live_loop_evidence_template(
    *,
    candidate_id: UUID,
    browser: str,
    score_rate_threshold_hz: float,
    tested_at: datetime,
) -> dict[str, object]:
    """Build a fillable all-glyph-form live-loop evidence JSON object."""
    return {
        "tested_at": tested_at.isoformat().replace("+00:00", "Z"),
        "browser": browser,
        "candidate_id": str(candidate_id),
        "score_rate_threshold_hz": score_rate_threshold_hz,
        "score_rate_hz_by_letter": {glyph_form: 0.0 for glyph_form in GLYPH_FORMS},
        "score_updates_by_letter": {glyph_form: 0 for glyph_form in GLYPH_FORMS},
        "glyph_target_id_by_letter": {glyph_form: "" for glyph_form in GLYPH_FORMS},
        "visible_score_by_letter": {glyph_form: False for glyph_form in GLYPH_FORMS},
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the live-loop evidence template generator."""
    parser = argparse.ArgumentParser(
        description="Generate a complete browser live-loop evidence JSON template for all Hebrew glyph forms.",
    )
    parser.add_argument("--candidate-id", type=UUID, required=True)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--score-rate-threshold-hz", type=_positive_float, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    template = live_loop_evidence_template(
        candidate_id=args.candidate_id,
        browser=args.browser,
        score_rate_threshold_hz=args.score_rate_threshold_hz,
        tested_at=datetime.now(tz=UTC),
    )
    encoded = json.dumps(template, ensure_ascii=False, indent=2)
    if args.output is None:
        print(encoded)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{encoded}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
