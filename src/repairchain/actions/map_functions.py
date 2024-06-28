from __future__ import annotations

import typing as t

from loguru import logger

if t.TYPE_CHECKING:
    import kaskara.functions


def map_function(
    function: kaskara.functions.Function,
    new_function_index: kaskara.functions.ProgramFunctions,
) -> kaskara.functions.Function | None:
    """Maps an individual function from an older version of the program to a newer version.

    Arguments:
    ---------
    function : kaskara.functions.Function
        The function to map (from the older version of the program).
    new_function_index : kaskara.functions.ProgramFunctions
        The index of functions in the newer version of the program.
    """
    # FIXME relax assumption about head_filename
    old_version_filename = function.location.filename
    new_version_filename = old_version_filename

    for match_candidate in new_function_index.in_file(new_version_filename):
        if match_candidate.name == function.name:
            return match_candidate

    return None


def map_functions(
    functions: list[kaskara.functions.Function],
    new_function_index: kaskara.functions.ProgramFunctions,
) -> list[kaskara.functions.Function]:
    # for now, map functions based purely on name and file
    mapped: list[kaskara.functions.Function] = []
    for function in functions:
        mapped_function = map_function(function, new_function_index)
        if mapped_function is None:
            logger.warning(
                f"unable to map function {function.name} in {function.location.filename}",
            )
        if mapped_function is not None:
            mapped.append(mapped_function)

    return mapped
