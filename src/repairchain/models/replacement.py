from __future__ import annotations

__all__ = ("Replacement",)

import functools
import typing as t
from dataclasses import dataclass

from sourcelocation import (
    FileLocationRange,
    Location,
)


@dataclass(frozen=True)
class Replacement:
    """Describes the replacement of a contiguous body of text in a single file with a provided text.

    Attributes
    ----------
    location: FileLocationRange
        The contiguous range of text that should be replaced.
    text: str
        The source text that should be used as a replacement.
    """
    location: FileLocationRange
    text: str

    @staticmethod
    def from_dict(d: dict[str, str]) -> Replacement:
        location = FileLocationRange.from_string(d["location"])
        return Replacement(location, d["text"])

    @classmethod
    def resolve(
        cls,
        replacements: t.Sequence[Replacement],
    ) -> list[Replacement]:
        """Resolves all conflicts in a sequence of replacements."""
        file_to_reps: dict[str, list[Replacement]] = {}
        for rep in replacements:
            if rep.filename not in file_to_reps:
                file_to_reps[rep.filename] = []
            file_to_reps[rep.filename].append(rep)

        # resolve redundant replacements
        for fn, reps in file_to_reps.items():
            def cmp(x: Location, y: Location) -> int:
                return -1 if x < y else 0 if x == y else 0

            def compare(x: Replacement, y: Replacement) -> int:
                start_x, stop_x = x.location.start, x.location.stop
                start_y, stop_y = y.location.start, y.location.stop
                if start_x != start_y:
                    return cmp(start_x, start_y)
                # start_x == start_y
                return -cmp(stop_x, stop_y)

            reps.sort(key=functools.cmp_to_key(compare))

            filtered: list[Replacement] = [reps[0]]
            i, j = 0, 1
            while j < len(reps):
                x, y = reps[i], reps[j]
                if x.location.stop > y.location.start:
                    j += 1
                else:
                    i += 1
                    j += 1
                    filtered.append(y)
            filtered.reverse()
            file_to_reps[fn] = filtered

        # collapse into a flat sequence of transformations
        resolved: list[Replacement] = []
        for reps in file_to_reps.values():
            resolved += reps
        return resolved

    @property
    def filename(self) -> str:
        """The name of the file in which the replacement should be made."""
        return self.location.filename

    def to_dict(self) -> dict[str, str]:
        return {
            "location": str(self.location),
            "text": self.text,
        }
