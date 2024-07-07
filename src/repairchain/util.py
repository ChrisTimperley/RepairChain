from __future__ import annotations

__all__ = (
    "dd_maximize",
    "dd_minimize",
    "split",
)

import typing as t

from loguru import logger

T = t.TypeVar("T")


def to_set(inp: t.Sequence[T]) -> set[int]:
    """Convert inp into a set of indices."""
    return set(range(len(inp)))


def from_indices(indices: set[int], inp: t.Sequence[T]) -> t.Sequence[T]:
    """Convert a set of indices into `inp` back into a collection."""
    ret = []
    for i, c in enumerate(inp):
        if i in indices:
            ret.append(c)
    return ret


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
) -> list[T]:
    """Finds the minimal portion of a sequence that satisfies a given predicate.

    Arguments:
    ---------
    original: t.Sequence[T]
        the original sequence to minimize
    tester: t.Callable[[t.Sequence[T]], bool]
        a function that takes a sequence and returns True if the sequence is valid

    Returns:
    -------
    list[T]
        the minimized sequence
    """
    c_fail = set(range(len(original)))
    logger.info(f"beginning dd_min. failure indices:{c_fail}")
    assert tester(original)  # property should hold on entry

    granularity = 2

    while len(c_fail) >= 2:  # noqa: PLR2004
        subsets = split(list(c_fail), granularity)
        some_complement_is_failing = False
        for subset in subsets:
            complement = c_fail - frozenset(subset)
            totest: t.Sequence[T] = from_indices(complement, original)
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

    return list(from_indices(set(c_fail), original))


def dd_maximize(
    original: t.Sequence[T],
    tester: t.Callable[[t.Sequence[T]], bool],
) -> list[T]:
    """Finds the maximal portion of a sequence that satisfies a given predicate.

    Arguments:
    ---------
    original: t.Sequence[T]
        the original sequence to maximize
    tester: t.Callable[[t.Sequence[T]], bool]
        a function that takes a sequence and returns True if the sequence is valid

    Returns:
    -------
    list[T]
        the maximized sequence
    """
    def new_tester(x: t.Sequence[T]) -> bool:
        return not tester(x)
    minimized = dd_minimize(original, new_tester)
    return [i for i in original if i not in minimized]
