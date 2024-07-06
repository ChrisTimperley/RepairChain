from __future__ import annotations

__all__ = ("Settings",)

from dataclasses import dataclass, field


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
    """
    workers: int = field(default=1)
    stop_early: bool = field(default=True)
    minimize_failure: bool = field(default=True)
    sanity_check: bool = field(default=True)
