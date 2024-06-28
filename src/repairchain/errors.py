__all__ = (
    "BuildFailure",
    "RepairChainError",
)

import abc
from dataclasses import dataclass


class RepairChainError(abc.ABC, Exception):
    """Base class for all exceptions in the repairchain package."""


@dataclass
class BuildFailure(RepairChainError):
    """Indicates that a build failed."""
    message: str
    exit_code: int

    def __str__(self) -> str:
        return f"build failed with exit code {self.exit_code}: {self.message}"
