"""How much memory this process is actually allowed to use.

Not the same as the machine's memory. Under a container runtime the limit is set
by a cgroup, and exceeding it doesn't raise `MemoryError` — the kernel's OOM
killer sends SIGKILL. There is nothing to catch and nothing to log, so anything
with a large fixed memory cost has to be refused *before* it is loaded rather
than attempted and recovered from.
"""

from __future__ import annotations

from pathlib import Path

# cgroup v2 first, then v1.
_LIMIT_FILES = (
    Path("/sys/fs/cgroup/memory.max"),
    Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
)

# Both cgroup versions express "no limit" as a sentinel rather than an absence:
# v2 writes the literal "max", v1 a number near 2**63. Anything at or above this
# is treated as unlimited.
_UNLIMITED_FLOOR = 1 << 62


def memory_limit_bytes() -> int | None:
    """The cgroup memory ceiling, or ``None`` when unlimited or unreadable.

    ``None`` means "don't know", which callers should read as "unconstrained" —
    the constrained case is the one we can positively detect.
    """
    for path in _LIMIT_FILES:
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            continue
        if raw == "max":
            return None
        try:
            value = int(raw)
        except ValueError:
            continue
        if value <= 0 or value >= _UNLIMITED_FLOOR:
            return None
        return value
    return None
