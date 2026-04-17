"""Tests for src/api/main.py.

Phase 1 scaffold: create_app raises NotImplementedError. When the body
lands the scaffold assertion is replaced by a real FastAPI smoke test
(see docs/phases/phase-1-plan.md).
"""

from __future__ import annotations

import pytest
from src.api import main


def test_create_app_is_scaffold_stub() -> None:
    with pytest.raises(NotImplementedError):
        main.create_app()


def test_app_attribute_is_declared() -> None:
    # Module-level `app: FastAPI` annotation must be present for Phase 1 scaffold.
    assert "app" in main.__annotations__
