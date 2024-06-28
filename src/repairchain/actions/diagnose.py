from __future__ import annotations

__all__ = ("diagnose",)

import typing as t

from loguru import logger

from repairchain.actions.commit_to_diff import commit_to_diff
from repairchain.actions.determine_bug_type import determine_bug_type
from repairchain.actions.index_functions import index_functions
from repairchain.actions.localize_diff import diff_to_functions
from repairchain.actions.map_functions import map_functions
from repairchain.models.diagnosis import Diagnosis

if t.TYPE_CHECKING:
    from repairchain.models.project import Project


def diagnose(project: Project) -> Diagnosis:
    bug_type = determine_bug_type(project.sanitizer_report)
    logger.info(f"determined bug type: {bug_type}")

    triggering_commit = project.triggering_commit
    implicated_diff = commit_to_diff(triggering_commit)

    crash_version_implicated_files = implicated_diff.files
    logger.info(
        f"implicated files ({len(crash_version_implicated_files)})"
        f": {', '.join(crash_version_implicated_files)}"
    )
    crash_version_function_index = index_functions(
        project=project,
        version=project.triggering_commit,
        restrict_to_files=crash_version_implicated_files,
    )
    crash_version_implicated_functions = diff_to_functions(
        implicated_diff,
        crash_version_function_index,
    )
    print(crash_version_implicated_functions)

    current_version_function_index = index_functions(
        project=project,
        version=project.head,
    )
    current_version_implicated_functions = map_functions(
        project=project,
        functions=crash_version_implicated_functions,
        from_version=project.triggering_commit,
        to_version=project.head,
        old_function_index=crash_version_function_index,
        new_function_index=current_version_function_index,
    )

    return Diagnosis(
        project=project,
        bug_type=bug_type,
        implicated_functions=current_version_implicated_functions,
    )
