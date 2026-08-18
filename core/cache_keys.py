"""Shared cache-key construction utilities.

Keeping key generation in one module prevents the memory and disk cache layers
from silently drifting apart when their implementations change.
"""

from __future__ import annotations

import hashlib
from typing import Any


def resolve_cache_key_source(request: Any = None, override: Any = None) -> str:
    """Return the explicit key source or the URL carried by a request object."""
    if override is not None:
        return str(override)
    if request is None:
        raise ValueError("request is required when no cache-key override is provided")
    return str(request.url)


def make_cache_key(request: Any = None, override: Any = None) -> str:
    """Build the legacy-compatible MD5 cache key for a source value.

    MD5 remains intentional here: this is a compact lookup key, not a security
    primitive, and changing it would invalidate every existing cache entry.
    """
    source = resolve_cache_key_source(request, override)
    return hashlib.md5(source.encode("utf-8")).hexdigest()  # noqa: S324 - non-security key
