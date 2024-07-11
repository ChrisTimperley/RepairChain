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
    time_limit: int
        The maximum time in seconds to allow for the entire repair process.
    build_time_limit: int
        The maximum time in seconds to allow for building a container.
    regression_time_limit: int
        The maximum time in seconds to allow for running regression tests.
    pov_time_limit: int
        The maximum time in seconds to allow for running a PoV.
    enable_kaskara: bool
        Enables or disables the use of Kaskara for indexing.
    enable_reversion_repair: bool
        Enables or disables the use of reversion repair.
    enable_yolo_repair: bool
        Enables or disables the use of YOLO repair.
    enable_template_repair: bool
        Enables or disables the use of template repair.
    """
    time_limit: int = field(default=3600)
    workers: int = field(default=1)
    stop_early: bool = field(default=True)
    minimize_failure: bool = field(default=True)
    sanity_check: bool = field(default=True)
    cache_evaluations_to_file: Path | None = field(default=None)
    cache_index_to_file: Path | None = field(default=None)
    build_time_limit: int = field(default=120)
    regression_time_limit: int = field(default=120)
    pov_time_limit: int = field(default=60)
    litellm_url: str = field(default="http://0.0.0.0:4000")
    litellm_key: str = field(default="sk-1234", repr=False)
    enable_kaskara: bool = field(default=True)
    enable_reversion_repair: bool = field(default=True)
    enable_yolo_repair: bool = field(default=True)
    enable_template_repair: bool = field(default=True)

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
        fetch_int("time_limit", "REPAIRCHAIN_TIME_LIMIT")
        fetch_int("build_time_limit", "REPAIRCHAIN_BUILD_TIME_LIMIT")
        fetch_int("regression_time_limit", "REPAIRCHAIN_REGRESSION_TIME_LIMIT")
        fetch_int("pov_time_limit", "REPAIRCHAIN_POV_TIME_LIMIT")
        fetch_bool("stop_early", "REPAIRCHAIN_STOP_EARLY")
        fetch_bool("minimize_failure", "REPAIRCHAIN_MINIMIZE_FAILURE")
        fetch_bool("sanity_check", "REPAIRCHAIN_SANITY_CHECK")
        fetch_bool("enable_reversion_repair", "REPAIRCHAIN_ENABLE_REVERSION_REPAIR")
        fetch_bool("enable_yolo_repair", "REPAIRCHAIN_ENABLE_YOLO_REPAIR")
        fetch_bool("enable_template_repair", "REPAIRCHAIN_ENABLE_TEMPLATE_REPAIR")
        fetch_bool("enable_kaskara", "REPAIRCHAIN_ENABLE_KASKARA")
        fetch_path("cache_evaluations_to_file", "REPAIRCHAIN_EVALUATION_CACHE")
        fetch_path("cache_index_to_file", "REPAIRCHAIN_KASKARA_CACHE")
        fetch("litellm_url", "AIXCXX_LITELLM_HOSTNAME")
        fetch("litellm_key", "LITELLM_KEY")

        return cls(**kwargs)
