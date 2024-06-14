from __future__ import annotations

import typing as t
from dataclasses import dataclass

from repairchain.actions.determine_patch_generation_strategy import determine_patch_generation_strategy
from repairchain.actions.diagnose import diagnose
from repairchain.actions.validate import validate

if t.TYPE_CHECKING:
    from repairchain.models.project import Project


@dataclass
class Orchestrator:
    project: Project

    def run(self) -> None:
        diagnosis = diagnose(self.project)
        patch_generator = determine_patch_generation_strategy(diagnosis)
        candidates = patch_generator.run()

        patches = validate(
            self.project,
            candidates,
            stop_early=True,
        )
        # TODO communicate these patches to VERSATIL (write to specified file?)
        print(patches)
