"""ORM row classes — one per file, mirroring src/models/.

Importing this package registers every row on ``Base.metadata`` (needed by
Alembic autogenerate and by ``Base.metadata.create_all`` in tests).
"""

from __future__ import annotations

from src.data.orm.audio_sample_row import AudioSampleRow
from src.data.orm.experiment_run_row import ExperimentRunRow
from src.data.orm.glyph_target_row import GlyphTargetRow
from src.data.orm.paired_example_row import PairedExampleRow
from src.data.orm.transform_candidate_row import TransformCandidateRow

__all__ = [
    "AudioSampleRow",
    "ExperimentRunRow",
    "GlyphTargetRow",
    "PairedExampleRow",
    "TransformCandidateRow",
]
