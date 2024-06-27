from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repairchain.models.diff import Diff


__all__ = ("create_context",)

def create_context(files: dict[str,str], diff: Diff) -> str:
    string_code : str = ""
    for key in files:
        string_code = "BEGIN FILE: " + key + "\n" + files[key] + "\n END FILE"

    return ("The following code has a memory vulnerability in one of the files:\n"
    "BEGIN CODE\n"
    f"{string_code}\n"
    "END CODE\n"
    "This code was modified with the following git commit:\n"
    f"{diff}"
    "I want a patch for this program with the following properties:\n"
    "- The repair is minimal\n"
    "- Do not add comments\n"
    "- Keep the same functionality of the code\n"
    "- Do not simplify the code\n"
    "Use as format the following:\n"
    "BEGIN GIT DIFF PATCH\n"
    "<patch>\n"
    "END GIT DIFF PATCH\n"
    "BEGIN DESCRIPTION\n"
    "<description>\n"
    "END DESCRIPTION\n"
    )
