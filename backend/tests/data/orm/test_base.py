"""Tests for src/data/orm/base.py."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from src.data.orm.base import Base


def test_base_is_declarative_base_subclass() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_base_registry_is_present() -> None:
    assert hasattr(Base, "registry")
    assert hasattr(Base, "metadata")
