from __future__ import annotations

import typing as t
from dataclasses import dataclass

from loguru import logger

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.determine_bug_type import determine_bug_type
from repairchain.actions.localize_diff import diff_to_functions

if t.TYPE_CHECKING:
    import kaskara.functions

    from repairchain.models.project import Project


@dataclass
class Orchestrator:
    project: Project

    # FIXME we need some better terms here
    def index_functions_in_crash_version(self) -> kaskara.functions.ProgramFunctions:
        # - we should only bother indexing implicated files
        raise NotImplementedError

    def run(self) -> None:
        bug_type = determine_bug_type(self.project.sanitizer_report)
        logger.info(f"determined bug type: {bug_type}")

        triggering_commit = self.project.triggering_commit
        implicated_diff = commit_to_diff(triggering_commit)

        crash_version_function_index = self.index_functions_in_crash_version()
        crash_version_implicated_functions = diff_to_functions(
            implicated_diff,
            crash_version_function_index,
        )
        print(crash_version_implicated_functions)

        # TODO map those implicated functions (from triggering commit) to current version

        raise NotImplementedError
