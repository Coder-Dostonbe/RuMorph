"""Time-ordered UUIDs (version 7, RFC 9562). Python 3.14 has uuid.uuid7, but the
tests may run on older versions, so the API generates them itself."""

from __future__ import annotations

import os
import time
import uuid


def uuid7(now_ms: int | None = None) -> uuid.UUID:
    ms = int(time.time() * 1000) if now_ms is None else now_ms
    rand = int.from_bytes(os.urandom(10), "big")
    value = (ms & ((1 << 48) - 1)) << 80          # 48-bit Unix time in milliseconds
    value |= 0x7 << 76                             # version
    value |= ((rand >> 62) & 0xFFF) << 64          # 12 random bits
    value |= 0b10 << 62                            # RFC 4122 variant
    value |= rand & ((1 << 62) - 1)                # 62 random bits
    return uuid.UUID(int=value)
