from __future__ import annotations

import typing as t
from dataclasses import dataclass

from repairchain.actions.diagnose import diagnose

if t.TYPE_CHECKING:
    from repairchain.models.project import Project


@dataclass
class Orchestrator:
    project: Project

    def run(self) -> None:
        diagnosis = diagnose(self.project)
        print(diagnosis)

        # generate patches

        # validate

        raise NotImplementedError
