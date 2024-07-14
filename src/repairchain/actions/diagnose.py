from __future__ import annotations

from repairchain.models.patch_outcome import PatchOutcome
from repairchain.util import dd_minimize

__all__ = ("diagnose",)

import typing as t

from dockerblade.stopwatch import Stopwatch
from loguru import logger

from repairchain.actions.localize_diff import diff_to_functions
from repairchain.actions.map_functions import map_functions
from repairchain.models.diagnosis import Diagnosis
from repairchain.models.diff import Diff

T = t.TypeVar("T")

if t.TYPE_CHECKING:
    from sourcelocation import FileHunk

    from repairchain.models.project import Project


def _minimize(project: Project) -> Diff:
    """Minimizes the triggering commit's diff."""
    implicated_diff = project.original_implicated_diff
    num_hunks = len(list(implicated_diff.file_hunks))
    if num_hunks == 1:
        logger.warning("only one hunk in implicated diff; skipping minimization")
        return implicated_diff

    stopwatch = Stopwatch()
    stopwatch.start()
    logger.info(f"minimizing implicated diff:\n{implicated_diff}")

    triggering_commit = project.triggering_commit
    triggering_commit_parent = triggering_commit.parents[0]

    validator = project.validator
    workers = project.settings.workers
    logger.debug(f"using {workers} workers for build/regression calls during minimization")

    def tester(hunks: t.Sequence[FileHunk]) -> bool:
        as_diff = Diff.from_file_hunks(list(hunks))
        logger.debug(f"testing minimization:\n{as_diff}")
        outcome = validator.validate(
            as_diff,
            commit=triggering_commit_parent,
        )
        logger.debug(f"outcome: {outcome}")
        return outcome == PatchOutcome.FAILED

    to_minimize: list[FileHunk] = list(implicated_diff.file_hunks)
    minimized_hunks = dd_minimize(to_minimize, tester, time_limit=project.time_left)
    implicated_diff = Diff.from_file_hunks(minimized_hunks)
    time_taken = stopwatch.duration
    logger.info(
        f"minimized implicated diff (took {time_taken:.2f} s):\n{implicated_diff}",
    )
    return implicated_diff


def _index_and_localize(partial_diagnosis: Diagnosis) -> Diagnosis:
    project = partial_diagnosis.project
    triggering_commit = project.triggering_commit
    implicated_diff = partial_diagnosis.implicated_diff

    crash_version_implicated_files = implicated_diff.files
    logger.info(
        "implicated files in crash version ({}):\n{}",
        len(crash_version_implicated_files),
        "\n".join(crash_version_implicated_files),
    )

    index_at_crash_version = project.indexer.run(
        version=triggering_commit,
        restrict_to_files=crash_version_implicated_files,
    )
    crash_version_implicated_functions = diff_to_functions(
        implicated_diff,
        index_at_crash_version.functions,
    )
    logger.info(
        "implicated functions in crash version ({}):\n{}",
        len(crash_version_implicated_functions),
        "\n".join(f.name for f in crash_version_implicated_functions),
    )

    # FIXME there's an assumption here that these files haven't moved!
    # work on relaxing this assumption
    current_version_implicated_files = crash_version_implicated_files
    index_at_head = project.indexer.run(
        version=None,
        restrict_to_files=current_version_implicated_files,
    )
    current_version_implicated_functions = map_functions(
        functions=crash_version_implicated_functions,
        new_function_index=index_at_head.functions,
    )
    logger.info(
        "implicated functions in current version ({}):\n{}",
        len(current_version_implicated_functions),
        "\n".join(f.name for f in current_version_implicated_functions),
    )

    return Diagnosis(
        project=project,
        bug_type=project.sanitizer_report.bug_type,
        index_at_head=index_at_head,
        index_at_crash_version=index_at_crash_version,
        implicated_diff=implicated_diff,
        implicated_functions_at_head=current_version_implicated_functions,
        implicated_functions_at_crash_version=crash_version_implicated_functions,
    )


def diagnose(project: Project) -> Diagnosis:
    logger.info(f"bug type from sanitizer report: {project.sanitizer_report.bug_type}")

    implicated_diff = project.original_implicated_diff

    if project.settings.sanity_check:
        project.sanity_check()
    else:
        logger.info("skipping sanity check")

    if project.settings.minimize_failure:
        try:
            implicated_diff = _minimize(project)
        except Exception:  # noqa: BLE001
            logger.exception("failed to minimize implicated diff; continuing with original")
    else:
        logger.info("skipping minimization of implicated diff")

    diagnosis = Diagnosis(
        project=project,
        bug_type=project.sanitizer_report.bug_type,
        implicated_diff=implicated_diff,
        index_at_head=None,
        index_at_crash_version=None,
        implicated_functions_at_head=None,
        implicated_functions_at_crash_version=None,
    )

    if project.settings.enable_kaskara:
        logger.info("indexing and localizing with kaskara...")
        try:
            diagnosis = _index_and_localize(diagnosis)
        except Exception:  # noqa: BLE001
            logger.exception("failed to index with kaskara; continuing without indexing")
        else:
            logger.info("indexed and localized with kaskara")
    else:
        logger.info("skipping indexing and localization with kaskara")

    return diagnosis
