from __future__ import annotations

__all__ = ("Diagnosis",)

import json
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.bug_type import BugType
    from repairchain.models.diff import Diff
    from repairchain.models.project import Project
    from repairchain.models.sanitizer_report import SanitizerReport


@dataclass
class Diagnosis:
    project: Project = field(repr=False)
    bug_type: BugType
    index_at_head: kaskara.analysis.Analysis = field(repr=False)
    index_at_crash_version: kaskara.analysis.Analysis = field(repr=False)
    implicated_functions_at_head: list[kaskara.functions.Function] = field(repr=False)
    implicated_functions_at_crash_version: list[kaskara.functions.Function] = field(repr=False)
    implicated_diff: Diff

    @property
    def implicated_files_at_head(self) -> set[str]:
        return {f.filename for f in self.implicated_functions_at_head}

    @property
    def implicated_files_at_crash_version(self) -> set[str]:
        return {f.filename for f in self.implicated_functions_at_crash_version}

    @property
    def sanitizer_report(self) -> SanitizerReport:
        return self.project.sanitizer_report

    def _functions_to_dict(self, functions: list[kaskara.functions.Function]) -> list[dict[str, t.Any]]:
        return [
            {
                "name": function.name,
                "filename": function.location.filename,
                "return-type": function.return_type,
                "location": str(function.location),
            }
            for function in functions
        ]

    def to_dict(self) -> dict[str, t.Any]:
        implicated_functions_at_head = self._functions_to_dict(self.implicated_functions_at_head)
        implicated_functions_at_crash_version = self._functions_to_dict(self.implicated_functions_at_crash_version)
        return {
            "bug-type": self.bug_type.value,
            "implicated-diff": str(self.implicated_diff),
            "implicated-functions-at-head": implicated_functions_at_head,
            "implicated-functions-at-crash-version": implicated_functions_at_crash_version,
        }

    def save(self, path: str | Path) -> None:
        as_dict = self.to_dict()
        if isinstance(path, str):
            path = Path(path)
        with path.open("w") as file:
            json.dump(as_dict, file, indent=2)
