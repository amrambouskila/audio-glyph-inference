"""AudioValidationError — raised when a recording violates the protocol."""

from __future__ import annotations


class AudioValidationError(ValueError):
    """An uploaded recording violates docs/recording_protocol.md §3 (duration / peak / active speech)."""
