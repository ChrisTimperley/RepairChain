from __future__ import annotations

import kaskara.functions

__all__ = (
    "diff_to_functions",
)

import typing as t

if t.TYPE_CHECKING:
    import kaskara

    from repairchain.models.diff import Diff


def diff_to_functions(
    diff: Diff,
    functions: kaskara.functions.ProgramFunctions,
) -> list[kaskara.functions.Function]:
    """Returns the functions that are affected by a given diff."""
    affected: list[kaskara.functions.Function] = []

    # NOTE need to handle abs vs. rel paths very, very, very carefully
    for file_diff in diff.file_diffs:
        filename = file_diff.new_filename
        functions_in_file = functions.in_file(filename)

        for function in functions_in_file:
            location = function.location.location_range
            function_start_at_line = location.start.line
            function_ends_at_line = location.stop.line

            for hunk in file_diff.hunks:
                # FIXME account for size of hunk
                hunk_starts_at_line = hunk.new_start_at
                if function_start_at_line <= hunk_starts_at_line <= function_ends_at_line:
                    affected.append(function)

    return affected
