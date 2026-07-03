"""Versioned prompt registry (design doc 5.6, Appendix B).

Prompts live as ``<name>.v<N>.md`` files in this directory and are loaded at
request time so prompt evolution can be tracked in git and correlated with eval
metrics. Use ``load("analysis")`` for the latest version or ``load("analysis",
version=2)`` to pin one.
"""

from __future__ import annotations

import re
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent
_PATTERN = re.compile(r"^(?P<name>.+)\.v(?P<version>\d+)\.md$")


def _versions(name: str) -> dict[int, Path]:
    out: dict[int, Path] = {}
    for path in _PROMPT_DIR.glob(f"{name}.v*.md"):
        m = _PATTERN.match(path.name)
        if m and m.group("name") == name:
            out[int(m.group("version"))] = path
    return out


def latest_version(name: str) -> int:
    versions = _versions(name)
    if not versions:
        raise FileNotFoundError(f"No prompt named '{name}' found in {_PROMPT_DIR}")
    return max(versions)


def load(name: str, version: int | None = None) -> str:
    versions = _versions(name)
    if not versions:
        raise FileNotFoundError(f"No prompt named '{name}' found in {_PROMPT_DIR}")
    version = version or max(versions)
    if version not in versions:
        raise FileNotFoundError(f"Prompt '{name}' has no version {version}.")
    return versions[version].read_text(encoding="utf-8")


def version_tag(name: str, version: int | None = None) -> str:
    version = version or latest_version(name)
    return f"{name}.v{version}"
