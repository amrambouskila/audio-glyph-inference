"""Database layer: SQLAlchemy 2.0 async engine + ORM rows.

Pydantic models (src/models/) own API contracts; ORM rows here own
storage. The two are wired together with explicit conversion via
`model_validate(..., from_attributes=True)` — never unified into one
class. See global CLAUDE.md section 5 for the SQLAlchemy+Pydantic
pairing rule.
"""
from __future__ import annotations