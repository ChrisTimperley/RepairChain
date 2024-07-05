from __future__ import annotations

__all__ = (
    "dd_maximize",
    "dd_minimize",
    "split",
)

import typing as t

T = t.TypeVar("T")


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
    raise NotImplementedError


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
    raise NotImplementedError


def split(list_: t.Sequence[T], chunks: int) -> list[frozenset[T]]:
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
    subsets: list[frozenset[T]] = []
    start = 0
    for i in range(chunks):
        subset = list_[start:start + (list_size - start) // (chunks - i)]
        if subset:
            subsets.append(frozenset(subset))
        start += len(subset)
    return subsets
