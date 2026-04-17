"""WebSocket live-pronunciation router (Phase 4).

Wire protocol: MessagePack-framed binary frames over `/ws/live`.
Client streams 16 kHz PCM; server streams back generated geometry +
shape-distance score for the candidate letter.
"""

from __future__ import annotations

from fastapi import APIRouter

router: APIRouter  # built in Phase 4 implementation
