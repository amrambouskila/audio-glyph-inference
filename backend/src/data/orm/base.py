"""Declarative base for all ORM rows."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root declarative base — all ORM rows inherit from this."""
