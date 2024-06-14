from __future__ import annotations

__all__ = ("Diagnosis",)

import typing as t
from dataclasses import dataclass

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.bug_type import BugType
    from repairchain.models.project import Project
    from repairchain.models.sanitizer_report import SanitizerReport


@dataclass
class Diagnosis:
    project: Project
    bug_type: BugType
    implicated_functions: list[kaskara.functions.Function]

    @property
    def sanitizer_report(self) -> SanitizerReport:
        return self.project.sanitizer_report
