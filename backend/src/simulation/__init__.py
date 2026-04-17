"""Core domain logic: audio preprocessing, glyph extraction, transform search.

Every engine in this package must be importable and usable standalone —
no hidden dependencies on the FastAPI app layer or any persistent store.
See global CLAUDE.md section 7 ("Separation of concerns").
"""

from __future__ import annotations
