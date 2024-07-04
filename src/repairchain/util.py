from __future__ import annotations

__all__ = ("split",)

import typing as t

T = t.TypeVar("T")


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
