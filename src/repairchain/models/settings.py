from __future__ import annotations

__all__ = ("Settings",)

import typing as t
from dataclasses import dataclass, field

if t.TYPE_CHECKING:
    from pathlib import Path


@dataclass
class Settings:
    """Contains settings for RepairChain.

    Attributes
    ----------
    workers: int
        The number of workers to use for parallel operations.
    stop_early: bool
        Whether to stop early if a repair is found.
    minimize_failure: bool
        Whether to minimize the failure-inducing diff.
    sanity_check: bool
        Whether to perform a sanity check on the failure-inducing diff.
    cache_evaluations_to_file: Path | None
        The path to a file used to persist the evaluations of patches.
        If :code:`None`, caching to disk is disabled.
    """
    workers: int = field(default=1)
    stop_early: bool = field(default=True)
    minimize_failure: bool = field(default=True)
    sanity_check: bool = field(default=True)
    cache_evaluations_to_file: Path | None = field(default=None)
