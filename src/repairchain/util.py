from __future__ import annotations

__all__ = (
    "dd_maximize",
    "dd_minimize",
    "split",
)

import typing as t

from dockerblade.stopwatch import Stopwatch
from loguru import logger
from sourcelocation.diff import (
    DeletedLine,
    FileHunk,
    HunkLine,
    InsertedLine,
)

from repairchain.models.diff import (
    Diff,
    FileDiff,
    Hunk,
)

if t.TYPE_CHECKING:
    import kaskara
    import kaskara.functions
    import kaskara.statements

T = t.TypeVar("T")


def revert_diff(diff: Diff) -> Diff:
    def revert_hunk_line(line: HunkLine) -> HunkLine:
        match line:
            case InsertedLine(content):
                return DeletedLine(content)
            case DeletedLine(content):
                return InsertedLine(content)
        return line

    def revert_hunk(hunk: Hunk) -> Hunk:
        return Hunk(
            old_start_at=hunk.old_start_at,
            new_start_at=hunk.new_start_at,
            lines=[revert_hunk_line(line) for line in hunk.lines],
        )

    def revert_file_hunk(file_hunk: FileHunk) -> FileHunk:
        return FileHunk(
            old_filename=file_hunk.old_filename,
            new_filename=file_hunk.new_filename,
            hunk=revert_hunk(file_hunk.hunk),
        )

    return Diff.from_file_hunks([
        revert_file_hunk(file_hunk) for file_hunk in list(diff.file_hunks)
    ])


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


def add_prefix_to_diff(diff: Diff) -> Diff:
    file_diffs = diff.file_diffs
    file_diffs = [
        FileDiff(
            old_filename=f"a/{file_diff.old_filename}",
            new_filename=f"b/{file_diff.new_filename}",
            hunks=file_diff.hunks,
        )
        for file_diff in file_diffs
    ]
    return Diff(file_diffs)


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
