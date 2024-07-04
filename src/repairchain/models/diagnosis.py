from __future__ import annotations

__all__ = ("Diagnosis",)

import json
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.bug_type import BugType
    from repairchain.models.project import Project
    from repairchain.models.sanitizer_report import SanitizerReport


@dataclass
class Diagnosis:
    project: Project = field(repr=False)
    bug_type: BugType
    implicated_functions: list[kaskara.functions.Function]

    @property
    def sanitizer_report(self) -> SanitizerReport:
        return self.project.sanitizer_report

    def to_dict(self) -> dict[str, t.Any]:
        function_descriptions: list[dict[str, t.Any]] = [
            {
                "name": function.name,
                "filename": function.location.filename,
                "return-type": function.return_type,
                "location": str(function.location),
            }
            for function in self.implicated_functions
        ]
        return {
            "bug-type": self.bug_type.value,
            "implicated-functions": function_descriptions,
        }

    def save(self, path: str | Path) -> None:
        as_dict = self.to_dict()
        if isinstance(path, str):
            path = Path(path)
        with path.open("w") as file:
            json.dump(as_dict, file, indent=2)
