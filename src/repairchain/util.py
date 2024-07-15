from __future__ import annotations

import contextlib
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path

__all__ = (
    "dd_maximize",
    "dd_minimize",
    "split",
)

import typing as t

import git
from dockerblade.stopwatch import Stopwatch
from loguru import logger

if t.TYPE_CHECKING:
    import kaskara
    import kaskara.functions
    import kaskara.statements

    from repairchain.models.diff import Diff
    from repairchain.models.project import Project

T = t.TypeVar("T")


@contextlib.contextmanager
def write_diff_to_file(diff: Diff) -> t.Iterator[Path]:
    """Writes the given diff to a temporary file and yields the path to that file."""
    temp_patch_path = Path(tempfile.mkstemp(suffix=".diff")[1])
    contents = str(diff)
    try:
        with temp_patch_path.open("w", encoding="utf-8") as temp_patch_file:
            temp_patch_file.write(contents)
        yield temp_patch_path
    finally:
        temp_patch_path.unlink()


def restore_to_head(project: Project) -> None:
    repo = project.repository
    restore_to = repo.head.commit.hexsha
    with suppress(git.exc.GitCommandError):
        repo.git.rebase("--abort")
    with suppress(git.exc.GitCommandError):
        repo.git.merge("--abort")
    with suppress(git.exc.GitCommandError):
        repo.git.clean("-xdf")
    with suppress(git.exc.GitCommandError):
        pass
    try:
        logger.debug(f"restoring to: {restore_to}")
        repo.git.reset(restore_to)
    except repo.git.exc.GitCommandError:
        logger.exception(f"failed to restore git repo to: {restore_to}")


def apply_patch(project: Project, patch: Diff) -> None:
    # make a commit consisting of only the minimized undo
    repo_path = Path.resolve(project.local_repository_path)
    with write_diff_to_file(patch) as temp_patch_path:
        command_args = [
                "patch",
                "-u",
                "-p0",
                "-i",
                str(temp_patch_path),
                "-d",
                str(repo_path),
        ]
        logger.debug(f"applying patch: {command_args}")
        subprocess.run(
                command_args,
                check=True,
                stdin=subprocess.DEVNULL,
            )


def diff_to_git_diff(
        project: Project,
        patch: Diff,
) -> str:
    restore_to_head(project)
    apply_patch(project, patch)
    return str(project.repository.git.diff())


def statements_in_function(
    index: kaskara.analysis.Analysis,
    function: kaskara.functions.Function,
) -> list[kaskara.statements.Statement]:
    """Returns a list of all statements in a given function."""
    results: list[kaskara.statements.Statement] = []

    within_file = function.body_location.filename
    within_range = function.body_location.location_range
    for statement in index.statements.in_file(within_file):
        statement_starts_at = statement.location.start
        if statement_starts_at in within_range:
            results.append(statement)

    return results


def strip_prefix(string: str, prefix: str) -> str:
    """Strips a given prefix from a provided string if it exists.

    Parameters
    ----------
    string: str
        the string to strip the prefix from
    prefix: str
        the prefix to strip

    Returns
    -------
    str
        the string with the prefix removed
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    return string


def to_set(inp: t.Sequence[T]) -> set[int]:
    """Convert inp into a set of indices."""
    return set(range(len(inp)))


def from_indices(indices: set[int], input_: t.Sequence[T]) -> list[T]:
    """Convert a set of indices into `inp` back into a collection."""
    return [value for (index, value) in enumerate(input_) if index in indices]


def split(list_: t.Sequence[T], chunks: int) -> list[set[T]]:
    """Splits a sequence into sub-sequences of approximately equal size.

    Parameters
    ----------
    list_: t.Sequence[T]
        list to split
    chunks: int
        number of desired sublists

    Returns
    -------
    list[frozenset[T]]
        a list of approximately equal-sized subsequences
    """
    list_size = len(list_)
    subsets: list[set[T]] = []
    start = 0
    for i in range(chunks):
        subset = list_[start:start + (list_size - start) // (chunks - i)]
        if subset:
            subsets.append(set(subset))
        start += len(subset)
    return subsets


def dd_minimize(
    original: t.Sequence[T],
    tester: t.Callable[[t.Sequence[T]], bool],
    *,
    time_limit: float | None = None,
) -> list[T]:
    """Finds the minimal portion of a sequence that satisfies a given predicate.

    Arguments:
    ---------
    original: t.Sequence[T]
        the original sequence to minimize
    tester: t.Callable[[t.Sequence[T]], bool]
        a function that takes a sequence and returns True if the sequence is valid
    time_limit: float | None
        the maximum time to spend on minimizing the sequence.
        if :code:`None`, no time limit is enforced

    Returns:
    -------
    list[T]
        the minimized sequence

    Raises:
    ------
    TimeoutError
        if the time limit is reached
    """
    timer = Stopwatch()
    timer.start()

    def check_time() -> None:
        if time_limit is not None and timer.duration > time_limit:
            message = f"minimization reached time limit after {timer.duration:.2f} seconds"
            raise TimeoutError(message)

    c_fail = set(range(len(original)))
    logger.debug(f"beginning dd_min. failure indices: {c_fail}")
    assert tester(original)  # property should hold on entry

    granularity = 2

    while len(c_fail) >= 2:  # noqa: PLR2004
        logger.debug(f"using granularity: {granularity}")
        subsets = split(list(c_fail), granularity)
        some_complement_is_failing = False
        for subset in subsets:
            check_time()
            complement = c_fail - frozenset(subset)
            totest = from_indices(complement, original)
            if tester(totest):
                c_fail = complement
                old_granularity = granularity
                granularity = max(granularity - 1, 2)
                logger.debug(
                    "property holds on this subset, decreasing granularity "
                    f"from {old_granularity} to {granularity}.",
                )
                logger.debug(f"updated c_fail to: {c_fail}")
                some_complement_is_failing = True
                break

        if not some_complement_is_failing:
            if granularity == len(c_fail):
                break
            granularity = min(granularity * 2, len(c_fail))

    logger.debug("finished dd_minimize")
    return from_indices(c_fail, original)


def dd_maximize(
    original: t.Sequence[T],
    tester: t.Callable[[t.Sequence[T]], bool],
    *,
    time_limit: float | None = None,
) -> list[T]:
    """Finds the maximal portion of a sequence that satisfies a given predicate.

    Arguments:
    ---------
    original: t.Sequence[T]
        the original sequence to maximize
    tester: t.Callable[[t.Sequence[T]], bool]
        a function that takes a sequence and returns True if the sequence is valid
    time_limit: float | None
        the maximum time to spend on maximizing the sequence.
        if :code:`None`, no time limit is enforced

    Returns:
    -------
    list[T]
        the maximized sequence

    Raises:
    ------
    TimeoutError
        if the time limit is reached
    """
    def new_tester(x: t.Sequence[T]) -> bool:
        return not tester(x)
    minimized = dd_minimize(original, new_tester, time_limit=time_limit)
    return [i for i in original if i not in minimized]
