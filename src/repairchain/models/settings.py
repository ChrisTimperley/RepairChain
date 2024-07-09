from __future__ import annotations

__all__ = ("Settings",)

import os
import typing as t
from dataclasses import dataclass, field
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
    cache_index_to_file: Path | None
        The path to a file used to persist the kaskara indices.
        If :code:`None`, caching to disk is disabled.
    build_time_limit: int
        The maximum time in seconds to allow for building a container.
    regression_time_limit: int
        The maximum time in seconds to allow for running regression tests.
    """
    workers: int = field(default=1)
    stop_early: bool = field(default=True)
    minimize_failure: bool = field(default=True)
    sanity_check: bool = field(default=True)
    cache_evaluations_to_file: Path | None = field(default=None)
    cache_index_to_file: Path | None = field(default=None)
    build_time_limit: int = field(default=60)
    regression_time_limit: int = field(default=60)

    @classmethod
    def from_env(cls, **kwargs: t.Any) -> Settings:  # noqa: ANN401
        """Create a settings object from environment variables.

        Parameters
        ----------
        **kwargs: t.Any
            Additional keyword arguments to pass to the constructor.

        Returns
        -------
        Settings
            The settings object.
        """
        def fetch(name: str, envvar: str) -> t.Any:  # noqa: ANN401
            value = kwargs.get(name, os.environ.get(envvar, None))
            if not value:
                value = None
            kwargs[name] = value
            return value

        def fetch_path(name: str, envvar: str) -> None:
            value = fetch(name, envvar)
            if isinstance(value, str):
                kwargs[name] = Path(value)

        def fetch_bool(name: str, envvar: str) -> None:
            value = fetch(name, envvar)
            if isinstance(value, str):
                value = value.lower()
                kwargs[name] = value in {"true", "1", "yes"}

        def fetch_int(name: str, envvar: str) -> None:
            value = fetch(name, envvar)
            if isinstance(value, str):
                kwargs[name] = int(value)

        fetch_int("workers", "REPAIRCHAIN_WORKERS")
        fetch_int("build_time_limit", "REPAIRCHAIN_BUILD_TIME_LIMIT")
        fetch_int("regression_time_limit", "REPAIRCHAIN_REGRESSION_TIME_LIMIT")
        fetch_bool("stop_early", "REPAIRCHAIN_STOP_EARLY")
        fetch_bool("minimize_failure", "REPAIRCHAIN_MINIMIZE_FAILURE")
        fetch_bool("sanity_check", "REPAIRCHAIN_SANITY_CHECK")
        fetch_path("cache_evaluations_to_file", "REPAIRCHAIN_EVALUATION_CACHE")
        fetch_path("cache_index_to_file", "REPAIRCHAIN_KASKARA_CACHE")

        return cls(**kwargs)
