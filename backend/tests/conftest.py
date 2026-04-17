"""Shared pytest fixtures for the audio-glyph-inference backend.

Integration tests must hit a real Postgres (via a test container), never a
mocked database. See global CLAUDE.md section 7 ("Testing").
"""

from __future__ import annotations
