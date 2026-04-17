"""Transform-search experiment runs (Phase 2+).

An experiment is one configured search over a transform family against a
dataset slice. Results include fitted θ*, scoring metrics, and artifacts.
"""

from __future__ import annotations

from fastapi import APIRouter

router: APIRouter  # built in Phase 2 implementation
