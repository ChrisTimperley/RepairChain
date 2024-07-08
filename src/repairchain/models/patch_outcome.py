from __future__ import annotations

__all__ = (
    "PatchOutcome",
    "PatchOutcomeCache",
)

import enum
import pickle  # noqa: S403
import typing as t
from dataclasses import dataclass, field

if t.TYPE_CHECKING:
    from pathlib import Path

    import git

    from repairchain.models.diff import Diff
    from repairchain.models.settings import Settings


class PatchOutcome(enum.StrEnum):
    """Reports the outcome of evaluating a single candidate patch.

    FAILED_TO_BUILD indicates that the patch did not compile; all other statuses imply that the patch compiled.
    PASSED indicates that the patch passed all tests and the sanitizer did not report any issues.
    FAILED indicates that the patch failed one or more tests.
    """
    PASSED = "passed"
    FAILED = "failed"
    FAILED_TO_BUILD = "failed-to-build"


@dataclass
class PatchOutcomeCache:
    _save_to_file: Path | None = field(default=None)
    _version_patch_to_outcome: dict[tuple[str, str], PatchOutcome] = field(default_factory=dict)

    @classmethod
    def for_settings(cls, settings: Settings) -> t.Self:
        save_to_file = settings.cache_evaluations_to_file
        if save_to_file and save_to_file.exists():
            return cls.load(save_to_file)
        return cls(save_to_file)

    @classmethod
    def load(cls, path: Path) -> t.Self:
        with path.open("rb") as file:
            version_patch_to_outcome = pickle.load(file, encoding="utf-8")  # noqa: S301
        assert isinstance(version_patch_to_outcome, dict)
        return cls(
            _save_to_file=path,
            _version_patch_to_outcome=version_patch_to_outcome,
        )

    def save(self) -> None:
        if self._save_to_file is None:
            return
        self._save_to_file.parent.mkdir(parents=True, exist_ok=True)
        with self._save_to_file.open("wb") as file:
            pickle.dump(self._version_patch_to_outcome, file)

    def _key(self, version: git.Commit, patch: Diff) -> tuple[str, str]:
        return (version.hexsha, str(patch))

    def store(self, version: git.Commit, patch: Diff, outcome: PatchOutcome) -> None:
        key = self._key(version, patch)
        self._version_patch_to_outcome[key] = outcome

    def fetch(self, version: git.Commit, patch: Diff) -> PatchOutcome | None:
        key = self._key(version, patch)
        return self._version_patch_to_outcome.get(key)

    def contains(self, version: git.Commit, patch: Diff) -> bool:
        key = self._key(version, patch)
        return key in self._version_patch_to_outcome
