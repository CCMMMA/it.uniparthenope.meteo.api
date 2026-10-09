"""Atomic file publication shared by the on-disk caches.

Cache readers run concurrently with writers in other threads and worker
processes, so an entry must never be visible under its final name before it is
complete.
"""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any, Callable


def write_atomic(path: Any, write: Callable[[Any], None], *, binary: bool = False) -> None:
    """Fill a sibling temporary file through ``write`` and rename it onto ``path``."""
    target = Path(path)
    kwargs = {} if binary else {"encoding": "utf-8", "newline": ""}
    # Exclusive creation with open() rather than mkstemp() keeps the umask-based
    # permissions of the published file, which other services may need to read.
    temporary = target.with_name(
        f".{target.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with open(temporary, "xb" if binary else "x", **kwargs) as file:
            write(file)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
